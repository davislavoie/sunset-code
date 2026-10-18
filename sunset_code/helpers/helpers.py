import json
from astral.sun import sun
from astral import Observer
from datetime import date, timedelta, datetime, timezone
import os
import numpy as np
from matplotlib import pyplot as plt
from influxdb import InfluxDBClient
from sunset_code.helpers.open_metro_weater_api import weather_fetch, path_clouds


def sunset_time(day=date.today(), lat=44.477101, lon=-73.221253, altitude=200, timezone_str='America/New_York', mode='sunset'):

    """
    Returns dict of UTC time intervals before and after sunset or sunrise.
    mode: 'sunset' or 'sunrise'
    """
    observer = Observer(latitude=lat, longitude=lon, elevation=altitude)
    s = sun(observer, date=day, tzinfo=timezone_str)

    if mode == 'sunrise':
        target_dt = s['sunrise']
        target_label = "07_sunrise"
    else:
        target_dt = s['sunset']
        target_label = "07_sunset"

    target_epoch = int(target_dt.timestamp())

    #Dict of intervals
    intervals = {
        "01_2h_pre": target_epoch - (60*60*2),
        "02_1h_pre": target_epoch - (60*60*1),
        "03_45m_pre": target_epoch - (60*45),
        "04_30m_pre": target_epoch - (60*30),
        "05_15m_pre": target_epoch - (60*15),
        "06_5m_pre": target_epoch - (60*5),
        target_label: target_epoch,
        "08_5m_post": target_epoch + (60*5),
        "09_15m_post": target_epoch + (60*15),
        "10_30m_post": target_epoch + (60*30),
    }

    return intervals


def influxdb_push(photo_file, time_epoch, label, camera_tag, score=0.0, fields=None, hist=None):

    """ Push data to InfluxDB. fields: rank_sunset's score breakdown, stored on the same point. hist: its sky
    histograms, stored in the sunset_hist measurement (same tags and time) so the dashboard's main query,
    which reads every point of a camera, stays small. """
    
    #python3 -m http.server 8080

    timestamp_iso = datetime.fromtimestamp(time_epoch, tz=timezone.utc).isoformat()

    # Weather for the capture (not the generated 11_/12_ images). Best effort: if Open-Meteo
    # is down the capture is still saved, and ai_analysis fills the weather in later.
    weather_fields = {}
    if not label.startswith(("11_", "12_")):
        try:
            current_weather = weather_fetch(time_epoch=time_epoch)
            for name in ["temperature_2m", "relative_humidity_2m", "dew_point_2m", "precipitation_probability",
                         "precipitation", "rain", "showers", "snowfall", "cloud_cover_low", "cloud_cover_mid",
                         "cloud_cover_high", "cloud_cover_total", "visibility"]:
                value = float(current_weather[name].values[0])
                if not np.isnan(value):  # InfluxDB rejects NaN, which would lose the whole point
                    weather_fields[name] = value
        except Exception as e:
            print(f"[WARN] Weather fetch failed, saving capture without it: {e}")
        try:
            weather_fields.update(path_clouds(time_epoch=time_epoch))
        except Exception as e:
            print(f"[WARN] Clouds toward the sunset failed, saving capture without them: {e}")

    influxdb_host = os.environ.get("INFLUXDB_HOST", "localhost")
    influxdb_port = int(os.environ.get("INFLUXDB_PORT", 8086))
    pictures_dir = os.environ.get("PICTURES_DIR", os.path.expanduser("~/Pictures"))
    image_base_url = os.environ.get("IMAGE_BASE_URL", "http://100.107.153.41:8080")

    client = InfluxDBClient(host=influxdb_host, port=influxdb_port, database="sunset_images")
    relative_path = os.path.relpath(photo_file, start=pictures_dir)
    url = f"{image_base_url}/{relative_path}"

    point = [
        {
            "measurement": "sunset_images",
            
            "tags": {
                "label": label,
                "camera": camera_tag,
            },
            "time": timestamp_iso,
            "fields": {
                "url": url,
                "score": float(score),
                **(fields or {}),
                **weather_fields,
            }
        }
    ]
    if hist is not None:
        point.append({"measurement": "sunset_hist", "tags": {"label": label, "camera": camera_tag},
                      "time": timestamp_iso, "fields": {"hist": json.dumps(hist, separators=(",", ":"))}})

    try:
        print(f"[DEBUG] Writing to InfluxDB: label={label}, time={timestamp_iso}, camera={camera_tag}")
        result = client.write_points(point)
        print(f"[DEBUG] Write result: {result}")
    except Exception as e:
        print(f"[ERROR] Could not write points to InfluxDB: {e}")
        return

    print(f"[INFO] Pushed to InfluxDB: {label} | Score: {score} | URL: {url}")