"""Non-interactive re-ranking of sunset days, from InfluxDB.

For each day: optionally re-score every capture with the current HSV code,
skip captures that can't win (store.exclusion: thumbs down, same view as a
thumbed-down shot, dark / no signal), pick a thumbs-up capture if there is one,
else the highest HSV score plus the glass-lake bump (store.glass_bonus), and
regenerate that day's ranked image + histogram with the pipeline's own functions
(rank_sunset, generate_ranked_image, influxdb_push), unchanged. If no capture that day can win, the day's ranking is
removed so it doesn't count at all.

Unlike tests/re_rank_sunsets.py it never deletes captures (so thumbs, weather and
AI fields survive), and it can target a date range.
"""

import glob
import logging
import os
from datetime import datetime

from . import store

log = logging.getLogger(__name__)


class Pipeline:
    """The capture pipeline's functions, imported only when a re-rank actually runs
    (they need OpenCV, matplotlib, astral...)."""

    def __init__(self):
        from sunset_code.helpers.generate_ranked_image import generate_ranked_image
        from sunset_code.helpers.helpers import influxdb_push
        from sunset_code.helpers.sunset_process import rank_sunset

        self.rank_sunset = rank_sunset
        self.generate_ranked_image = generate_ranked_image
        self.influxdb_push = influxdb_push


def pick(captures, use_rules=True):
    """The day's best shot, or None if no capture can win."""
    candidates = [p for p in captures if not use_rules or not store.exclusion(p)]
    liked = [p for p in candidates if (p.get("thumb") or 0) > 0]
    return max(liked or candidates, key=lambda p: (p.get("score") or 0) + store.glass_bonus(p), default=None)


def rerank_day(client, camera, day_points, pipeline, rescore=False, use_rules=True, dry_run=False, fill_missing=False):
    """Re-pick one day's best shot. day_points: all of that day's points (captures + ranked).
    Returns a short description of what happened (or would happen, with dry_run)."""
    captures = [p for p in day_points if store.is_raw_capture(p)]
    ranked = [p for p in day_points if not store.is_raw_capture(p)]
    current = next((p["time"] for p in ranked if store.is_ranked(p)), None)
    if current is None and not fill_missing:
        # The pipeline never ranked this day (e.g. its ranked-image step failed); leave it unless asked.
        return "not ranked; skipped (--fill-missing ranks it)"

    if rescore and not dry_run:
        for p in captures:
            score = float(pipeline.rank_sunset(store.local_path(p))[0])
            if score != p.get("score"):
                store.save_fields(client, p, {"score": score})
                p["score"] = score

    best = pick(captures, use_rules)
    if best is None:
        if not ranked:
            return "no eligible captures (nothing ranked)"
        if dry_run:
            return "no eligible captures: would remove this day's ranking"
        remove_ranked(client, camera, ranked)
        return "no eligible captures: ranking removed"
    if best["time"] == current and not rescore:
        return f"unchanged: {best['label']} ({best.get('score', 0):.1f})"
    if dry_run:
        return f"would pick {best['label']} ({best.get('score', 0):.1f})" + (f", was {current}" if current else "")

    path = store.local_path(best)
    score, final_txt_img, name, hist_h, hist_s, hist_v, *_ = pipeline.rank_sunset(path)
    photo_dir = os.path.dirname(path)
    for old in glob.glob(os.path.join(photo_dir, "11_*.png")) + glob.glob(os.path.join(photo_dir, "12_*.png")):
        os.remove(old)
    histogram_path, ranked_path = pipeline.generate_ranked_image(final_txt_img, score, name, hist_h, hist_s, hist_v, photo_dir)
    epoch = store.epoch_seconds(best)
    # Same order as the pipeline: pushing the 12_ histogram first makes influxdb_push delete this
    # day's old 11_/12_ points (it clears that window), then the new 11_ is written.
    pipeline.influxdb_push(histogram_path, epoch, os.path.basename(histogram_path), camera, score)
    pipeline.influxdb_push(ranked_path, epoch, os.path.basename(ranked_path), camera, score)
    return f"picked {best['label']} ({float(score):.1f})" + (f", was {current}" if current and current != best["time"] else "")


def remove_ranked(client, camera, ranked):
    """Delete a day's 11_/12_ points (and their files) so the day isn't ranked."""
    for p in ranked:
        store.delete_point(client, p)
        try:
            os.remove(store.local_path(p))
        except (OSError, ValueError):
            pass  # file already gone or not on this machine; the point is what matters


def rerank(client, camera, since=None, before=None, rescore=False, use_rules=True, dry_run=False, fill_missing=False, pipeline=None):
    pipeline = pipeline or (None if dry_run and not rescore else Pipeline())
    days = store.by_day(store.points(client, camera, since=since, before=before))
    log.info("%s: re-ranking %d days%s", camera, len(days), " (dry run)" if dry_run else "")
    for day, day_points in sorted(days.items()):
        try:
            log.info("%s %s: %s", camera, day, rerank_day(client, camera, day_points, pipeline, rescore, use_rules, dry_run, fill_missing))
        except Exception:
            log.exception("%s %s: re-rank failed", camera, day)


def gate_days(client, camera, pipeline_factory=Pipeline):
    """Re-pick every ranked day whose best shot no longer matches the rules (a thumbs up or
    down, a bad view, a dark frame). Days already right are left alone, so it's cheap to run
    every pass. An unranked day is only ranked again if the rules un-ranked it and a vote
    since then brought a capture back; days the pipeline never ranked (today, still
    capturing, or its ranked-image step failed) are left alone."""
    pipeline = None
    today = datetime.now(store.LOCAL_TZ).date()
    for day, day_points in sorted(store.by_day(store.points(client, camera)).items()):
        captures = [p for p in day_points if store.is_raw_capture(p)]
        current = next((p["time"] for p in day_points if store.is_ranked(p)), None)
        best = pick(captures)
        if current is None and not (day < today and best and any(voted(p) for p in captures)):
            continue
        if best is not None and best["time"] == current:
            continue
        pipeline = pipeline or pipeline_factory()
        msg = rerank_day(client, camera, day_points, pipeline, fill_missing=True)
        log.info("%s %s: best shot changed; %s", camera, day, msg)


def voted(point):
    """The thumbs/view rules have touched this capture (even if since cleared back to 0/false)."""
    return point.get("thumb") is not None or point.get("view_blocked") is not None
