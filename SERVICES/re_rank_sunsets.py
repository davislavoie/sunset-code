# %%
import importlib
import sunset_process
importlib.reload(sunset_process)
from sunset_process import rank_sunset
import os
import glob
import matplotlib.pyplot as plt
import numpy as np
from influxdb import InfluxDBClient
from datetime import date, timedelta, datetime, timezone
from generate_ranked_image import generate_ranked_image
from sunset_predictor import grafana_push
import pytz
from sunset_predictor import sunset_time
from datetime import datetime

def filename_to_epoch(filename):
    """Extract epoch time from filename formatted as 'prefix_MM-DD-YYYY.ext'."""
    base = os.path.basename(filename)
    base_no_ext = os.path.splitext(base)[0]  # e.g. "01_2h_pre_11-05-2025"
    parts = base_no_ext.split("_")
    if len(parts) < 2:
        print(f"[ERROR] Unexpected filename format: {filename}")
        return None

    date_str = parts[-1]
    try:
        day = datetime.strptime(date_str, "%m-%d-%Y").date()
    except ValueError:
        print(f"[ERROR] Could not parse date from filename: {filename}")
        return None

    intervals = sunset_time(day=day)

    # normalize tokens (common variants: '15min' -> '15m', '2hr' -> '2h', remove extra hyphens)
    norm_tokens = []
    for tok in parts[:-1]:
        t = tok.replace("min", "m").replace("mins", "m").replace("minute", "m").replace("minutes", "m")
        t = t.replace("hrs", "h").replace("hr", "h").replace("hours", "h").replace("hour", "h")
        t = t.replace("-", "_")
        # collapse repeated letters (e.g. '2hh' -> '2h') and trim
        while "hh" in t:
            t = t.replace("hh", "h")
        norm_tokens.append(t)

    base_norm = "_".join(norm_tokens)
    base_orig = "_".join(parts[:-1])

    # Try direct match of normalized or original prefix first
    epoch_time = None
    if base_norm in intervals:
        epoch_time = intervals[base_norm]
    elif base_orig in intervals:
        epoch_time = intervals[base_orig]
    else:
        # progressive fallback: try progressively shorter prefixes (normalized then original)
        for j in range(len(norm_tokens), 0, -1):
            candidate = "_".join(norm_tokens[:j])
            if candidate in intervals:
                epoch_time = intervals[candidate]
                break
        if epoch_time is None:
            for j in range(len(parts) - 1, 0, -1):
                candidate = "_".join(parts[:j])
                if candidate in intervals:
                    epoch_time = intervals[candidate]
                    break

    #Add prints to debug
    if epoch_time is None:
        print(f"[ERROR] Could not find interval key for filename: {filename}")
        print(f"[ERROR] Available intervals: {list(intervals.keys())}")
        print(f"[ERROR] Extracted date: {date_str}")
        print(f"[ERROR] Parts: {parts}")
        print(f"[ERROR] Normalized base: {base_norm} | Tried candidates: {[ '_'.join(norm_tokens[:j]) for j in range(len(norm_tokens),0,-1)] + [ '_'.join(parts[:j]) for j in range(len(parts)-1,0,-1)]}")

    return epoch_time

local_tz = pytz.timezone("America/New_York")
client = InfluxDBClient(host="100.107.153.41", port=8086, database="sunset_images")
results = client.query("SELECT * FROM sunset_images")
#Delete all data
client.query('DELETE FROM "sunset_images"')
print("[INFO] Cleared existing data from InfluxDB 'sunset_images' database.")

# Input Directory
sunset_root = "/home/dlavoie/Pictures/sunset_images/"


sunset_list = ( 
                os.path.join(sunset_root, "**", "01*.jpg"),
                os.path.join(sunset_root, "**", "02*.jpg"),
                os.path.join(sunset_root, "**", "03*.jpg"),
                os.path.join(sunset_root, "**", "04*.jpg"),
                os.path.join(sunset_root, "**", "05*.jpg"),
                os.path.join(sunset_root, "**", "06*.jpg"),
                os.path.join(sunset_root, "**", "07*.jpg"),
                os.path.join(sunset_root, "**", "08*.jpg"),
                os.path.join(sunset_root, "**", "09*.jpg"),
                os.path.join(sunset_root, "**", "10*.jpg"),
            )

#Ten group scores for images
#First group is 01_*.jpg ...
group_scores = [[], [], [], [], [], [], [], [], [], []]
all_images_scores = [[], [], [], [], [], [], [], [], [], []]

