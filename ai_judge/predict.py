"""A simple sunset forecast, written onto the 2h-pre and 1h-pre captures as predicted_score
(0-100) and predicted_class (good / maybe / poor).

From analysis/REPORT.md: the best weather signal for the day's HSV score is a clear path toward
the sun. clear = share of the stored path points (13 / 40 / 80 km toward the sun) with low cloud
< 20% and mid cloud < 30%; humid air mutes the colour a little more:

    raw = clear - 0.5 * relative_humidity / 100        (-0.5 .. 1)

On ~560 days of history (1h-pre reading vs the best score from 15 min before to 30 min after):
raw <= 0 -> median day in its camera's 25th percentile, 8% top-quarter days; raw > 0.6 -> 70th
percentile, 41% top-quarter days. Those cut points are the class thresholds.
"""

import logging

from . import store

log = logging.getLogger(__name__)

LABELS = ("01_2h_pre", "02_1h_pre")
PATH_KM = (13, 40, 80)
GOOD, POOR = 73, 34  # predicted_score at raw = 0.6 and raw = 0.0


def simple_score(point):
    """(predicted_score, predicted_class) from a capture's stored weather, or None if it has none."""
    try:
        clear = sum(point[f"path{km}_cloud_cover_low"] < 20 and point[f"path{km}_cloud_cover_mid"] < 30
                    for km in PATH_KM) / len(PATH_KM)
        raw = clear - 0.5 * point["relative_humidity_2m"] / 100
    except (KeyError, TypeError):
        return None
    score = round(max(0.0, min(100.0, (raw + 0.5) / 1.5 * 100)), 1)
    return score, "good" if score >= GOOD else "poor" if score < POOR else "maybe"


def fill(client, camera, since=None, before=None, refill=False):
    """Add the forecast to 2h/1h-pre captures that have weather but no forecast yet."""
    writes = []
    for p in store.captures(client, camera, since=since, before=before):
        if not p.get("label", "").startswith(LABELS) or (p.get("predicted_score") is not None and not refill):
            continue
        result = simple_score(p)
        if result:
            writes.append(store.field_point(p, {"predicted_score": result[0], "predicted_class": result[1]}))
    if writes:
        client.write_points(writes, batch_size=1000)
    log.info("%s: forecast added to %d captures", camera, len(writes))
    return len(writes)
