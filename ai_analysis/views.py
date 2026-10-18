""""All shots like this": a thumbed-down capture marked bad_view rules out every
near-identical shot from the same camera (e.g. Bolton's lift-tower close-up preset).

Each capture gets a small fingerprint of its lower part (the fixed scenery; the sky
changes), as edge strengths so lighting doesn't matter much. Two shots of the same
view score >= SIMILAR (cosine similarity). Tuned on Bolton: tower-view shots scored
0.45-1.0 against a tower exemplar, every other view 0.31 or less.
"""

import base64
import io
import logging

import numpy as np
import requests
from PIL import Image

from . import store

log = logging.getLogger(__name__)

SIMILAR = 0.4
# Per-camera cutoffs. btv_echo_cam: lake views matched its brick-building exemplars at 0.40-0.42,
# real matches start at 0.48. Bolton stays at 0.4: its tower in fog only scores 0.41-0.44.
SIMILAR_BY_CAMERA = {"btv_echo_cam": 0.45}
GRID = (48, 18)  # fingerprint resolution (width, height) of the frame's lower 60%


def fingerprint(image_bytes):
    """Base64 int8 vector, or "" for a blank/black frame (no edges to compare)."""
    img = Image.open(io.BytesIO(image_bytes)).convert("L")
    w, h = img.size
    a = np.asarray(img.crop((0, int(h * 0.4), w, h)).resize(GRID, Image.BILINEAR), float)
    edges = np.hypot(np.diff(a, axis=1)[:-1], np.diff(a, axis=0)[:, :-1]).ravel()
    edges -= edges.mean()
    peak = np.abs(edges).max()
    if peak < 1e-6:
        return ""
    return base64.b64encode((edges / peak * 127).astype(np.int8).tobytes()).decode("ascii")


def vector(fp):
    v = np.frombuffer(base64.b64decode(fp), np.int8).astype(float)
    n = np.linalg.norm(v)
    return v / n if n else None


def fill_fingerprints(client, camera):
    """Fingerprint captures that don't have one yet (all of history the first time)."""
    todo = [p for p in store.captures(client, camera) if p.get("view_fp") is None]
    writes = []
    for p in todo:
        try:
            writes.append(store.field_point(p, {"view_fp": fingerprint(store.image_bytes(p))}))
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                # The photo is gone from disk (InfluxDB still lists it): nothing to compare, don't retry.
                log.warning("No photo for %s; skipping it from now on", p.get("url"))
                writes.append(store.field_point(p, {"view_fp": ""}))
            else:
                log.warning("Can't fingerprint %s: %s", p.get("url"), e)
        except Exception as e:  # image server down, bad file: try again next pass
            log.warning("Can't fingerprint %s: %s", p.get("url"), e)
        if len(writes) >= 200:
            client.write_points(writes)
            writes = []
    if writes:
        client.write_points(writes)
    if todo:
        log.info("%s: fingerprinted %d captures", camera, len(todo))


def blocked_flags(captures, similar=SIMILAR):
    """{time: view_blocked} for captures whose view matches a bad_view exemplar."""
    exemplars = [v for p in captures if p.get("bad_view") and p.get("view_fp") and (v := vector(p["view_fp"])) is not None]
    flags = {}
    for p in captures:
        v = vector(p["view_fp"]) if p.get("view_fp") else None
        flags[p["time"]] = bool(v is not None and exemplars and max(float(v @ e) for e in exemplars) >= similar)
    return flags


def apply_bad_views(client, camera):
    """Set view_blocked on the camera's captures to match the current bad_view exemplars.
    Writes only what changed; returns how many changed."""
    captures = store.captures(client, camera)
    flags = blocked_flags(captures, SIMILAR_BY_CAMERA.get(camera, SIMILAR))
    writes = [store.field_point(p, {"view_blocked": flags[p["time"]]}) for p in captures
              if bool(p.get("view_blocked")) != flags[p["time"]]]
    if writes:
        client.write_points(writes, batch_size=1000)
        log.info("%s: %d captures changed 'same view as a thumbed-down shot'", camera, len(writes))
    return len(writes)
