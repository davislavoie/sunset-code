"""Local AI judge for sunset captures. A sidecar to the capture pipeline: it reads
captures from InfluxDB, asks a local vision model about each one, and writes
ai_* fields back. It never changes the pipeline's own data or code.

  python -m ai_judge watch      # keep judging new captures; re-pick a day's best shot if it isn't the sky
  python -m ai_judge backfill --camera btv_echo_cam [--since 2025-07-01] [--before 2025-08-01] [--best-only] [--limit N] [--rejudge]
  python -m ai_judge rerank   --camera btv_echo_cam [--since ...] [--before ...] [--rescore] [--ignore-ai] [--fill-missing] [--dry-run]
  python -m ai_judge bakeoff  --camera btv_echo_cam --models qwen3-vl:4b,gemma3:4b [--sample 12] [--dates 2025-05-26,...]

Dates are the cameras' local dates (TIMEZONE, default America/New_York): --since is
inclusive, --before is exclusive. --camera all runs every camera.

Config (env): OLLAMA_URL, AI_MODEL, INFLUXDB_HOST, INFLUXDB_PORT, IMAGE_BASE_URL,
IMAGE_FETCH_URL, PICTURES_DIR, TIMEZONE.
"""

import argparse
import html
import logging
import os
import random
import time
from datetime import date
from pathlib import Path

from influxdb import InfluxDBClient

from . import store
from .judge import ensure_model, judge_image
from .rerank import gate_recent_days, rerank

log = logging.getLogger("ai_judge")

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
AI_MODEL = os.environ.get("AI_MODEL", "qwen3-vl:4b")
WATCH_INTERVAL_S = int(os.environ.get("WATCH_INTERVAL_S", 600))


def influx():
    return InfluxDBClient(
        host=os.environ.get("INFLUXDB_HOST", "localhost"),
        port=int(os.environ.get("INFLUXDB_PORT", 8086)),
        database="sunset_images",
    )


def judge_and_save(client, point, model):
    """Judge one capture and store the result. Returns the result, or None to retry later."""
    try:
        image = store.image_bytes(point)
    except Exception as e:  # missing file, image server down: try again next pass
        log.warning("Can't fetch %s: %s", point.get("url"), e)
        return None
    started = time.monotonic()
    result = judge_image(image, model, OLLAMA_URL)
    if result:
        store.save_judgment(client, point, result, model)
        log.info("%s %s %s: %s %d (%.0fs) %s", point["camera"], point["time"], point["label"],
                 result["view"], result["score"], time.monotonic() - started, result["reason"])
    return result


def watch(_args):
    client = influx()
    ensure_model(AI_MODEL, OLLAMA_URL)
    log.info("Watching for new captures every %ds with %s", WATCH_INTERVAL_S, AI_MODEL)
    while True:
        try:
            for camera in store.cameras(client):
                for point in store.captures(client, camera, recent="2d"):
                    if store.needs_judging(point, AI_MODEL):
                        judge_and_save(client, point, AI_MODEL)
                # A finished day whose best shot turned out not to be the sky gets a new best
                # shot from its real-sky captures (or no ranking at all if there are none).
                gate_recent_days(client, camera)
        except Exception:
            log.exception("Watch pass failed; retrying next interval")
        time.sleep(WATCH_INTERVAL_S)


def camera_list(client, camera):
    known = store.cameras(client)
    if camera == "all":
        return known
    if camera not in known:
        raise SystemExit(f"Unknown camera {camera!r}. Cameras: {', '.join(known)} (or 'all')")
    return [camera]


def backfill(args):
    client = influx()
    ensure_model(AI_MODEL, OLLAMA_URL)
    for camera in camera_list(client, args.camera):
        points = store.captures(client, camera, since=args.since, before=args.before)
        if args.best_only:
            best = store.best_shot_times(client, camera)
            points = [p for p in points if p["time"] in best]
        todo = [p for p in points if store.needs_judging(p, AI_MODEL, args.rejudge)]
        if args.limit:
            todo = todo[: args.limit]
        log.info("%s: %d of %d captures to judge with %s", camera, len(todo), len(points), AI_MODEL)
        for i, point in enumerate(todo, 1):
            log.info("[%d/%d]", i, len(todo))
            judge_and_save(client, point, AI_MODEL)


def rerank_cmd(args):
    client = influx()
    for camera in camera_list(client, args.camera):
        rerank(client, camera, since=args.since, before=args.before, rescore=args.rescore,
               use_ai=not args.ignore_ai, dry_run=args.dry_run, fill_missing=args.fill_missing)


