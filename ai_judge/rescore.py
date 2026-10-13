"""Rescore captures in place with the current sunset_process.py, and remove the old ranked images.

rescore() rewrites each capture's score, its breakdown fields and its histograms on the same point (same
measurement, tags and time). InfluxDB merges fields, so thumbs, weather, AI verdicts and everything else on
the capture stay. Nothing is deleted and no images are made: the dashboard picks each day's best shot from
the scores when it reads them (html_project/backend.py).

drop_ranked() removes the 11_ranked / 12_histogram points and PNGs the pipeline used to make.
"""

import json
import logging
import os

from . import store

log = logging.getLogger(__name__)

BATCH = 500  # points per InfluxDB write


def rescore(client, camera, since=None, before=None, dry_run=False, rank_sunset=None):
    if rank_sunset is None:  # imported only when it runs (needs OpenCV)
        from sunset_code.helpers.sunset_process import rank_sunset
    caps = store.captures(client, camera, since=since, before=before)
    log.info("%s: rescoring %d captures%s", camera, len(caps), " (dry run)" if dry_run else "")
    pending, moved = [], []
    for i, p in enumerate(caps, 1):
        try:
            result = rank_sunset(store.local_path(p))
        except Exception:
            log.exception("%s %s %s: rescore failed", camera, p["time"], p["label"])
            continue
        if result is None:  # photo missing or unreadable; `cleanup` lists those
            continue
        score, fields, hist = result
        moved.append(abs(score - (p.get("score") or 0)))
        pending += [store.field_point(p, {"score": float(score), **fields}),
                    {"measurement": store.HIST_MEASUREMENT, "tags": {"label": p["label"], "camera": p["camera"]},
                     "time": p["time"], "fields": {"hist": json.dumps(hist, separators=(",", ":"))}}]
        if len(pending) >= BATCH:
            flush(client, pending, dry_run)
            log.info("%s: %d / %d", camera, i, len(caps))
    flush(client, pending, dry_run)
    if moved:
        log.info("%s: %d captures %s, mean change %.1f points, biggest %.1f", camera, len(moved),
                 "would change" if dry_run else "rescored", sum(moved) / len(moved), max(moved))


def flush(client, pending, dry_run):
    if pending and not dry_run:
        client.write_points(pending)
    pending.clear()


def drop_ranked(client, camera, delete=False):
    """The 11_/12_ points and their PNG files. Lists them; delete=True removes them."""
    ranked = [p for p in store.points(client, camera) if not store.is_raw_capture(p)]
    log.info("%s: %d ranked/histogram points %s", camera, len(ranked),
             "deleting" if delete else "would be deleted (dry run; add --delete)")
    if not delete or not ranked:
        return
    client.query(f"DELETE FROM {store.MEASUREMENT} WHERE camera = $camera AND label =~ /^1[12]_/",
                 bind_params={"camera": camera})
    for p in ranked:
        try:
            os.remove(store.local_path(p))
        except (OSError, ValueError):
            pass  # already gone or not on this machine; the point is what matters