for i in range(len(sunset_list)):
    for img_path in glob.glob(sunset_list[i], recursive=True):
        score, final_txt_img, name, hist_h, hist_s, hist_v, combined_mask_full_image, texts, bg_colors = rank_sunset(img_path)
        result = (score, final_txt_img, name, hist_h, hist_s, hist_v, img_path)
        group_scores[i].append(result)
        all_images_scores[i].append(result)

# Debug: Print group lengths
print("[DEBUG] Group lengths:")
for idx, group in enumerate(all_images_scores):
    print(f"  Group {idx} (0{idx+1}_*.jpg): {len(group)} images")

# group_Scores[0] is all the scores for 06_*.jpg etc
# group_scores[0][0] is the first image data in 06_*.jpg
# group_scores[0][0][0] is the score of the first image in 06_*.jpg
# group_scores[0][0][1] is the image itself 06_*.jpg
# group_scores[0][0][2] is the name of the first image in 06_*.jpg
# group_scores[0][0][3] is the hist_h of the first image in 06_*.jpg
# group_scores[0][0][4] is the hist_s of the first image in 06_*.jpg
# group_scores[0][0][5] is the hist_v of the first image in 06_*.jpg
# group_scores[0][0][6] is the full path of the first image in 06_*.jpg

# Group images by date instead of by index
# Extract date from each image and organize by date
images_by_date = {}

for group_idx in range(len(group_scores)):
    for img_idx, result in enumerate(group_scores[group_idx]):
        if result is None:
            continue
        
        img_path = result[6]
        # Extract date from filename (format: prefix_MM-DD-YYYY.jpg)
        base_name = os.path.basename(img_path)
        # Get date part (last part before extension)
        date_part = base_name.rsplit('_', 1)[-1].replace('.jpg', '')
        
        if date_part not in images_by_date:
            images_by_date[date_part] = {}
        
        images_by_date[date_part][group_idx] = result

# Now find and mark the highest score for each date
for date, groups_dict in images_by_date.items():
    max_score = -1
    max_group_idx = -1
    
    # Find max score for this date
    for group_idx, result in groups_dict.items():
        score = float(result[0])
        if score > max_score:
            max_score = score
            max_group_idx = group_idx
    
    # Mark all non-max images for this date as None
    for group_idx, result in groups_dict.items():
        score = float(result[0])
        if group_idx != max_group_idx:
            # Find and mark as None in the original group_scores
            for img_idx, img_result in enumerate(group_scores[group_idx]):
                if img_result and img_result[6] == result[6]:
                    group_scores[group_idx][img_idx] = None
                    break

# Now generate ranked images for the remaining max-score images
for group_idx in range(len(group_scores)):
    for img_idx, result in enumerate(group_scores[group_idx]):
        if result is not None:
            score = result[0]
            final_txt_img = result[1]
            name = result[2]
            hist_h = result[3]
            hist_s = result[4]
            hist_v = result[5]
            img_path = result[6]
            photo_dir = os.path.dirname(img_path)  # Get directory path without filename

            #Remove prefix
            clean_name = name[3:]

            # Clean up existing files with 11_ or 12_ prefix in the output directory
            for existing_file in glob.glob(os.path.join(photo_dir, "11_*.png")):
                os.remove(existing_file)
            for existing_file in glob.glob(os.path.join(photo_dir, "12_*.png")):
                os.remove(existing_file)

            #Generates and saves ranked image and histogram
            histogram_path, score_image_path = generate_ranked_image(final_txt_img, score, name, hist_h, hist_s, hist_v, photo_dir)
            
            #Histogram name
            histogram_name = os.path.basename(histogram_path)
            score_image_name = os.path.basename(score_image_path)

            epoch_time = filename_to_epoch(img_path)

            # Push to Grafana
            print(f"[INFO] Pushing ranked image for {name} with score {score} at epoch time {epoch_time}")

            grafana_push(histogram_path, epoch_time, histogram_name, score)
            grafana_push(score_image_path, epoch_time, score_image_name, score)

# #Push all images to influx with scoring data
# Find the maximum length across all groups
max_images = max(len(group) for group in all_images_scores) if all_images_scores else 0

for i in range(max_images):
    for b in range(len(all_images_scores)):
        # Skip this group if it doesn't have an image at index i
        if i >= len(all_images_scores[b]):
            print(f"[DEBUG] Group {b} (0{b+1}_*.jpg) doesn't have image index {i}, skipping")
            continue
        
        score = (all_images_scores[b][i][0])
        name = all_images_scores[b][i][2]
        img_path = all_images_scores[b][i][6]
        photo_dir = os.path.dirname(img_path)

        epoch_time = filename_to_epoch(img_path)

        print(f"[INFO] Pushing image {name} with score {score} at epoch time {epoch_time}")
        grafana_push(img_path, epoch_time, name, score)




# %%