def bakeoff(args):
    """Compare models on a sample without writing anything to InfluxDB. Writes an HTML
    contact sheet (photo + each model's verdict and time) to --out."""
    client = influx()
    models = [m.strip() for m in args.models.split(",") if m.strip()]
    points = store.captures(client, args.camera)
    if args.dates:
        wanted = set(args.dates.split(","))
        sample = [p for p in points if any(p["time"].startswith(d) for d in wanted)]
    else:
        sample = []
    # Top it up with the highest- and lowest-scoring captures (where the color score is most
    # likely to be fooled by walls/trees or miss a good sky) plus a few random ones.
    by_score = sorted((p for p in points if p not in sample), key=lambda p: p.get("score") or 0)
    n = max(0, args.sample - len(sample))
    k = n // 3
    top, bottom = by_score[len(by_score) - k:], by_score[:k]
    middle = [p for p in by_score if p not in top and p not in bottom]
    sample += top + bottom + random.Random(0).sample(middle, min(len(middle), n - 2 * k))

    rows = []
    for model in models:
        ensure_model(model, OLLAMA_URL)
    for point in sample:
        image = store.image_bytes(point)
        verdicts = []
        for model in models:
            started = time.monotonic()
            result = judge_image(image, model, OLLAMA_URL)
            verdicts.append((model, result, time.monotonic() - started))
            log.info("%s %s: %s (%.0fs)", point["time"], model, result, verdicts[-1][2])
        rows.append((point, verdicts))

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    report = out / "bakeoff.html"
    report.write_text(render_report(rows, models), encoding="utf-8")
    for model in models:
        times = [t for _, verdicts in rows for m, _, t in verdicts if m == model]
        log.info("%s: %.1fs per photo on average", model, sum(times) / max(1, len(times)))
    log.info("Report: %s", report.resolve())


def render_report(rows, models):
    head = "".join(f"<th>{html.escape(m)}</th>" for m in models)
    body = []
    for point, verdicts in rows:
        cells = []
        for _, r, secs in verdicts:
            text = "failed" if not r else f"<b>{r['view']}</b> · {r['score']}<br>{html.escape(r['reason'])}"
            cells.append(f"<td>{text}<br><small>{secs:.0f}s</small></td>")
        body.append(
            f"<tr><td><img src='{html.escape(point['url'])}' width='320'><br>"
            f"{html.escape(point['time'])} · color score {point.get('score', 0):.1f}</td>{''.join(cells)}</tr>"
        )
    return (
        "<!doctype html><meta charset='utf-8'><title>AI judge bake-off</title>"
        "<style>body{font-family:sans-serif;background:#0e1117;color:#eee}td{vertical-align:top;padding:8px;"
        "border-bottom:1px solid #333}img{border-radius:6px}</style>"
        f"<table><tr><th>Capture</th>{head}</tr>{''.join(body)}</table>"
    )


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser(prog="ai_judge", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("watch")
    b = sub.add_parser("backfill", help="judge past captures")
    b.add_argument("--camera", required=True, help="camera tag, or 'all'")
    add_date_range(b)
    b.add_argument("--best-only", action="store_true", help="only each day's best shot (much faster)")
    b.add_argument("--limit", type=int)
    b.add_argument("--rejudge", action="store_true", help="judge again even if already judged by this model")
    r = sub.add_parser("rerank", help="re-pick each day's best shot and regenerate its ranked image")
    r.add_argument("--camera", required=True, help="camera tag, or 'all'")
    add_date_range(r)
    r.add_argument("--rescore", action="store_true", help="recompute every capture's HSV score with the current sunset_process.py first")
    r.add_argument("--ignore-ai", action="store_true", help="pick by HSV score only, even for captures the AI judged not the sky")
    r.add_argument("--fill-missing", action="store_true", help="also rank days the pipeline never ranked (e.g. its ranked-image step failed)")
    r.add_argument("--dry-run", action="store_true", help="show what would change without changing anything")
    k = sub.add_parser("bakeoff", help="compare models on a sample (writes nothing)")
    k.add_argument("--camera", required=True)
    k.add_argument("--models", default="qwen3-vl:4b,gemma3:4b")
    k.add_argument("--sample", type=int, default=12)
    k.add_argument("--dates", help="comma-separated YYYY-MM-DD days to include (e.g. ones you know were obstructed)")
    k.add_argument("--out", default="bakeoff")
    args = parser.parse_args()
    {"backfill": backfill, "rerank": rerank_cmd, "bakeoff": bakeoff}.get(args.command, watch)(args)


def add_date_range(parser):
    parser.add_argument("--since", type=date.fromisoformat, metavar="YYYY-MM-DD", help="first day to include")
    parser.add_argument("--before", type=date.fromisoformat, metavar="YYYY-MM-DD", help="stop before this day")


if __name__ == "__main__":
    main()
