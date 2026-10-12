"""Glass-lake badge: btv_echo_cam shots where the lake mirrors the sky.

The camera cycles PTZ presets, so there's no fixed sky / lake region. Each frame (shrunk to 320 px wide)
is searched for the row that best acts as a mirror: the vertical colour gradients in the K rows above it,
flipped, against the K rows below. A reflection flips them; posts, masts and trees (no vertical gradient)
and the plain sky-to-ground brightness ramp (removed per row) don't count as mirroring. Tuned on 335 btv
days (analysis/reflection.py): the mirror-calm Jan 8 2026 lake scored 0.58, median 0.19, and >= 0.35
(about 4 % of days) were mostly genuine reflections. Badge plus a small bump when picking and
showing the day's best (store.glass_bonus); the stored HSV score is never changed.
"""

import io
import logging

import numpy as np
import requests
from PIL import Image

from . import store

log = logging.getLogger(__name__)

CAMERAS = {"btv_echo_cam"}
GLASS_LAKE = store.GLASS_BONUS[-1][0]  # badge threshold = smallest bump
K = 12  # rows compared on each side of the mirror line, at 320 px wide


def mirror_score(image_bytes):
    """(best correlation, mirror row as a fraction of height); (-1.0, None) for a featureless frame."""
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    if img.width != 320:
        img = img.resize((320, max(2 * K + 2, round(img.height * 320 / img.width))), Image.BILINEAR)
    g = np.asarray(img, dtype=float)
    dy = np.diff(g - g.mean(axis=1, keepdims=True), axis=0)
    best = (-1.0, None)
    for h in range(max(K, int(.3 * len(dy))), min(len(dy) - K - 1, int(.8 * len(dy)))):
        a, b = -dy[h - K:h][::-1].ravel(), dy[h + 1:h + 1 + K].ravel()
        if a.std() < 1 or b.std() < 1:  # flat fog / dark frames
            continue
        r = float(np.corrcoef(a, b)[0, 1])
        if r > best[0]:
            best = (r, h / len(dy))
    return best


def fill(client, camera):
    """Score captures that don't have a mirror_score yet (all of history the first time)."""
    if camera not in CAMERAS:
        return 0
    todo = [p for p in store.captures(client, camera) if p.get("mirror_score") is None]
    writes = []
    for p in todo:
        try:
            score, _ = mirror_score(store.image_bytes(p))
        except requests.HTTPError as e:
            if e.response is None or e.response.status_code != 404:
                log.warning("Can't score %s: %s", p.get("url"), e)
                continue
            score = -1.0  # photo gone from disk: don't retry
        except Exception as e:  # image server down, bad file: try again next pass
            log.warning("Can't score %s: %s", p.get("url"), e)
            continue
        writes.append(store.field_point(p, {"mirror_score": round(score, 3), "glass_lake": score >= GLASS_LAKE}))
        if len(writes) >= 200:
            client.write_points(writes)
            writes = []
    if writes:
        client.write_points(writes)
    if todo:
        log.info("%s: mirror-scored %d captures", camera, len(todo))
    return len(todo)
