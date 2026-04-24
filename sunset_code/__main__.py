
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sunset_code.helpers.helpers import sunset_time, influxdb_push
from sunset_code.helpers.get_photo import get_photo
from sunset_code.helpers.sunset_process import rank_sunset
from sunset_code.helpers.generate_ranked_image import generate_ranked_image
from datetime import datetime
import os
import time
import numpy as np
from matplotlib import pyplot as plt
import traceback

def main(youtube_url, lat, lon, altitude, timezone_str, camera_tag):
    intervals = sunset_time(lat=lat, lon=lon, altitude=altitude, timezone_str=timezone_str)
    max_score = -1
    max_final_txt_img = None

    for photo_interval, epoch_time in sorted(intervals.items(), key=lambda x: x[1]):
        now = time.time()

        if now > epoch_time:
            print(f"[{photo_interval}] Skipped — time has passed.")
            continue

        sleep_time = epoch_time - now
        print(f"[{photo_interval}] Sleeping for {int(sleep_time)}s until capture...")
        time.sleep(sleep_time)
        
        try:
            frame, photo_filename = get_photo(photo_interval, youtube_url, camera_tag)

            score, final_txt_img, name, hist_h, hist_s, hist_v, combined_mask_full_image, texts, bg_colors = rank_sunset(photo_filename)
            
            influxdb_push(photo_filename, epoch_time, photo_interval, score, camera_tag)

            print(f"[{photo_interval}] Score: {score} | Pushed to InfluxDB")

            if score > max_score:
                max_score = score
                max_final_txt_img = final_txt_img
                max_name = name
                max_hist_h = hist_h
                max_hist_s = hist_s
                max_hist_v = hist_v 
                max_epoch_time = epoch_time
                max_photo_file = photo_filename
                max_photo_dir = os.path.dirname(photo_filename)
                
        except Exception as e:
            print(f"[{photo_interval}] ERROR: {e}")
            #Error feedback
            print(f"Frame: {frame}, Photo Filename: {photo_filename}")
            traceback.print_exc()

    # Only generate ranked image if we have valid data
    if max_final_txt_img is not None:
        try:
            histogram_path, score_image_path = generate_ranked_image(max_final_txt_img, str(max_score), max_name, max_hist_h, max_hist_s, max_hist_v, max_photo_dir)

            #Get file name from path s
            histogram_name = os.path.basename(histogram_path)
            score_image_name = os.path.basename(score_image_path)

            # Push ranked image to influx db
            influxdb_push(histogram_path, max_epoch_time, histogram_name, camera_tag, str(max_score))
            influxdb_push(score_image_path, max_epoch_time, score_image_name, camera_tag, str(max_score))

            print(f"[INFO] Generating ranked image for best sunset (score: {max_score})")

        except Exception as e:
            print(f"[ERROR] Failed to generate ranked image: {e}")
    else:
        print("[INFO] No images were processed successfully")

    print(f"[INFO] Script finished at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", flush=True)



if __name__ == "__main__":
    
    print(f"[INFO] Script started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", flush=True)
    
    #Service template file at /etc/systemd/system/sunset_predictor@.service:
    
    #Input parameters
    #env config files in config folder
    youtube_url = os.environ.get("YOUTUBE_URL")
    camera_tag = os.environ.get("CAMERA_TAG")
    lat = float(os.environ.get("LAT"))
    lon = float(os.environ.get("LON"))
    altitude = float(os.environ.get("ALTITUDE"))
    timezone_str = os.environ.get("TIMEZONE")
        
    main(youtube_url, lat, lon, altitude, timezone_str, camera_tag)


#TEST MAIN FOR DEBUGGING
#MAIN
# if __name__ == "__main__":

#     intervals = sunset_time()
    
#     # TEST: Only process one image
#     photo_interval = "07_sunset"
#     epoch_time = intervals[photo_interval]
#     frame, photo_file = get_photo(photo_interval)
#     score, final_txt_img, name, hist_h, hist_s, hist_v, combined_mask_full_image, texts, bg_colors = rank_sunset(photo_file)

