# %%

from astral.sun import sun
from astral import Observer
from datetime import date, timedelta, datetime, timezone
import os
import time
import numpy as np
from matplotlib import pyplot as plt
from influxdb import InfluxDBClient
import glob
from sunset_process import rank_sunset
from generate_ranked_image import generate_ranked_image
from open_metro_weater_api import weather_fetch
from get_photo import get_photo
import traceback

# Runs once a day starting at 0000

print(f"[INFO] Script started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", flush=True)

def sunset_time(day=date.today(), lat=44.477101, lon=-73.221253, altitude=200, timezone='America/New_York'):
    """
    Returns dict of UTC time intervals before and after sunset.
    """
    observer = Observer(latitude=lat, longitude=lon, elevation=altitude)
    s = sun(observer, date=day, tzinfo=timezone)

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


def grafana_push(photo_file, time_epoch, label, score=0):

    """ Push data to InfluxDB """
    
    #python3 -m http.server 8080

    timestamp_iso = datetime.fromtimestamp(time_epoch, tz=timezone.utc).isoformat()
    date_str = datetime.fromtimestamp(time_epoch, tz=timezone.utc).strftime('%Y-%m-%d')

    current_weather = weather_fetch(date=date_str, time_epoch = time_epoch)

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
            f'WHERE "label" =~ /11_|12_/ '
            f'AND time >= {lower} AND time <= {upper}'
        )
        client.query(delete_query)
        print(f"[INFO] Deleted {label} from directory: {directory}")

    point = [
        {
            "measurement": "sunset_images",
            
            "tags": {
                "label": label 
            },
            "time": timestamp_iso,
            "fields": {
                "url": url,
                "score": str(score),

                "temperature_2m": float(current_weather['temperature_2m'].values[0]),
                "relative_humidity_2m": float(current_weather['relative_humidity_2m'].values[0]),
                "dew_point_2m": float(current_weather['dew_point_2m'].values[0]),
                "precipitation_probability": float(current_weather['precipitation_probability'].values[0]),
                "precipitation": float(current_weather['precipitation'].values[0]),
                "rain": float(current_weather['rain'].values[0]),
                "showers": float(current_weather['showers'].values[0]),
                "snowfall": float(current_weather['snowfall'].values[0]),
                "cloud_cover_low": float(current_weather['cloud_cover_low'].values[0]),
                "cloud_cover_mid": float(current_weather['cloud_cover_mid'].values[0]),
                "cloud_cover_high": float(current_weather['cloud_cover_high'].values[0]),
                "cloud_cover_total": float(current_weather['cloud_cover_total'].values[0]),
                "visibility": float(current_weather['visibility'].values[0]),   
            }
        }
    ]

    try:
        client.write_points(point)
    except Exception as e:
        print(f"[ERROR] Could not write points to InluxDB: {e}")
        return

    print(f"[INFO] Pushed to InfluxDB: {label} | Score: {score} | URL: {url}")

# # #MAIN
if __name__ == "__main__":
    intervals = sunset_time()
    max_score = -1
    max_final_txt_img = None

    for label, epoch_time in sorted(intervals.items(), key=lambda x: x[1]):
        now = time.time()

        if now > epoch_time:
            print(f"[{label}] Skipped — time has passed.")
            continue

        sleep_time = epoch_time - now
        print(f"[{label}] Sleeping for {int(sleep_time)}s until capture...")
        time.sleep(sleep_time)
        
        try:
            frame, photo_file = get_photo(label)

            score, final_txt_img, name, hist_h, hist_s, hist_v, combined_mask_full_image, texts, bg_colors = rank_sunset(photo_file)
            
            grafana_push(photo_file, epoch_time, label, score)

            print(f"[{label}] Score: {score} | Pushed to Grafana")

            if float(score) > max_score:
                max_score = float(score)
                max_final_txt_img = final_txt_img
                max_name = name
                max_hist_h = hist_h
                max_hist_s = hist_s
                max_hist_v = hist_v 
                max_epoch_time = epoch_time
                max_photo_file = photo_file
                max_photo_dir = os.path.dirname(photo_file)
                
        except Exception as e:
            print(f"[{label}] ERROR: {e}")
            #Error feedback
            print(f"Frame: {frame}, Photo File: {photo_file}")

            traceback.print_exc()

    # Only generate ranked image if we have valid data
    if max_final_txt_img is not None:
        try:
            histogram_path, score_image_path = generate_ranked_image(max_final_txt_img, str(max_score), max_name, max_hist_h, max_hist_s, max_hist_v, max_photo_dir)

            #Get file name from path 
            histogram_name = os.path.basename(histogram_path)
            score_image_name = os.path.basename(score_image_path)

            # Push ranked image to influx db

            grafana_push(histogram_path, max_epoch_time, histogram_name, str(max_score))
            grafana_push(score_image_path, max_epoch_time, score_image_name, str(max_score))

            print(f"[INFO] Generating ranked image for best sunset (score: {max_score})")

        except Exception as e:
            print(f"[ERROR] Failed to generate ranked image: {e}")
    else:
        print("[INFO] No images were processed successfully")

    print(f"[INFO] Script finished at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", flush=True)



#TEST MAIN FOR DEBUGGING
#MAIN
# if __name__ == "__main__":

#     intervals = sunset_time()
    
#     # TEST: Only process one image
#     label = "07_sunset"
#     epoch_time = intervals[label]
#     frame, photo_file = get_photo(label)
#     score, final_txt_img, name, hist_h, hist_s, hist_v, combined_mask_full_image, texts, bg_colors = rank_sunset(photo_file)

   