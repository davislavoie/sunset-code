
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sunset_code.helpers.helpers import sunset_time, influxdb_push
from sunset_code.helpers.get_photo import get_photo
from sunset_code.helpers.sunset_process import rank_sunset
# generate_ranked_image is no longer called: see the note at the end of main().
from datetime import datetime
import os
import time
import traceback

def main(youtube_url, lat, lon, altitude, timezone_str, camera_tag, mode='sunset'):
    intervals = sunset_time(lat=lat, lon=lon, altitude=altitude, timezone_str=timezone_str, mode=mode)

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

            score, fields, hist = rank_sunset(photo_filename)

            influxdb_push(photo_filename, epoch_time, photo_interval, camera_tag, score, fields=fields, hist=hist)

            print(f"[{photo_interval}] Score: {score} | Pushed to InfluxDB")

        except Exception as e:
            print(f"[{photo_interval}] ERROR: {e}")
            #Error feedback - removed Frame print to avoid massive array output
            print(f"Photo Filename: {photo_filename}")
            traceback.print_exc()

    # Ranked image + histogram PNGs (11_ranked / 12_histogram) are turned off (2026-10-13). The dashboard
    # works out each day's best shot from the captures' scores, draws the colour overlay in the browser and
    # shows the breakdown + histograms stored with each capture above, so the PNGs and their InfluxDB points
    # were extra work nobody saw. generate_ranked_image.py is kept for reference.

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
    mode = os.environ.get("MODE", "sunset").lower()

    main(youtube_url, lat, lon, altitude, timezone_str, camera_tag, mode)


#TEST MAIN FOR DEBUGGING
#MAIN
# if __name__ == "__main__":

#     intervals = sunset_time()
    
#     # TEST: Only process one image
#     photo_interval = "07_sunset"
#     epoch_time = intervals[photo_interval]
#     frame, photo_file = get_photo(photo_interval)
#     score, final_txt_img, name, hist_h, hist_s, hist_v, combined_mask_full_image, texts, bg_colors = rank_sunset(photo_file)

