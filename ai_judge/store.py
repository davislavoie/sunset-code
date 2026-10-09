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
AI_FIELDS = ("ai_view", "ai_is_sunset", "ai_score", "ai_reason", "ai_model")

# Days are grouped by the cameras' local date: an evening sunset in Vermont is after
# midnight UTC, so UTC dates would split or shift it.
LOCAL_TZ = ZoneInfo(os.environ.get("TIMEZONE", "America/New_York"))


def is_raw_capture(point):
    """Photos from the camera, as opposed to the generated 11_ranked / 12_histogram images."""
    return not point.get("label", "").startswith(("11_", "12_"))


def is_ranked(point):
    return point.get("label", "").startswith("11_")


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
    """Timestamps of each day's best shot (where the pipeline wrote its 11_ranked image)."""
    query = f"SELECT url, label FROM {MEASUREMENT} WHERE camera = $camera"
    found = client.query(query, bind_params={"camera": camera}).get_points()
    return {p["time"] for p in found if is_ranked(p)}


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
        "ai_score": float(result["score"]),
        "ai_reason": result["reason"],
        "ai_model": model,
    })


def save_fields(client, point, fields):
    """Merge fields into an existing point (same measurement, tags and time)."""
    client.write_points([{
        "measurement": MEASUREMENT,
        "tags": {"label": point["label"], "camera": point["camera"]},
        "time": point["time"],
        "fields": fields,
    }])


def epoch_seconds(point):
    return int(parse_time(point).timestamp())
