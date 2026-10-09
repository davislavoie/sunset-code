"""Ask a local vision model (served by Ollama) whether a capture actually shows
the sky, and how good the sunset in it is.

Runs entirely on the NUC's CPU; nothing leaves the machine. Best-effort: any
failure returns None so the caller can skip the frame and try again later.
"""

import base64
import io
import json
import logging

import requests
from PIL import Image

log = logging.getLogger(__name__)

# What the camera is looking at. Only "sky" frames should count toward rankings.
VIEWS = ["sky", "obstructed", "dark", "no_signal"]

# Ollama constrains the reply to this JSON schema, so it always parses.
SCHEMA = {
    "type": "object",
    "properties": {
        "view": {"type": "string", "enum": VIEWS},
        "score": {"type": "integer", "minimum": 0, "maximum": 100},
        "reason": {"type": "string"},
    },
    "required": ["view", "score", "reason"],
}

PROMPT = """This is a still frame from a fixed webcam that is meant to look out at the sky \
at sunset or sunrise. Judge it.

view:
- "sky": open sky above a horizon is clearly visible and fills a good part of the frame.
- "obstructed": a wall, building, tree, foliage or other close object blocks most of the \
view (for example the camera has been turned the wrong way).
- "dark": the frame is mostly black, e.g. night.
- "no_signal": an error screen, test card, blank frame or "stream offline" graphic.

score (0-100), how beautiful the sunset is:
- 0-20: grey, flat or washed-out sky, little or no warm color.
- 20-40: some faint warm color near the horizon.
- 40-60: clear warm colors (orange, pink, red) in part of the sky.
- 60-80: vivid colors across much of the sky, with interesting clouds catching the light.
- 80-100: spectacular: intense reds, pinks and oranges lighting up clouds across the sky.
If view is not "sky", the score must be 0.

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


def normalize(data):
    """Clamp and validate the model's answer; None if it's unusable."""
    view = data.get("view")
    if view not in VIEWS:
        return None
    score = max(0, min(100, int(data.get("score", 0))))
    is_sunset = view == "sky"
    return {
        "view": view,
        "is_sunset": is_sunset,
        "score": score if is_sunset else 0,
        "reason": str(data.get("reason", "")).strip()[:200],
    }


def ensure_model(model, ollama_url):
    """Download the model into Ollama if it isn't there yet (first run only; can take minutes)."""
    base = ollama_url.rstrip("/")
    tags = requests.get(f"{base}/api/tags", timeout=30).json().get("models", [])
    if any(m.get("name") == model or m.get("model") == model for m in tags):
        return
    log.info("Pulling %s into Ollama (one-time download)...", model)
    requests.post(f"{base}/api/pull", json={"model": model, "stream": False}, timeout=None).raise_for_status()
