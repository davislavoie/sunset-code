"""Non-interactive re-ranking of sunset days, from InfluxDB.

For each day: optionally re-score every capture with the current HSV code,
skip captures the AI judged aren't the sky, pick the highest HSV score, and
regenerate that day's ranked image + histogram with the pipeline's own
functions (rank_sunset, generate_ranked_image, influxdb_push), unchanged.
If no capture that day shows the sky, the day's ranking is removed so it
doesn't count at all.

Unlike tests/re_rank_sunsets.py it never deletes captures (so AI judgments
survive), and it can target a date range.
"""

import glob
import logging
import os

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


def is_sky(point):
    """Not judged yet counts as sky: only a confirmed 'not the sky' is excluded."""
    return point.get("ai_is_sunset") is not False


def rerank_day(client, camera, day_points, pipeline, rescore=False, use_ai=True, dry_run=False, fill_missing=False):
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

    candidates = [p for p in captures if not use_ai or is_sky(p)]
    if not candidates:
        if not ranked:
            return "no sky captures (nothing ranked)"
        if dry_run:
            return "no sky captures: would remove this day's ranking"
        remove_ranked(client, camera, ranked)
        return "no sky captures: ranking removed"

    best = max(candidates, key=lambda p: p.get("score") or 0)
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
        client.query(
            f"DELETE FROM {store.MEASUREMENT} WHERE camera = $camera AND label = $label AND time = '{p['time']}'",
            bind_params={"camera": camera, "label": p["label"]},
        )
        try:
            os.remove(store.local_path(p))
        except (OSError, ValueError):
            pass  # file already gone or not on this machine; the point is what matters


def rerank(client, camera, since=None, before=None, rescore=False, use_ai=True, dry_run=False, fill_missing=False, pipeline=None):
    pipeline = pipeline or (None if dry_run and not rescore else Pipeline())
    days = store.by_day(store.points(client, camera, since=since, before=before))
    log.info("%s: re-ranking %d days%s", camera, len(days), " (dry run)" if dry_run else "")
    for day, day_points in sorted(days.items()):
        try:
            log.info("%s %s: %s", camera, day, rerank_day(client, camera, day_points, pipeline, rescore, use_ai, dry_run, fill_missing))
        except Exception:
            log.exception("%s %s: re-rank failed", camera, day)


def gate_recent_days(client, camera, pipeline_factory=Pipeline):
    """After the AI has judged a finished day, make sure its best shot is actually the sky.
    Only touches days where every capture is judged and the pipeline's pick was judged
    'not the sky'; otherwise does nothing. Safe to call repeatedly."""
    pipeline = None
    for day, day_points in sorted(store.by_day(store.points(client, camera, recent="2d")).items()):
        captures = [p for p in day_points if store.is_raw_capture(p)]
        best_time = next((p["time"] for p in day_points if store.is_ranked(p)), None)
        if not best_time or any(p.get("ai_model") is None for p in captures):
            continue  # day still in progress, or not fully judged yet
        best = next((p for p in captures if p["time"] == best_time), None)
        if best is None or is_sky(best):
            continue
        pipeline = pipeline or pipeline_factory()
        log.info("%s %s: best shot isn't the sky; %s", camera, day, rerank_day(client, camera, day_points, pipeline))
