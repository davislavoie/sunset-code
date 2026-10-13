from flask import Flask, jsonify, request, send_from_directory, Response
from influxdb import InfluxDBClient
from datetime import datetime
from urllib.parse import urlsplit
from pathlib import Path
import os
import pytz
import time
import requests
import glob
import html
import re
import yaml

app = Flask(__name__, static_folder=None)

# Config directory - check /app/config first (Docker mount), fallback to relative path
def get_config_dir():
    docker_path = Path("/app/config")
    if docker_path.exists():
        return docker_path
    return Path(__file__).parent.parent / "config"

# Docker compose file - mounted at /app/docker-compose.yml in Docker
def get_compose_file():
    docker_path = Path("/app/docker-compose.yml")
    if docker_path.exists():
        return docker_path
    return Path(__file__).parent.parent / "docker-compose.existing-infra.yml"

# Pictures path from env (for compose service template)
PICTURES_PATH = os.environ.get("PICTURES_PATH", "/home/YOUR_USER/Pictures")

INFLUXDB_HOST = os.environ.get("INFLUXDB_HOST", "100.107.153.41")
INFLUXDB_PORT = int(os.environ.get("INFLUXDB_PORT", 8086))

client = InfluxDBClient(host=INFLUXDB_HOST, port=INFLUXDB_PORT, database="sunset_images")
local_tz = pytz.timezone("America/New_York")

IMAGE_BASE_URL = os.environ.get("IMAGE_BASE_URL", "")

CACHE_TTL = 300  # seconds, mirrors @st.cache_data(ttl=300) in streamlit_project/app.py
_cache = {}


