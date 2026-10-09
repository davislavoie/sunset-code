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

# What the camera is looking at.
VIEWS = ["sky", "obstructed", "dark", "no_signal"]

# A frame only counts as "not the sky" (score 0) when open sky is under this share of the
# frame. Foreground trees/buildings/water are normal, so this is deliberately low.
MIN_SKY_PERCENT = int(os.environ.get("AI_MIN_SKY_PERCENT", 10))

# Ollama constrains the reply to this JSON schema, so it always parses.
SCHEMA = {
    "type": "object",
    "properties": {
        "view": {"type": "string", "enum": VIEWS},
        "sky_percent": {"type": "integer", "minimum": 0, "maximum": 100},
        "score": {"type": "integer", "minimum": 0, "maximum": 100},
        "reason": {"type": "string"},
    },
    "required": ["view", "sky_percent", "score", "reason"],
}

PROMPT = """This is a still frame from a fixed webcam that looks out at the sky at sunset or sunrise. The bottom half of the frame normally shows foreground (trees, buildings, hills, water, boats or a shoreline), and the camera may be aimed a little off; that is expected. The sunset is the sky above the horizon. Judge it.

view:
- "sky": open sky above a horizon is visible, even if trees, buildings or other things fill the foreground. When in doubt, choose "sky".
- "obstructed": the camera is pointed the wrong way, so a wall, building, tree trunk, branches or another close object fills nearly the whole frame and little or no sky shows.
- "dark": the frame is mostly black, e.g. night.
- "no_signal": an error screen, test card, blank frame or "stream offline" graphic.

sky_percent (0-100): roughly what percentage of the frame is open sky.

score (0-100), how beautiful the sunset is, judged on the visible sky only (foreground objects and a slightly off camera angle must not lower it):
- 0-20: grey, flat or washed-out sky, little or no warm color.
- 20-40: some faint warm color near the horizon.
- 40-60: clear warm colors (orange, pink, red) in part of the sky.
- 60-80: vivid colors across much of the sky, with interesting clouds catching the light.
- 80-100: spectacular: intense reds, pinks and oranges lighting up clouds across the sky.
Use 0 only for "dark" or "no_signal".

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


def normalize(data, min_sky_percent=None):
    """Clamp and validate the model's answer; None if it's unusable.

    The model's own "obstructed" call is only a hint: a frame counts as not the sky when
    it's dark / no signal, or when open sky is under min_sky_percent of the frame. Trees or
    buildings in front of a visible sunset therefore still count."""
    min_sky = MIN_SKY_PERCENT if min_sky_percent is None else min_sky_percent
    view = data.get("view")
    if view not in VIEWS:
        return None
    sky_percent = max(0, min(100, int(data.get("sky_percent", 100))))
    is_sunset = view not in ("dark", "no_signal") and sky_percent >= min_sky
    if view in ("sky", "obstructed"):
        view = "sky" if is_sunset else "obstructed"
    return {
        "view": view,
        "is_sunset": is_sunset,
        "sky_percent": sky_percent,
        "score": max(0, min(100, int(data.get("score", 0)))) if is_sunset else 0,
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
