"""Horizon light band on the pre shots: how much brighter the sky just above the horizon is than the sky
higher up. A bright strip under the clouds is the gap the setting sun shines through (analysis/horizon_band.md:
rho 0.39 with the day's score; adds to the forecast at 1h and 30m pre).

Same maths as analysis/horizon_band.py on the 320 px thumbs: the horizon is found per frame (the camera drifts
between presets), band = the 8 % of sky just above it, sky = 15-60 % of the way down to it, 0-1 brightness.
Stored as horizon_lift on each pre shot; predict.py uses it.
"""

import io
import logging

import numpy as np
import requests
from PIL import Image

from . import predict, store

log = logging.getLogger(__name__)

TEX = 0.012   # gradient that counts as texture (analysis/horizon_gap.py)
SHARE = 0.4   # horizon = topmost row whose frame-wide edge is at least this share of the strongest
GONE = -9.0   # stored when the photo is gone; real values are within -1..1, and predict.py skips it


def horizon(v):
    """Topmost strong, frame-wide edge with sky above it: darker or busier below than above (horizon_gap.py)."""
    gy, gx = np.gradient(v)
    tex = np.hypot(gx, gy) > TEX
    edge = np.convolve(np.median(np.abs(np.diff(v, axis=0)), axis=1), np.ones(3) / 3, mode="same")
    lo, hi = int(.2 * len(v)), int(.85 * len(v))
    strong = [r for r in range(lo, hi) if edge[r] >= SHARE * edge[lo:hi].max()]
    for r in strong:
        above, below = slice(max(0, r - 15), r - 1), slice(r + 2, r + 17)
        if (v[above].mean() - v[below].mean()) + (tex[below].mean() - tex[above].mean()) >= 0.05:
            return r
    return strong[0]


def horizon_lift(image_bytes):
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB").resize((320, 180), Image.BILINEAR)
    v = np.asarray(img, dtype=float).mean(axis=2) / 255
    h = horizon(v)
    band = v[max(0, h - int(.08 * h) - 3):h - 3]
    sky = v[int(.15 * h):int(.6 * h)]
    return float(band.mean() - sky.mean())


def fill(client, camera):
    """Add horizon_lift to pre shots that don't have it (all of history the first time)."""
    todo = [p for p in store.captures(client, camera)
            if predict.label_of(p) and p.get("horizon_lift") is None]
    writes = []
    for p in todo:
        try:
            lift = horizon_lift(store.image_bytes(p))
        except requests.HTTPError as e:
            if e.response is None or e.response.status_code != 404:
                log.warning("Can't read %s: %s", p.get("url"), e)
                continue
            lift = GONE  # photo gone from disk: don't retry
        except Exception as e:  # image server down, bad file: try again next pass
            log.warning("Can't read %s: %s", p.get("url"), e)
            continue
        writes.append(store.field_point(p, {"horizon_lift": round(lift, 4)}))
        if len(writes) >= 200:
            client.write_points(writes)
            writes = []
    if writes:
        client.write_points(writes)
    if todo:
        log.info("%s: horizon band on %d pre shots", camera, len(todo))
    return len(todo)
