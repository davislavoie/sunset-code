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

app = Flask(__name__, static_folder="static", static_url_path="")

# Config directory - look for it relative to the project root
CONFIG_DIR = Path(__file__).parent.parent / "config"

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
    if CONFIG_DIR.exists():
        for env_file in CONFIG_DIR.glob("*.env"):
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
    required_fields = ["CAMERA_TAG", "YOUTUBE_URL", "LAT", "LON", "ALTITUDE", "TIMEZONE"]

    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Missing required field: {field}"}), 400

    camera_tag = data["CAMERA_TAG"]
    if not re.match(r"^[a-zA-Z0-9_-]+$", camera_tag):
        return jsonify({"error": "CAMERA_TAG must be alphanumeric with underscores/hyphens only"}), 400

    filename = f"{camera_tag}.env"
    filepath = CONFIG_DIR / filename

    if filepath.exists():
        return jsonify({"error": f"Config file {filename} already exists"}), 409

    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w") as f:
            for field in required_fields:
                f.write(f"{field}={data[field]}\n")
        return jsonify({"success": True, "filename": filename})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8502, debug=False)