def fetch_camera_data(camera_tag):
    """Fetch and process all data for a camera (mirrors app.py's fetch_camera_data)."""
    results = client.query("SELECT * FROM sunset_images WHERE camera = $camera", bind_params={"camera": camera_tag})

    sunset_data = []
    all_data = []
    days = {}  # date -> [(point, data_item)] for picking each day's best shot

    for point in results.get_points():
        # 11_ranked / 12_histogram points are the pipeline's old ranked images; the best shot is worked
        # out below instead (`python -m ai_judge drop-ranked` removes them).
        if point.get("label", "").startswith(("11_", "12_")):
            continue
        dt_utc = datetime.strptime(point["time"], "%Y-%m-%dT%H:%M:%SZ")
        dt_local = dt_utc.replace(tzinfo=pytz.utc).astimezone(local_tz)
        date_str = dt_local.strftime("%Y-%m-%d")
        time_str = dt_local.strftime("%I:%M %p")

        hsv_score = 0 if point["score"] is None else point["score"]
        zoom = ZOOMED_DAYS.get(camera_tag, {}).get(date_str, 0)
        data_item = {
            "Date": date_str,
            "Time": time_str,
            "Label": point["label"],
            "Image": point["url"],
            # A capture that can't be a day's best shot (thumbs down, dark...) counts as 0.
            "Score": 0 if exclusion(point) else shown_score(hsv_score, point, zoom),
            "HSV Score": hsv_score,
            "Breakdown": breakdown_fields(point),
            "Glass": glass_fields(point),
            "Zoom": zoom,
            "AI": ai_fields(point),
            "ts": point["time"],
            "Thumb": point.get("thumb") or 0,
            "BadView": bool(point.get("bad_view")),
            "Excluded": exclusion(point),
            "Weather": weather_fields(point),
            "Forecast": forecast_fields(point),
        }

        all_data.append(data_item)
        days.setdefault(date_str, []).append((point, data_item))

        if point.get("label", "").startswith("07_"):
            sunset_data.append(data_item)

    ranked_images = []
    for date_str, shots in days.items():
        best = best_shot([p for p, _ in shots])
        if best is None:
            continue  # nothing that day can be the best shot (all thumbed down / dark)
        point, item = next(s for s in shots if s[0] is best)
        ranked_images.append({
            # The pipeline's annotated 11_ranked PNG is gone; the dashboard draws the overlay itself.
            "Ranked Image": point["url"],
            "Raw Image": point["url"],
            "HSV Image": None,
            "Score": shown_score(item["HSV Score"], point, item["Zoom"]),
            "HSV Score": item["HSV Score"],
            "Breakdown": item["Breakdown"],
            "Glass": item["Glass"],
            "Zoom": item["Zoom"],
            "Date": date_str,
            "Time": item["Time"],
            "dt_local": datetime.strptime(point["time"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=pytz.utc).astimezone(local_tz).isoformat(),
            "Label": point["label"],
            "ts": point["time"],
            "AI": item["AI"],
            "Excluded": item["Excluded"],
            "Weather": item["Weather"],
        })

    return {"sunset_data": sunset_data, "all_data": all_data, "ranked_images": ranked_images}


def best_shot(captures):
    """A day's best shot: the highest HSV score plus glass bonus among captures that can win; a thumbs up
    beats everything. None if no capture can win."""
    candidates = [p for p in captures if not exclusion(p)]
    liked = [p for p in candidates if (p.get("thumb") or 0) > 0]
    return max(liked or candidates, key=lambda p: (p.get("score") or 0) + glass_bonus(p), default=None)


BREAKDOWN_FIELDS = [f"{c}_{k}" for c in ("red", "orange", "yellow", "pink") for k in ("points", "coverage", "saturation")] + [
    "hue_spread", "lit_contrast", "contrast"]


def breakdown_fields(point):
    """The score's pieces stored by sunset_process.rank_sunset, or None for captures scored before they were
    stored (run `python -m ai_judge rescore`)."""
    return {k: point[k] for k in BREAKDOWN_FIELDS if point.get(k) is not None} if point.get("contrast") is not None else None


AI_EXCLUSIONS = {"dark": "too dark", "no_signal": "no camera signal"}


def exclusion(point):
    """Why a capture can't be a day's best shot, or None. Keep in sync with ai_judge/store.py.
    The HSV score decides everything else; a thumbs up overrides all of it."""
    thumb = point.get("thumb") or 0
    if thumb > 0:
        return None
    if thumb < 0:
        return "thumbs down"
    if point.get("view_blocked"):
        return "same view as a thumbed-down shot"
    return AI_EXCLUSIONS.get(point.get("ai_view"))


# Glass lake (ai_judge/reflect.py): mirror-calm lake shots get a small bump. Keep in sync with ai_judge/store.py.
GLASS_BONUS = ((0.45, 8), (0.35, 5))  # (mirror_score at least, points)


GLASS_MIN_HSV = 10  # a calm lake mirroring a grey sky isn't a sunset; flat grey sky + lake also fools the detector


def glass_bonus(point):
    mirror = point.get("mirror_score")
    if (point.get("score") or 0) < GLASS_MIN_HSV or (point.get("precipitation") or 0) > 0:  # raining: not glass
        return 0
    return next((pts for at, pts in GLASS_BONUS if mirror is not None and mirror >= at), 0)


# Days the camera was zoomed in on the sun: the sky filled the frame (~3-4x zoom, ~10x the area), so the
# HSV score maxed out at 100 (102-192 uncapped, like the best wide-view days). Shown score gets this offset.
ZOOMED_DAYS = {
    "btv_echo_cam": dict.fromkeys(["2026-01-30", "2026-01-31", "2026-02-01", "2026-02-26"], -40),
    "wcax_tower_sunset": {"2025-09-14": -40},
}


def shown_score(hsv, point, zoom=0):
    """Displayed score: HSV plus the glass-lake bump and any zoom offset, kept within 0-100."""
    return max(0, min(100, hsv + glass_bonus(point) + zoom))


def glass_fields(point):
    """{"mirror": score, "bonus": points} for a glass-lake shot, else None."""
    bonus = glass_bonus(point)
    return {"mirror": point["mirror_score"], "bonus": bonus} if bonus else None


WEATHER_FIELDS = ["temperature_2m", "relative_humidity_2m", "dew_point_2m", "precipitation_probability",
                  "precipitation", "rain", "showers", "snowfall", "cloud_cover_low", "cloud_cover_mid",
                  "cloud_cover_high", "cloud_cover_total", "visibility"] + [
    f"path{km}_{model}cloud_cover_{layer}" for model in ("", "icon_") for km in (13, 40, 80)
    for layer in ("low", "mid", "high")] + [  # toward the sun, 8/25/50 mi (best_match, and the ICON model)
    "goes_over", "goes_near", "goes_far", "goes_fan"] + [  # observed by GOES-East: cloudy share overhead / toward the sun
    f"goes_{k}_{z}" for z in ("over", "near", "far") for k in ("top", "high", "mid", "low")]  # and its cloud-top height (km)


def weather_fields(point):
    """Open-Meteo weather saved with the capture (°F, %, mm, m), or None if it has none yet."""
    weather = {k: point[k] for k in WEATHER_FIELDS if point.get(k) is not None}
    return weather or None


def forecast_fields(point):
    """Sunset forecast ai_judge/predict.py writes on each pre shot, or None."""
    if point.get("predicted_pct") is None:
        return None
    return {"pct": point["predicted_pct"], "score": point.get("predicted_score"), "call": point.get("predicted_call"),
            "with": point.get("predicted_with")}


def ai_fields(point):
    """ai_* fields written by the optional ai_judge service, or None if not judged (or not running)."""
    if point.get("ai_model") is None:
        return None
    return {
        "view": point.get("ai_view"),
        "is_sunset": point.get("ai_is_sunset"),
        "sky_percent": point.get("ai_sky_percent"),
        "score": point.get("ai_score"),
        "reason": point.get("ai_reason"),
        "model": point.get("ai_model"),
    }


def fetch_camera_data_cached(camera_tag):
    now = time.time()
    entry = _cache.get(camera_tag)
    if entry and now - entry["ts"] < CACHE_TTL:
        return entry["data"]
    data = fetch_camera_data(camera_tag)
    _cache[camera_tag] = {"ts": now, "data": data}
    return data


@app.route("/api/cameras")
def cameras():
    camera_query = client.query("SHOW TAG VALUES FROM sunset_images WITH KEY = camera")
    camera_tags = [point["value"] for point in camera_query.get_points()]
    if not camera_tags:
        camera_tags = ["btv_echo_cam"]
    return jsonify(camera_tags)


@app.route("/api/data")
def data():
    camera = request.args.get("camera")
    if not camera:
        return jsonify({"error": "camera query param required"}), 400
    return jsonify(fetch_camera_data_cached(camera))


@app.route("/api/image-proxy")
def image_proxy():
    """Fetch a gallery image server-side so the browser can read its pixels
    (getImageData) without hitting cross-origin canvas tainting). Mirrors
    hsv_tuner.py's load_image_from_url, which does the same fetch in Python."""
    url = request.args.get("url")
    if not url:
        return jsonify({"error": "url query param required"}), 400
    # Only proxy our own image server, otherwise this is an open proxy (SSRF).
    allowed = urlsplit(IMAGE_BASE_URL)
    target = urlsplit(url)
    if not IMAGE_BASE_URL or (target.scheme, target.netloc) != (allowed.scheme, allowed.netloc):
        return jsonify({"error": "url must point at IMAGE_BASE_URL"}), 400
    resp = requests.get(url, timeout=10, allow_redirects=False)
    return Response(resp.content, mimetype=resp.headers.get("Content-Type", "image/jpeg"))


FRONTEND_DIST = Path(__file__).parent / "frontend" / "dist"
SUNSET_PAGE = re.compile(r"sunset/([A-Za-z0-9_-]+)/(\d{4}-\d{2}-\d{2})")


def sunset_preview_tags(camera, date):
    """Open Graph tags so a shared /sunset/<camera>/<date> link unfurls with the photo.
    Crawlers don't run JavaScript, so these have to be in the HTML Flask sends."""
    try:
        ranked = fetch_camera_data_cached(camera)["ranked_images"]
    except Exception:
        return None
    entry = next((r for r in ranked if r["Date"] == date), None)
    if not entry:
        return None
    day = datetime.strptime(date, "%Y-%m-%d")
    title = f"{camera} sunset · {day:%B} {day.day}, {day.year} · {entry['Score']:.0f}%"
    tags = {
        "og:title": title,
        "og:description": f"Scored {entry['Score']:.1f}/100 by color analysis of the sky.",
        "og:image": entry["Raw Image"] or entry["Ranked Image"],
        "og:type": "website",
    }
    meta = "".join(f'<meta property="{k}" content="{html.escape(str(v))}" />\n' for k, v in tags.items())
    return f'<title>{html.escape(title)}</title>\n{meta}<meta name="twitter:card" content="summary_large_image" />'


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def frontend(path):
    """Serves the React app (frontend/, built to frontend/dist). Unknown paths fall
    back to index.html so client-side routes like /calendar work; /api/ stays 404."""
    if path.startswith("api/"):
        return jsonify({"error": "not found"}), 404
    if path and (FRONTEND_DIST / path).is_file():
        return send_from_directory(FRONTEND_DIST, path)
    match = SUNSET_PAGE.fullmatch(path)
    tags = match and sunset_preview_tags(*match.groups())
    if tags:
        page = (FRONTEND_DIST / "index.html").read_text(encoding="utf-8")
        return Response(page.replace("<title>Sunset Dashboard</title>", tags, 1), mimetype="text/html")
    return send_from_directory(FRONTEND_DIST, "index.html")


def parse_env_file(filepath):
    """Parse a .env file and return a dict of key-value pairs."""
    config = {}
    with open(filepath, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                config[key.strip()] = value.strip()
    return config


@app.route("/api/admin/thumb", methods=["POST"])
def set_thumb():
    """Thumbs up (1), down (-1) or clear (0) one capture. bad_view with a thumbs down also
    rules out every near-identical shot from that camera (ai_judge applies it within ~10 min,
    and re-picks affected days' best shots)."""
    body = request.json or {}
    camera, label, ts, thumb = (body.get(k) for k in ("camera", "label", "ts", "thumb"))
    if thumb not in (-1, 0, 1) or not all(isinstance(v, str) for v in (camera, label, ts)):
        return jsonify({"error": "camera, label, ts and thumb (-1, 0 or 1) required"}), 400
    try:
        datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ")  # also makes ts safe to put in the query
    except ValueError:
        return jsonify({"error": "ts must look like 2025-05-16T22:17:26Z"}), 400
    found = client.query(f"SELECT url FROM sunset_images WHERE camera = $camera AND label = $label AND time = '{ts}'",
                         bind_params={"camera": camera, "label": label})
    if not list(found.get_points()):
        return jsonify({"error": "no such capture"}), 404
    client.write_points([{
        "measurement": "sunset_images",
        "tags": {"label": label, "camera": camera},
        "time": ts,
        "fields": {"thumb": int(thumb), "bad_view": thumb == -1 and bool(body.get("bad_view"))},
    }])
    _cache.pop(camera, None)
    return jsonify({"ok": True})


@app.route("/api/my-ranks")
def my_ranks():
    """Davis's own sunset ranking for a camera: one chosen frame and a 0-100 score per day.
    The source of truth for what counts as a good sunset (analysis trains against it)."""
    camera = request.args.get("camera")
    if not camera:
        return jsonify({"error": "camera query param required"}), 400
    rows = client.query("SELECT * FROM my_rank WHERE camera = $camera", bind_params={"camera": camera}).get_points()
    return jsonify([{"date": r["date"], "ts": r["ts"], "label": r["label"], "url": r["url"], "score": r["score"]}
                    for r in rows if r.get("score") is not None and r["score"] >= 0])


@app.route("/api/admin/my-rank", methods=["POST"])
def set_my_rank():
    """Set (or with score -1, clear) the chosen frame and score for one camera-day.
    One point per camera-day at that day's midnight UTC, so a new pick overwrites the old."""
    body = request.json or {}
    camera, date, ts, label, url, score = (body.get(k) for k in ("camera", "date", "ts", "label", "url", "score"))
    if not all(isinstance(v, str) for v in (camera, date, ts, label, url)) or not isinstance(score, (int, float)) \
            or not -1 <= score <= 100:
        return jsonify({"error": "camera, date, ts, label, url and score (0-100, or -1 to clear) required"}), 400
    try:
        datetime.strptime(date, "%Y-%m-%d")
        datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return jsonify({"error": "date must be YYYY-MM-DD and ts like 2025-05-16T22:17:26Z"}), 400
    client.write_points([{
        "measurement": "my_rank",
        "tags": {"camera": camera, "date": date},
        "time": f"{date}T00:00:00Z",
        "fields": {"ts": ts, "label": label, "url": url, "score": float(score)},
    }])
    return jsonify({"ok": True})


@app.route("/api/admin/camera-configs")
def camera_configs():
    """Return all camera configurations from config/*.env files."""
    configs = []
    if get_config_dir().exists():
        for env_file in get_config_dir().glob("*.env"):
            try:
                config = parse_env_file(env_file)
                config["_filename"] = env_file.name
                configs.append(config)
            except Exception as e:
                configs.append({"_filename": env_file.name, "_error": str(e)})
    return jsonify(configs)


@app.route("/api/camera-locations")
def camera_locations():
    """Public subset of the camera configs for the map: no stream URLs."""
    public_fields = ["CAMERA_TAG", "LAT", "LON", "ALTITUDE", "MODE"]
    locations = []
    for env_file in get_config_dir().glob("*.env"):
        try:
            config = parse_env_file(env_file)
        except OSError:
            continue
        locations.append({k: config[k] for k in public_fields if k in config})
    return jsonify(locations)


@app.route("/api/admin/camera-configs", methods=["POST"])
def add_camera_config():
    """Create a new camera configuration file."""
    data = request.json
    required_fields = ["CAMERA_TAG", "YOUTUBE_URL", "LAT", "LON", "ALTITUDE", "TIMEZONE", "MODE"]

    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Missing required field: {field}"}), 400

    camera_tag = data["CAMERA_TAG"]
    if not re.match(r"^[a-zA-Z0-9_-]+$", camera_tag):
        return jsonify({"error": "CAMERA_TAG must be alphanumeric with underscores/hyphens only"}), 400

    filename = f"{camera_tag}.env"
    filepath = get_config_dir() / filename

    if filepath.exists():
        return jsonify({"error": f"Config file {filename} already exists"}), 409

    try:
        get_config_dir().mkdir(parents=True, exist_ok=True)
        with open(filepath, "w") as f:
            for field in required_fields:
                f.write(f"{field}={data[field]}\n")
        return jsonify({"success": True, "filename": filename})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/admin/camera-configs/<camera_tag>", methods=["PUT"])
def update_camera_config(camera_tag):
    """Update an existing camera configuration file."""
    data = request.json
    editable_fields = ["YOUTUBE_URL", "LAT", "LON", "ALTITUDE", "TIMEZONE", "MODE"]

    filename = f"{camera_tag}.env"
    filepath = get_config_dir() / filename

    if not filepath.exists():
        return jsonify({"error": f"Config file {filename} not found"}), 404

    try:
        # Read existing config
        existing = parse_env_file(filepath)

        # Update only provided fields
        for field in editable_fields:
            if field in data:
                existing[field] = data[field]

        # Ensure CAMERA_TAG stays the same
        existing["CAMERA_TAG"] = camera_tag

        # Write back
        with open(filepath, "w") as f:
            for key, value in existing.items():
                if not key.startswith("_"):
                    f.write(f"{key}={value}\n")

        return jsonify({"success": True, "filename": filename})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/admin/camera-configs/<camera_tag>", methods=["DELETE"])
def delete_camera_config(camera_tag):
    """Delete a camera configuration file."""
    filename = f"{camera_tag}.env"
    filepath = get_config_dir() / filename

    if not filepath.exists():
        return jsonify({"error": f"Config file {filename} not found"}), 404

    try:
        filepath.unlink()
        return jsonify({"success": True, "deleted": filename})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/admin/add-compose-service", methods=["POST"])
def add_compose_service():
    """Add a new capture service to the docker-compose file."""
    data = request.json
    camera_tag = data.get("camera_tag")

    if not camera_tag:
        return jsonify({"error": "camera_tag required"}), 400

    compose_file = get_compose_file()
    if not compose_file.exists():
        return jsonify({"error": "docker-compose file not found"}), 404

    try:
        with open(compose_file, "r") as f:
            compose = yaml.safe_load(f)

        service_name = f"capture-{camera_tag}"
        if service_name in compose.get("services", {}):
            return jsonify({"error": f"Service {service_name} already exists"}), 409

        new_service = {
            "build": {
                "context": ".",
                "dockerfile": "sunset_code/Dockerfile"
            },
            "restart": "unless-stopped",
            "depends_on": ["influxdb"],
            "env_file": [f"config/{camera_tag}.env"],
            "environment": {
                "INFLUXDB_HOST": "influxdb",
                "INFLUXDB_PORT": "8086",
                "PICTURES_DIR": "/pictures",
                "IMAGE_BASE_URL": "${IMAGE_BASE_URL:-http://localhost:8080}"
            },
            "volumes": [f"{PICTURES_PATH}:/pictures"]
        }

        compose["services"][service_name] = new_service

        with open(compose_file, "w") as f:
            yaml.dump(compose, f, default_flow_style=False, sort_keys=False)

        return jsonify({"success": True, "service": service_name})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


SCORE_CONFIG = Path(__file__).parent.parent / "sunset_code" / "helpers" / "hsv_score.json"


@app.route("/api/scoring-config")
def get_scoring_config():
    """Every number in the HSV score (sunset_code/helpers/hsv_score.json, mounted at /sunset_code)."""
    try:
        return Response(SCORE_CONFIG.read_text(), mimetype="application/json")
    except OSError as e:
        return jsonify({"error": str(e)}), 404


@app.route("/api/hist")
def get_hist():
    """A capture's sky histograms (hue / saturation / value shares), stored by the pipeline in sunset_hist."""
    found = list(client.query("SELECT hist FROM sunset_hist WHERE camera = $camera AND time = $ts",
                              bind_params={"camera": request.args.get("camera", ""), "ts": request.args.get("ts", "")}).get_points())
    if not found:
        return jsonify({"error": "no stored histogram (scored before they were stored)"}), 404
    return Response(found[0]["hist"], mimetype="application/json")


@app.route("/api/admin/rebuild", methods=["POST"])
def trigger_rebuild():
    """Trigger a docker compose rebuild via the webhook service."""
    webhook_url = os.environ.get("REBUILD_WEBHOOK_URL")
    token = os.environ.get("REBUILD_TOKEN", "changeme")

    if not webhook_url:
        return jsonify({"error": "Rebuild webhook not configured"}), 503

    try:
        resp = requests.post(webhook_url, headers={"X-Token": token}, timeout=5)
        if resp.status_code == 202:
            return jsonify({"status": "rebuilding", "message": "Rebuild started. Containers will restart shortly."})
        else:
            return jsonify({"error": "Webhook rejected request"}), resp.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8502, debug=False)
