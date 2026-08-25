from flask import Flask, jsonify, request, send_from_directory, Response
from influxdb import InfluxDBClient
from datetime import datetime
from pathlib import Path
import os
import pytz
import time
import requests
import glob
import re
import yaml

app = Flask(__name__, static_folder="static", static_url_path="")

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

CACHE_TTL = 300  # seconds, mirrors @st.cache_data(ttl=300) in streamlit_project/app.py
_cache = {}


def fetch_camera_data(camera_tag):
    """Fetch and process all data for a camera (mirrors app.py's fetch_camera_data)."""
    results = client.query(f"SELECT * FROM sunset_images WHERE camera = '{camera_tag}'")

    sunset_data = []
    all_data = []
    ranked_images = []

    points_list = list(results.get_points())

    for point in points_list:
        dt_utc = datetime.strptime(point["time"], "%Y-%m-%dT%H:%M:%SZ")
        dt_local = dt_utc.replace(tzinfo=pytz.utc).astimezone(local_tz)
        date_str = dt_local.strftime("%Y-%m-%d")
        time_str = dt_local.strftime("%I:%M %p")

        data_item = {
            "Date": date_str,
            "Time": time_str,
            "Label": point["label"],
            "Image": point["url"],
            "Score": 0 if point["score"] is None else point["score"],
        }

        all_data.append(data_item)

        if point.get("label", "").startswith("07_"):
            sunset_data.append(data_item)

        if point.get("label", "").startswith("11_"):
            epoch_time = point["time"]
            matching_photo = [
                p for p in points_list
                if p["time"] == epoch_time and not p.get("label", "").startswith(("11_", "12_"))
            ]
            matching_photo_url = matching_photo[0]["url"] if matching_photo else None
            hsv_photo = [
                p for p in points_list
                if p["time"] == epoch_time and p.get("label", "").startswith("12_")
            ]

            ranked_images.append({
                "Ranked Image": point["url"],
                "Raw Image": matching_photo_url,
                "HSV Image": hsv_photo[0]["url"] if hsv_photo else None,
                "Score": 0 if point["score"] is None else point["score"],
                "Date": date_str,
                "Time": time_str,
                "dt_local": dt_local.isoformat(),
                "Label": point["label"],
            })

    return {"sunset_data": sunset_data, "all_data": all_data, "ranked_images": ranked_images}


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
    resp = requests.get(url, timeout=10)
    return Response(resp.content, mimetype=resp.headers.get("Content-Type", "image/jpeg"))


@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


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


@app.route("/api/camera-configs")
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


@app.route("/api/camera-configs", methods=["POST"])
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


@app.route("/api/camera-configs/<camera_tag>", methods=["PUT"])
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


@app.route("/api/camera-configs/<camera_tag>", methods=["DELETE"])
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


@app.route("/api/add-compose-service", methods=["POST"])
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


@app.route("/api/rebuild", methods=["POST"])
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
