"""Reading captures from, and writing results back to, the sunset_images
measurement. Only merges fields: InfluxDB 1.x merges fields when a point is
written again with the same measurement, tags and timestamp, so the pipeline's
own fields (url, score) are left exactly as they were.
"""

import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import requests

MEASUREMENT = "sunset_images"
HIST_MEASUREMENT = "sunset_hist"  # each capture's sky histograms (same tags and time), kept out of the main measurement
AI_FIELDS = ("ai_view", "ai_is_sunset", "ai_sky_percent", "ai_score", "ai_reason", "ai_model")

# Days are grouped by the cameras' local date: an evening sunset in Vermont is after
# midnight UTC, so UTC dates would split or shift it.
LOCAL_TZ = ZoneInfo(os.environ.get("TIMEZONE", "America/New_York"))


def is_raw_capture(point):
    """Photos from the camera, as opposed to the 11_ranked / 12_histogram images the pipeline used to make
    (`python -m ai_judge drop-ranked` removes those)."""
    return not point.get("label", "").startswith(("11_", "12_"))


def parse_time(point):
    """Influx RFC3339 time ("2025-05-16T22:17:26Z", maybe with fractions) -> aware datetime."""
    return datetime.fromisoformat(point["time"].replace("Z", "+00:00"))


def local_date(point):
    return parse_time(point).astimezone(LOCAL_TZ).date()


def cameras(client):
    result = client.query(f"SHOW TAG VALUES FROM {MEASUREMENT} WITH KEY = camera")
    return [p["value"] for p in result.get_points()]


def points(client, camera, recent=None, since=None, before=None):
    """All points (captures and ranked/histogram images) for a camera, oldest first.

    recent: InfluxQL duration like "2d". since/before: local dates (datetime.date);
    since is inclusive, before is exclusive.
    """
    query = f"SELECT * FROM {MEASUREMENT} WHERE camera = $camera"
    if recent:
        query += f" AND time > now() - {recent}"
    # Query a day wider than asked in UTC, then filter exactly by local date below.
    if since:
        query += f" AND time >= '{since - timedelta(days=1)}T00:00:00Z'"
    if before:
        query += f" AND time < '{before + timedelta(days=1)}T00:00:00Z'"
    found = client.query(query, bind_params={"camera": camera}).get_points()
    return [p for p in found if (not since or local_date(p) >= since) and (not before or local_date(p) < before)]


def captures(client, camera, recent=None, since=None, before=None):
    """Raw camera captures only."""
    return [p for p in points(client, camera, recent, since, before) if is_raw_capture(p)]


def by_day(day_points):
    """{local date: [points]} preserving order."""
    days = {}
    for p in day_points:
        days.setdefault(local_date(p), []).append(p)
    return days


def best_shot_times(client, camera):
    """Timestamps of each day's highest-scoring capture (for judging only those)."""
    best = {}
    for p in captures(client, camera):
        day = local_date(p)
        if (p.get("score") or 0) > (best.get(day, {}).get("score") or -1):
            best[day] = p
    return {p["time"] for p in best.values()}


AI_EXCLUSIONS = {"dark": "too dark", "no_signal": "no camera signal"}


def exclusion(point):
    """Why a capture can't be a day's best shot, or None. Same rule as html_project/backend.py.
    The HSV score decides everything else; a thumbs up overrides all of it."""
    thumb = point.get("thumb") or 0
    if thumb > 0:
        return None
    if thumb < 0:
        return "thumbs down"
    if point.get("view_blocked"):
        return "same view as a thumbed-down shot"
    return AI_EXCLUSIONS.get(point.get("ai_view"))


# Glass lake (ai_judge/reflect.py): a mirror-calm lake earns a small bump in the displayed score and when
# the dashboard picks the day's best shot (html_project/backend.py applies it); the HSV score is untouched.
# Here only for reflect.py's badge threshold. Same numbers as backend.py (which also skips grey (HSV < 10) and rainy shots).
GLASS_BONUS = ((0.45, 8), (0.35, 5))  # (mirror_score at least, points)


def needs_judging(point, model, rejudge=False):
    return rejudge or point.get("ai_model") != model


def image_bytes(point):
    """Download the capture. IMAGE_FETCH_URL lets a container reach the image server by its
    compose name (http://imageserver:8080) instead of the public IMAGE_BASE_URL in the stored url."""
    url = point["url"]
    public, internal = os.environ.get("IMAGE_BASE_URL"), os.environ.get("IMAGE_FETCH_URL")
    if public and internal and url.startswith(public.rstrip("/")):
        url = internal.rstrip("/") + url[len(public.rstrip("/")):]
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    return resp.content


def local_path(point):
    """The capture's file on disk: its url with IMAGE_BASE_URL swapped for PICTURES_DIR
    (the inverse of how helpers.influxdb_push builds the url)."""
    base = os.environ.get("IMAGE_BASE_URL", "http://100.107.153.41:8080").rstrip("/")
    pictures = os.environ.get("PICTURES_DIR", os.path.expanduser("~/Pictures"))
    url = point["url"]
    if not url.startswith(base + "/"):
        raise ValueError(f"url {url} doesn't start with IMAGE_BASE_URL {base}")
    return os.path.join(pictures, *url[len(base) + 1:].split("/"))


def save_judgment(client, point, result, model):
    """Merge the AI fields into the existing capture point."""
    save_fields(client, point, {
        "ai_view": result["view"],
        "ai_is_sunset": result["is_sunset"],
        "ai_sky_percent": float(result["sky_percent"]),
        "ai_score": float(result["score"]),
        "ai_reason": result["reason"],
        "ai_model": model,
    })


def save_fields(client, point, fields):
    """Merge fields into an existing point (same measurement, tags and time)."""
    client.write_points([field_point(point, fields)])


def field_point(point, fields):
    return {
        "measurement": MEASUREMENT,
        "tags": {"label": point["label"], "camera": point["camera"]},
        "time": point["time"],
        "fields": fields,
    }


def delete_point(client, point):
    client.query(
        f"DELETE FROM {MEASUREMENT} WHERE camera = $camera AND label = $label AND time = '{point['time']}'",
        bind_params={"camera": point["camera"], "label": point["label"]},
    )


def missing_files(client, camera, max_share=0.2):
    """Points whose photo is gone from PICTURES_DIR (e.g. deleted by hand), grouped by local date.
    Refuses if more than max_share of the camera's photos look missing: that means the folder
    isn't mounted / PICTURES_DIR is wrong, not that you deleted them."""
    pts = points(client, camera)
    gone = [p for p in pts if not os.path.exists(local_path(p))]
    if pts and len(gone) > max_share * len(pts):
        raise SystemExit(f"{camera}: {len(gone)} of {len(pts)} photos missing from "
                         f"{os.environ.get('PICTURES_DIR')}; is the photos folder mounted? Not touching anything.")
    return by_day(gone)


def epoch_seconds(point):
    return int(parse_time(point).timestamp())
