"""Ask a local vision model (served by Ollama) whether a capture actually shows
the sky, and how good the sunset in it is.

Runs entirely on the NUC's CPU; nothing leaves the machine. Best-effort: any
failure returns None so the caller can skip the frame and try again later.
"""

import base64
import io
import json
import logging
import os

import requests
from PIL import Image

log = logging.getLogger(__name__)

# What the camera is looking at. The model answers with one of these; "no_sunset" is added
# by normalize() for visible sky that shows no sunset color.
VIEWS = ["sky", "obstructed", "dark", "no_signal"]

# A frame needs at least this AI sunset score (judged on the sky only) to be eligible as a
# day's best shot.
MIN_SCORE = int(os.environ.get("AI_MIN_SCORE", 15))

# Ollama constrains the reply to this JSON schema, so it always parses.
SCHEMA = {
    "type": "object",
    "properties": {
        "sky_visible": {"type": "boolean"},
        "view": {"type": "string", "enum": VIEWS},
        "sky_percent": {"type": "integer", "minimum": 0, "maximum": 100},
        "score": {"type": "integer", "minimum": 0, "maximum": 100},
        "reason": {"type": "string"},
    },
    "required": ["sky_visible", "view", "sky_percent", "score", "reason"],
}

PROMPT = """This is a still frame from a fixed webcam that looks out at the sky at sunset or sunrise. Trees, branches, buildings, hills, water, boats or a shoreline in the frame are normal, and the camera may be aimed a little off; that is expected.

sky_visible: is ANY open sky visible anywhere in the frame, even a small patch or a thin strip above trees? Answer true unless there is no sky at all. Trees in the frame are NOT a reason to answer false.

view:
- "sky": any open sky is visible. This is the answer for almost every frame, including ones with trees or buildings in them.
- "obstructed": ONLY when no sky is visible at all, because a wall or object completely fills the frame.
- "dark": the frame is black or nearly black, e.g. night.
- "no_signal": an error screen, test card, blank frame or "stream offline" graphic.

sky_percent (0-100): roughly what percentage of the frame is open sky (for information only).

score (0-100), how beautiful the sunset is, judged on the visible sky only (trees, buildings or a slightly off camera angle must not lower it):
- 0-20: grey, flat or washed-out sky, little or no warm color.
- 20-40: some faint warm color near the horizon.
- 40-60: clear warm colors (orange, pink, red) in part of the sky.
- 60-80: vivid colors across much of the sky, with interesting clouds catching the light.
- 80-100: spectacular: intense reds, pinks and oranges lighting up clouds across the sky.

reason: one short phrase (at most 12 words) saying what drives the score."""

MAX_WIDTH = 768  # the model doesn't need full 1080p, and smaller images are much faster on CPU


def prepare_image(image_bytes, max_width=MAX_WIDTH):
    """Downscale to max_width and return base64 JPEG, as Ollama expects."""
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    if img.width > max_width:
        img = img.resize((max_width, round(img.height * max_width / img.width)))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def judge_image(image_bytes, model, ollama_url, timeout=600):
    """Returns {"view", "is_sunset", "score", "reason"} or None if anything fails."""
    body = {
        "model": model,
        "messages": [{"role": "user", "content": PROMPT, "images": [prepare_image(image_bytes)]}],
        "format": SCHEMA,
        "stream": False,
        "think": False,  # skip "thinking" models' reasoning step; it's slow on CPU
        "options": {"temperature": 0},
    }
    url = f"{ollama_url.rstrip('/')}/api/chat"
    try:
        resp = requests.post(url, json=body, timeout=timeout)
        if resp.status_code == 400 and "think" in resp.text:
            # Models without a thinking mode may reject the flag; ask again without it.
            del body["think"]
            resp = requests.post(url, json=body, timeout=timeout)
        resp.raise_for_status()
        return normalize(json.loads(resp.json()["message"]["content"]))
    except (requests.RequestException, ValueError, KeyError, TypeError) as e:
        log.warning("AI judge failed (%s): %s", model, e)
        return None


def normalize(data, min_score=None):
    """Clamp and validate the model's answer; None if it's unusable.

    A frame can't win a day ("is_sunset" false) when it's dark / no signal, when the model
    says BOTH that no sky is visible and that the view is obstructed, or when the sky shows
    no sunset: its sky-only score is under min_score. That last case catches a camera turned
    toward red autumn leaves or brick under a grey sky, which the color score reads as a
    blazing sunset. Trees or buildings on their own never disqualify a frame.
    """
    min_score = MIN_SCORE if min_score is None else min_score
    view = data.get("view")
    if view not in VIEWS:
        return None
    score = max(0, min(100, int(data.get("score", 0))))
    if view in ("dark", "no_signal"):
        view, score = view, 0
    elif data.get("sky_visible") is False and view == "obstructed":
        view, score = "obstructed", 0
    else:
        view = "sky" if score >= min_score else "no_sunset"
    return {
        "view": view,
        "is_sunset": view == "sky",
        "sky_percent": max(0, min(100, int(data.get("sky_percent", 100)))),
        "score": score,
        "reason": str(data.get("reason", "")).strip()[:200],
    }


def ensure_model(model, ollama_url):
    """Download the model into Ollama if it isn't there yet (first run only; can take minutes)."""
    base = ollama_url.rstrip("/")
    tags = requests.get(f"{base}/api/tags", timeout=30).json().get("models", [])
    if any(m.get("name") == model or m.get("model") == model for m in tags):
        return
    log.info("Downloading %s into Ollama (one-time, a few GB)...", model)
    # Stream the pull so progress shows up instead of a long silence.
    with requests.post(f"{base}/api/pull", json={"model": model, "stream": True}, stream=True, timeout=None) as resp:
        resp.raise_for_status()
        last_logged = -10
        for line in resp.iter_lines():
            if not line:
                continue
            update = json.loads(line)
            if update.get("error"):
                raise RuntimeError(f"Ollama couldn't pull {model}: {update['error']}")
            total, done = update.get("total"), update.get("completed")
            if total and done is not None:
                pct = int(done * 100 / total)
                if pct >= last_logged + 10 or pct == 100:
                    log.info("  %s: %s %d%% of %.1f GB", model, update.get("status", ""), pct, total / 1e9)
                    last_logged = pct
            elif update.get("status") and update["status"] != "success":
                log.info("  %s: %s", model, update["status"])
                last_logged = -10  # a new layer starts its own progress
    log.info("%s ready", model)
