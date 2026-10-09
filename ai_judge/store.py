"""Reading captures from, and writing AI results back to, the sunset_images
measurement. Only adds ai_* fields: InfluxDB 1.x merges fields when a point is
written again with the same measurement, tags and timestamp, so the pipeline's
own fields (url, score) are left exactly as they were.
"""

import os

import requests

MEASUREMENT = "sunset_images"
AI_FIELDS = ("ai_view", "ai_is_sunset", "ai_score", "ai_reason", "ai_model")


def is_raw_capture(point):
    """Photos from the camera, as opposed to the generated 11_ranked / 12_histogram images."""
    return not point.get("label", "").startswith(("11_", "12_"))


def cameras(client):
    result = client.query(f"SHOW TAG VALUES FROM {MEASUREMENT} WITH KEY = camera")
    return [p["value"] for p in result.get_points()]


def captures(client, camera, since=None):
    """Raw captures for a camera, oldest first. `since` is an InfluxQL duration like "2d"."""
    query = f"SELECT * FROM {MEASUREMENT} WHERE camera = $camera"
    if since:
        query += f" AND time > now() - {since}"
    points = list(client.query(query, bind_params={"camera": camera}).get_points())
    return [p for p in points if is_raw_capture(p)]


def best_shot_times(client, camera):
    """Timestamps of each day's best shot (where the pipeline wrote its 11_ranked image)."""
    query = f"SELECT url, label FROM {MEASUREMENT} WHERE camera = $camera"
    points = client.query(query, bind_params={"camera": camera}).get_points()
    return {p["time"] for p in points if p.get("label", "").startswith("11_")}


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


def save_judgment(client, point, result, model):
    """Merge the AI fields into the existing capture point."""
    client.write_points([{
        "measurement": MEASUREMENT,
        "tags": {"label": point["label"], "camera": point["camera"]},
        "time": point["time"],
        "fields": {
            "ai_view": result["view"],
            "ai_is_sunset": result["is_sunset"],
            "ai_score": float(result["score"]),
            "ai_reason": result["reason"],
            "ai_model": model,
        },
    }])
