"""The local vision model reads the sky on the 1h, 45m, 30m and 15m pre shots: is there a lit band between the cloud
base and the horizon that the setting sun can shine through, and clouds above it to catch the light?
On 160 1h-pre photos its gap_thickness tracked the day's outcome at rho 0.61 (analysis/vision_gap.md), the
strongest single sign found. 30 min before is the last shot with plenty of time to get down to the lake;
15 min is a last check. At 5 min the photo's own colour already says it.

Stored as sky_* fields on the shot; predict.py uses them once predict_coefs.json has a set with them
(analysis/horizons.py, after the history is filled: python -m ai_judge sky --camera all).
About 10-20 s per photo on the NUC's CPU, with the photo at 320 px as in the analysis.
"""

import base64
import io
import json
import logging
import os

import requests
from PIL import Image

from . import store, weather

log = logging.getLogger(__name__)

MODEL = os.environ.get("SKY_MODEL", "qwen3-vl:4b")
LABELS = {"02_1h_pre": "1 hour", "03_45m_pre": "45 minutes", "04_30m_pre": "30 minutes", "05_15m_pre": "15 minutes"}
WIDTH = 320

# analysis/vision_gap.py's prompt, with the time before sunset filled in per shot.
PROMPT = """This webcam photo was taken {when} before sunset, looking roughly toward where the sun will set.
Find the horizon toward the sun (the far shore, ridge or skyline), then look at the cloud deck above it and
at the strip of sky between the cloud base and the horizon. Answer in JSON:
horizon_found (true if you can see where land or water meets the sky),
cloud_cover (0-100, percent of the visible sky covered by cloud),
cloud_base (where the bottom of the main cloud deck sits in the frame: none, touching_horizon, low, mid, high),
gap (yes / no / unclear: is there a band of clear or bright sky between the cloud base and the horizon that the setting sun could shine through),
gap_thickness (0-100, that band's height as a percent of the sky's height in the frame; 0 if no gap),
clouds_overhead (true if there is cloud higher up that could catch the light),
underside_lit (likely / possible / unlikely: will the setting sun light the undersides of the clouds from below),
predicted_quality (0-100, 0 = grey/no colour, 100 = spectacular),
reason (one short sentence)."""
SCHEMA = {
    "type": "object",
    "properties": {
        "horizon_found": {"type": "boolean"}, "cloud_cover": {"type": "number"},
        "cloud_base": {"type": "string", "enum": ["none", "touching_horizon", "low", "mid", "high"]},
        "gap": {"type": "string", "enum": ["yes", "no", "unclear"]}, "gap_thickness": {"type": "number"},
        "clouds_overhead": {"type": "boolean"},
        "underside_lit": {"type": "string", "enum": ["likely", "possible", "unlikely"]},
        "predicted_quality": {"type": "number"}, "reason": {"type": "string"},
    },
    "required": ["horizon_found", "cloud_cover", "cloud_base", "gap", "gap_thickness", "clouds_overhead",
                 "underside_lit", "predicted_quality", "reason"],
}
LIT = {"unlikely": 0.0, "possible": 0.5, "likely": 1.0}  # floats: the first write fixes the field type


def ask(image_bytes, label, ollama_url):
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    img = img.resize((WIDTH, round(img.height * WIDTH / img.width)))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    body = {"model": MODEL, "stream": False, "think": False, "format": SCHEMA,
            "options": {"temperature": 0, "num_predict": 400},
            # qwen3-vl thinks even with think=False; an empty think block as the start of the answer skips it.
            "messages": [{"role": "user", "content": PROMPT.format(when=LABELS[label]),
                          "images": [base64.b64encode(buf.getvalue()).decode()]},
                         {"role": "assistant", "content": "<think>\n\n</think>\n\n"}]}
    resp = requests.post(f"{ollama_url.rstrip('/')}/api/chat", json=body, timeout=900)
    resp.raise_for_status()
    return json.loads(resp.json()["message"]["content"])


def fields(a):
    """The model's answer as sky_* fields, numbers clamped to 0-100."""
    clamp = lambda v: max(0.0, min(100.0, float(v)))
    return {"sky_model": MODEL, "sky_gap": a["gap"], "sky_gap_thickness": clamp(a["gap_thickness"]),
            "sky_cloud_cover": clamp(a["cloud_cover"]), "sky_cloud_base": a["cloud_base"],
            "sky_overhead": bool(a["clouds_overhead"]), "sky_lit": LIT.get(a["underside_lit"], 0.5),
            "sky_quality": clamp(a["predicted_quality"]), "sky_reason": str(a["reason"])[:200]}


def label_of(point):
    return next((l for l in LABELS if point.get("label", "").startswith(l)), None)


def fill(client, camera, ollama_url, recent=None, limit=None):
    """Read the sky on sunset-camera 1h/45m/30m/15m shots that don't have it yet, newest first."""
    if weather.camera_config(camera).get("MODE", "sunset") != "sunset":
        return 0
    todo = sorted((p for p in store.captures(client, camera, recent=recent)
                   if label_of(p) and (p.get("sky_model") != MODEL or (p.get("sky_gap") and p.get("sky_lit") is None))), key=lambda p: p["time"], reverse=True)[:limit]
    done = 0
    for p in todo:
        try:
            a = ask(store.image_bytes(p), label_of(p), ollama_url)
            client.write_points([store.field_point(p, fields(a))])
            done += 1
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 404 and not e.request.url.endswith("/api/chat"):
                client.write_points([store.field_point(p, {"sky_model": MODEL})])  # photo gone: don't retry
            else:
                log.warning("%s: sky read failed for %s: %s", camera, p.get("url"), e)
        except (requests.RequestException, ValueError, KeyError, TypeError) as e:
            log.warning("%s: sky read failed for %s: %s", camera, p.get("url"), e)
    if todo:
        log.info("%s: sky read on %d of %d shots (%s)", camera, done, len(todo), MODEL)
    return done
