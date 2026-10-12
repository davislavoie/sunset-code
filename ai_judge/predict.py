"""Sunset forecast at every pre shot (2h, 1h, 45m, 30m, 15m, 5m before), written onto that capture:

  predicted_pct    0-100: where the day's best score should land among this camera's past days
  predicted_score  that percentile as an HSV score (the camera's past daily bests), to compare with the actual
  predicted_call   poor / maybe / good / banger

Inputs are only what's known at that shot (analysis/REPORT.md, analysis/horizons.md):
  weather = clear-path share - 0.5 * RH/100, where the clear-path share is the share of the stored
            path points (13 / 40 / 80 km toward the sun) with low cloud < 20% and mid cloud < 30%
  cur_pct = this shot's HSV score as a percentile of the camera's past daily-best scores
  max_pct = the best shot so far today, on the same scale
One straight line per horizon (predict_coefs.json, fitted by analysis/horizons.py) turns those
into predicted_pct. The day's actual score is its best shot from 15m pre to 30m post.
"""

import bisect
import json
import logging
from pathlib import Path

from . import store

log = logging.getLogger(__name__)

PATH_KM = (13, 40, 80)
HORIZONS = ("01_2h_pre", "02_1h_pre", "03_45m_pre", "04_30m_pre", "05_15m_pre", "06_5m_pre")
WINDOW = ("05_15m_pre", "06_5m_pre", "07_sunset", "07_sunrise", "08_5m_post", "09_15m_post", "10_30m_post")
COEFS = json.loads((Path(__file__).with_name("predict_coefs.json")).read_text())["coefs"]
# predicted_pct cut points for the calls (calibrated in analysis/horizons.md)
POOR, GOOD, BANGER = 0.35, 0.6, 0.8
MIN_DAYS = 10  # need this many past days to turn scores into percentiles


def weather_raw(point):
    """clear-path share - 0.5 * RH/100 (-0.5 .. 1), or None if the capture has no weather yet."""
    try:
        clear = sum(point[f"path{km}_cloud_cover_low"] < 20 and point[f"path{km}_cloud_cover_mid"] < 30
                    for km in PATH_KM) / len(PATH_KM)
        return clear - 0.5 * point["relative_humidity_2m"] / 100
    except (KeyError, TypeError):
        return None


def percentile(history, score):
    """Share of past daily bests (sorted) at or below score."""
    return bisect.bisect_right(history, score or 0) / len(history)


def call(p):
    return "banger" if p >= BANGER else "good" if p >= GOOD else "poor" if p < POOR else "maybe"


def forecast(horizon, weather, cur_pct, max_pct):
    c = COEFS[horizon]
    return min(1.0, max(0.0, c[0] + c[1] * weather + c[2] * cur_pct + c[3] * max_pct))


def label_of(point):
    return next((h for h in HORIZONS if point.get("label", "").startswith(h)), None)


def daily_bests(points):
    """Each past day's best score in the sunset window, among shots allowed to be the best."""
    best = {}
    for p in points:
        if p.get("label", "").startswith(WINDOW) and not store.exclusion(p):
            day = store.local_date(p)
            best[day] = max(best.get(day, 0), p.get("score") or 0)
    return best


def fill(client, camera, since=None, before=None, refill=False):
    """Add the forecast to pre shots that have weather but no forecast yet."""
    points = store.captures(client, camera)
    bests = daily_bests(points)
    writes = []
    for day, day_points in store.by_day(points).items():
        if (since and day < since) or (before and day >= before):
            continue
        # Only earlier days count as history, as it would have been live.
        history = sorted(v for d, v in bests.items() if d < day)
        if len(history) < MIN_DAYS:
            continue
        seen = 0
        for p in sorted((p for p in day_points if label_of(p)), key=lambda p: HORIZONS.index(label_of(p))):
            # A shot that can't be the day's best (thumbs down, blocked view) counts as 0, as on the dashboard.
            shot = 0 if store.exclusion(p) else p.get("score") or 0
            seen = max(seen, shot)
            weather = weather_raw(p)
            if weather is None or (p.get("predicted_pct") is not None and not refill):
                continue
            pct = forecast(label_of(p), weather, percentile(history, shot), percentile(history, seen))
            score = history[min(len(history) - 1, int(pct * len(history)))]
            writes.append(store.field_point(p, {"predicted_pct": round(100 * pct, 1),
                                                "predicted_score": round(float(score), 2),
                                                "predicted_call": call(pct)}))
    if writes:
        client.write_points(writes, batch_size=1000)
    log.info("%s: forecast added to %d pre shots", camera, len(writes))
    return len(writes)
