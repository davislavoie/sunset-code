"""Ask a local vision model (Ollama) to forecast the sunset from a pre-sunset photo.

Photos are re-downloaded at 640 px from the image server (the 320 px thumbs are small for a model),
answers are appended to analysis_export/vision_<model>.jsonl so a run can be stopped and resumed.

    python analysis/vision.py qwen3-vl:4b 02_1h_pre [limit]
"""

import base64
import io
import json
import sys
import time
import urllib.parse

import requests
from PIL import Image

import data

OLLAMA = "http://localhost:11434"
BASE = "http://100.107.153.41:8080"
PROMPT = """This webcam photo was taken {when} before sunset, looking roughly toward where the sun will set.
Forecast how colourful the sunset will be (vivid red, orange, pink and purple in the sky), judging from
the clouds, haze and the sky toward the horizon. Answer in JSON:
predicted_quality (0-100, 0 = grey/no colour, 100 = spectacular),
cloud_cover (0-100, percent of the visible sky covered by cloud),
cloud_type (one of: clear, high_thin, mid_broken, low_thick, overcast, mixed),
horizon_clear (true if the sky near the horizon toward the sun looks open enough for sunlight to get under the clouds),
reason (one short sentence)."""
SCHEMA = {
    "type": "object",
    "properties": {
        "predicted_quality": {"type": "number"},
        "cloud_cover": {"type": "number"},
        "cloud_type": {"type": "string", "enum": ["clear", "high_thin", "mid_broken", "low_thick", "overcast", "mixed"]},
        "horizon_clear": {"type": "boolean"},
        "reason": {"type": "string"},
    },
    "required": ["predicted_quality", "cloud_cover", "cloud_type", "horizon_clear", "reason"],
}
WHEN = {"01_2h_pre": "2 hours", "02_1h_pre": "1 hour", "04_30m_pre": "30 minutes"}


def photo(url, width=640):
    raw = requests.get(BASE + urllib.parse.urlparse(url).path, timeout=60).content
    img = Image.open(io.BytesIO(raw)).convert("RGB")
    img = img.resize((width, round(img.height * width / img.width)))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def ask(model, label, image_b64):
    body = {"model": model, "stream": False, "think": False, "format": SCHEMA, "options": {"temperature": 0},
            "messages": [{"role": "user", "content": PROMPT.format(when=WHEN[label]), "images": [image_b64]}]}
    resp = requests.post(f"{OLLAMA}/api/chat", json=body, timeout=900)
    if resp.status_code == 400 and "think" in resp.text:
        del body["think"]
        resp = requests.post(f"{OLLAMA}/api/chat", json=body, timeout=900)
    resp.raise_for_status()
    return json.loads(resp.json()["message"]["content"])


def run(model, label, limit=None):
    out = data.EXPORT / f"vision_{model.replace(':', '_')}.jsonl"
    done = set()
    if out.exists():
        done = {(r["camera"], r["day"], r["label"]) for r in map(json.loads, out.read_text().splitlines())}
    cap = data.captures()
    days = data.days(cap)
    keep = set(map(tuple, days[days.camera.isin(data.SUNSET_CAMS)][["camera", "day"]].astype(str).values))
    todo = cap[(cap.label == label) & cap.camera.isin(data.SUNSET_CAMS)]
    todo = todo[[(c, str(d)) in keep and (c, str(d), label) not in done for c, d in zip(todo.camera, todo.day)]]
    # Spread a partial run over the whole history rather than the oldest days.
    todo = todo.sample(frac=1, random_state=0)
    if limit:
        todo = todo.head(limit)
    print(f"{len(todo)} photos to judge", flush=True)
    with out.open("a") as f:
        for i, r in enumerate(todo.itertuples(), 1):
            t0 = time.time()
            try:
                ans = ask(model, label, photo(r.url))
            except Exception as e:  # skip a bad photo / answer, keep going
                print("fail", r.camera, r.day, e, flush=True)
                continue
            rec = {"camera": r.camera, "day": str(r.day), "label": label, "sec": round(time.time() - t0, 1), **ans}
            f.write(json.dumps(rec) + "\n")
            f.flush()
            print(i, rec["camera"], rec["day"], rec["sec"], "s", rec["predicted_quality"], rec["cloud_type"], flush=True)


if __name__ == "__main__":
    run(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else None)
