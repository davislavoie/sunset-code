"""Sidecar to the capture pipeline: reads captures from InfluxDB and adds fields to
them (weather, a simple sunset forecast, view fingerprints, glass-lake badge, thumbs rules, the vision model's sky read).
The dashboard picks each day's best shot from the scores itself; `rescore` rewrites the scores in place
after a change to sunset_process.py / hsv_score.json.

  python -m ai_analysis watch      # keep new captures filled in
  python -m ai_analysis weather  --camera all [--since ...] [--before ...] [--refill]
  python -m ai_analysis goes     --camera all [--since ...] [--before ...]   # GOES-East observed cloud on captures (history; watch does recent ones)
  python -m ai_analysis predict  --camera all [--since ...] [--before ...] [--refill]   # sunset forecast on the pre shots
  python -m ai_analysis views    --camera all   # fingerprint captures for "all shots like this"
  python -m ai_analysis metar    --camera all   # observed airport weather (KBTV METAR) on captures
  python -m ai_analysis sky      --camera all   # vision model reads the band of light on the 1h/45m/30m/15m shots
  python -m ai_analysis band     --camera all   # horizon light band (horizon_lift) on the pre shots, for the forecast
  python -m ai_analysis reflect  --camera all   # "Glass lake" badge: mirror score on btv_echo_cam captures
  python -m ai_analysis cleanup  --camera all [--delete]   # list (or remove) entries whose photo you deleted
  python -m ai_analysis rescore  --camera all [--since ...] [--before ...] [--dry-run]   # new HSV scores, in place
  python -m ai_analysis drop-ranked --camera all [--delete]   # list (or remove) the old 11_ranked / 12_histogram points + PNGs

Dates are the cameras' local dates (TIMEZONE, default America/New_York): --since is
inclusive, --before is exclusive. --camera all runs every camera.

Config (env): OLLAMA_URL, SKY_MODEL, CONFIG_DIR, INFLUXDB_HOST, INFLUXDB_PORT, IMAGE_BASE_URL,
IMAGE_FETCH_URL, PICTURES_DIR, TIMEZONE.
"""

import argparse
import logging
import os
import time
from datetime import date

import requests
from influxdb import InfluxDBClient

from . import band, goes, metar, predict, reflect, sky, store, views, weather
from .ollama import ensure_model
from .rescore import drop_ranked, rescore

log = logging.getLogger("ai_analysis")

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
WATCH_INTERVAL_S = int(os.environ.get("WATCH_INTERVAL_S", 600))


def influx():
    return InfluxDBClient(
        host=os.environ.get("INFLUXDB_HOST", "localhost"),
        port=int(os.environ.get("INFLUXDB_PORT", 8086)),
        database="sunset_images",
    )


def watch(_args):
    client = influx()
    try:
        ensure_model(sky.MODEL, OLLAMA_URL)
    except requests.RequestException as e:  # Ollama down: everything else still runs; sky retries each pass
        log.warning("Can't reach Ollama for %s: %s", sky.MODEL, e)
    log.info("Watching for new captures every %ds", WATCH_INTERVAL_S)
    while True:
        for camera in store.cameras(client):
            # Each step on its own, so e.g. Open-Meteo being down doesn't stop thumbs from applying.
            steps = [lambda: weather.fill(client, camera), lambda: metar.fill(client, camera), lambda: goes.fill(client, camera), lambda: band.fill(client, camera),
                     lambda: sky.fill(client, camera, OLLAMA_URL, recent="2d"),
                     lambda: predict.fill(client, camera),
                     lambda: views.fill_fingerprints(client, camera), lambda: reflect.fill(client, camera)]
            steps.append(lambda: views.apply_bad_views(client, camera))
            for step in steps:
                try:
                    step()
                except Exception:
                    log.exception("%s: watch step failed; retrying next interval", camera)
        time.sleep(WATCH_INTERVAL_S)


def camera_list(client, camera):
    known = store.cameras(client)
    if camera == "all":
        return known
    if camera not in known:
        raise SystemExit(f"Unknown camera {camera!r}. Cameras: {', '.join(known)} (or 'all')")
    return [camera]


def rescore_cmd(args):
    client = influx()
    for camera in camera_list(client, args.camera):
        rescore(client, camera, since=args.since, before=args.before, dry_run=args.dry_run)


def drop_ranked_cmd(args):
    client = influx()
    for camera in camera_list(client, args.camera):
        drop_ranked(client, camera, delete=args.delete)


def weather_cmd(args):
    client = influx()
    for camera in camera_list(client, args.camera):
        weather.fill(client, camera, since=args.since, before=args.before, refill=args.refill)


def predict_cmd(args):
    client = influx()
    for camera in camera_list(client, args.camera):
        predict.fill(client, camera, since=args.since, before=args.before, refill=args.refill)


