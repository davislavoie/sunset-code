from astral.sun import sun
from astral import Observer
from datetime import date, timedelta, datetime, timezone
import os
import numpy as np
from matplotlib import pyplot as plt
from influxdb import InfluxDBClient
from sunset_code.helpers.open_metro_weater_api import weather_fetch


def sunset_time(day=date.today(), lat=44.477101, lon=-73.221253, altitude=200, timezone_str='America/New_York'):
    
    """
    Returns dict of UTC time intervals before and after sunset.
    """
    observer = Observer(latitude=lat, longitude=lon, elevation=altitude)
    s = sun(observer, date=day, tzinfo=timezone_str)

    sunset_dt = s['sunset']
    sunset_epoch = int(sunset_dt.timestamp())

    #Dict of intervals
    intervals = {
        "01_2h_pre": sunset_epoch - (60*60*2),
        "02_1h_pre": sunset_epoch - (60*60*1),
        "03_45m_pre": sunset_epoch - (60*45),
        "04_30m_pre": sunset_epoch - (60*30),
        "05_15m_pre": sunset_epoch - (60*15),
        "06_5m_pre": sunset_epoch - (60*5),
        "07_sunset": sunset_epoch,
        "08_5m_post": sunset_epoch + (60*5),
        "09_15m_post": sunset_epoch + (60*15),
        "10_30m_post": sunset_epoch + (60*30),
    }

    #print("[INFO] Local sunset epoch:", sunset_epoch)
    #print("[INFO] Local sunset readable:", sunset_dt.strftime("%Y-%m-%d %H:%M:%S"))

    return intervals


def influxdb_push(photo_file, time_epoch, label, camera_tag, score=0.0):

    """ Push data to InfluxDB """
    
    #python3 -m http.server 8080

    timestamp_iso = datetime.fromtimestamp(time_epoch, tz=timezone.utc).isoformat()
    date_str = datetime.fromtimestamp(time_epoch, tz=timezone.utc).strftime('%Y-%m-%d')

    #current_weather = weather_fetch(date=date_str, time_epoch = time_epoch)

    client = InfluxDBClient(host="localhost", port=8086, database="sunset_images")
    relative_path = os.path.relpath(photo_file, start=os.path.expanduser("~/Pictures"))
    url = f"http://100.107.153.41:8080/{relative_path}"

    #For re rankings 
    # Check if this is a ranked image (11_ or 12_ prefix)
    if label.startswith(("12_")):
        directory = os.path.dirname(relative_path)

        # Calculate bounds in nanoseconds (InfluxDB uses nanosecond precision)
        lower = int((time_epoch - 18000) * 1e9)  # 4 hours before, converted to nanoseconds
        upper = int((time_epoch + 18000) * 1e9)  # 4 hours after, converted to nanoseconds

        delete_query = (
            f'DELETE FROM "sunset_images" '
            f'WHERE "camera" = \'{camera_tag}\' '
            f'AND "label" =~ /11_|12_/ '
            f'AND time >= {lower} AND time <= {upper}'
        )
        print(f"[DEBUG] Executing delete query for time range {lower} to {upper}")
        result = client.query(delete_query)
        print(f"[DEBUG] Delete query result: {result}")
        print(f"[INFO] Deleted old 11_/12_ entries from directory: {directory}")

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

                # "temperature_2m": float(current_weather['temperature_2m'].values[0]),
                # "relative_humidity_2m": float(current_weather['relative_humidity_2m'].values[0]),
                # "dew_point_2m": float(current_weather['dew_point_2m'].values[0]),
                # "precipitation_probability": float(current_weather['precipitation_probability'].values[0]),
                # "precipitation": float(current_weather['precipitation'].values[0]),
                # "rain": float(current_weather['rain'].values[0]),
                # "showers": float(current_weather['showers'].values[0]),
                # "snowfall": float(current_weather['snowfall'].values[0]),
                # "cloud_cover_low": float(current_weather['cloud_cover_low'].values[0]),
                # "cloud_cover_mid": float(current_weather['cloud_cover_mid'].values[0]),
                # "cloud_cover_high": float(current_weather['cloud_cover_high'].values[0]),
                # "cloud_cover_total": float(current_weather['cloud_cover_total'].values[0]),
                # "visibility": float(current_weather['visibility'].values[0]),   
            }
        }
    ]

    try:
        print(f"[DEBUG] Writing to InfluxDB: label={label}, time={timestamp_iso}, camera={camera_tag}")
        result = client.write_points(point)
        print(f"[DEBUG] Write result: {result}")
    except Exception as e:
        print(f"[ERROR] Could not write points to InfluxDB: {e}")
        return

    print(f"[INFO] Pushed to InfluxDB: {label} | Score: {score} | URL: {url}")