def cleanup_cmd(args):
    """Photos deleted by hand leave their InfluxDB entries behind (broken images in the
    dashboard, junk rows for training). Lists them per day; --delete removes the entries."""
    client = influx()
    for camera in camera_list(client, args.camera):
        days = store.missing_files(client, camera)
        for day, gone in sorted(days.items()):
            log.info("%s %s: %d entries with no photo (%s)", camera, day, len(gone),
                     ", ".join(sorted(p["label"][:12] for p in gone)))
            if args.delete:
                for p in gone:
                    store.delete_point(client, p)
        total = sum(map(len, days.values()))
        log.info("%s: %d entries on %d days %s", camera, total, len(days),
                 "deleted" if args.delete else "would be deleted (dry run; add --delete)")


def views_cmd(args):
    client = influx()
    for camera in camera_list(client, args.camera):
        views.fill_fingerprints(client, camera)
        views.apply_bad_views(client, camera)


def goes_cmd(args):
    client = influx()
    for camera in camera_list(client, args.camera):
        goes.fill(client, camera, recent=None, since=args.since, before=args.before)


def metar_cmd(args):
    client = influx()
    for camera in camera_list(client, args.camera):
        metar.fill(client, camera)


def sky_cmd(args):
    client = influx()
    ensure_model(sky.MODEL, OLLAMA_URL)
    for camera in camera_list(client, args.camera):
        sky.fill(client, camera, OLLAMA_URL, limit=args.limit)


def band_cmd(args):
    client = influx()
    for camera in camera_list(client, args.camera):
        band.fill(client, camera)


def reflect_cmd(args):
    client = influx()
    for camera in camera_list(client, args.camera):
        reflect.fill(client, camera)


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser(prog="ai_analysis", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("watch")
    r = sub.add_parser("rescore", help="recompute every capture's HSV score (and breakdown) in place with the current sunset_process.py")
    r.add_argument("--camera", required=True, help="camera tag, or 'all'")
    add_date_range(r)
    r.add_argument("--dry-run", action="store_true", help="score and report how much scores would move, without writing")
    d = sub.add_parser("drop-ranked", help="list (or --delete) the old 11_ranked / 12_histogram points and their PNGs")
    d.add_argument("--camera", required=True, help="camera tag, or 'all'")
    d.add_argument("--delete", action="store_true", help="actually remove them (default: just list)")
    w = sub.add_parser("weather", help="add Open-Meteo hourly weather to captures")
    w.add_argument("--camera", required=True, help="camera tag, or 'all'")
    add_date_range(w)
    w.add_argument("--refill", action="store_true", help="fetch again even for captures that have weather")
    f = sub.add_parser("predict", help="add the simple sunset forecast (predicted_score/class) to 2h/1h-pre captures")
    f.add_argument("--camera", required=True, help="camera tag, or 'all'")
    add_date_range(f)
    f.add_argument("--refill", action="store_true", help="recompute even for captures that have a forecast")
    v = sub.add_parser("views", help="fingerprint captures and apply 'all shots like this' thumbs downs")
    v.add_argument("--camera", required=True, help="camera tag, or 'all'")
    g = sub.add_parser("goes", help="add GOES-East observed cloud toward the sun to captures (about 1 s each)")
    g.add_argument("--camera", required=True, help="camera tag, or 'all'")
    add_date_range(g)
    m = sub.add_parser("reflect", help="add the glass-lake mirror score to btv_echo_cam captures that lack one")
    m.add_argument("--camera", required=True, help="camera tag, or 'all' (only btv_echo_cam is scored)")
    o = sub.add_parser("metar", help="add the observed airport weather (METAR, obs_*) to captures that lack it")
    o.add_argument("--camera", required=True, help="camera tag, or 'all'")
    y = sub.add_parser("sky", help="vision model reads the band of light / cloud on the 1h, 45m, 30m, 15m shots (about 40-70 s each on the NUC)")
    y.add_argument("--camera", required=True, help="camera tag, or 'all'")
    y.add_argument("--limit", type=int, help="at most this many shots per camera (newest first)")
    b = sub.add_parser("band", help="add the horizon light band (horizon_lift) to the pre shots that lack it")
    b.add_argument("--camera", required=True, help="camera tag, or 'all'")
    x = sub.add_parser("cleanup", help="list (or --delete) entries whose photo file is gone")
    x.add_argument("--camera", required=True, help="camera tag, or 'all'")
    x.add_argument("--delete", action="store_true", help="actually remove them (default: just list)")
    args = parser.parse_args()
    commands = {"rescore": rescore_cmd, "drop-ranked": drop_ranked_cmd, "weather": weather_cmd, "predict": predict_cmd,
                "views": views_cmd, "reflect": reflect_cmd, "band": band_cmd, "sky": sky_cmd, "metar": metar_cmd, "goes": goes_cmd, "cleanup": cleanup_cmd}
    commands.get(args.command, watch)(args)


def add_date_range(parser):
    parser.add_argument("--since", type=date.fromisoformat, metavar="YYYY-MM-DD", help="first day to include")
    parser.add_argument("--before", type=date.fromisoformat, metavar="YYYY-MM-DD", help="stop before this day")


if __name__ == "__main__":
    main()
