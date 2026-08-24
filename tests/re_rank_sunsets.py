# %%
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import importlib
import sunset_code.helpers.sunset_process
importlib.reload(sunset_code.helpers.sunset_process)
from sunset_code.helpers.sunset_process import rank_sunset
import glob
import matplotlib.pyplot as plt
import numpy as np
from influxdb import InfluxDBClient
from datetime import date, timedelta, datetime, timezone
from sunset_code.helpers.generate_ranked_image import generate_ranked_image
from sunset_code.helpers.helpers import influxdb_push, sunset_time
import pytz
from datetime import datetime
from simple_term_menu import TerminalMenu


def select_rerank_mode_and_month(sunset_root):
    """
    Prompts user to select re-rank mode: all or specific month. If month, shows available months from file tree.
    Returns (mode, month) where mode is 'all' or 'month', and month is None or 'YYYY-MM'.
    """
    from simple_term_menu import TerminalMenu
    import glob
    import re
    # Find all jpg files recursively
    jpg_files = glob.glob(os.path.join(sunset_root, "**", "*.jpg"), recursive=True)
    # Extract months from filenames (expects MM-DD-YYYY)
    month_set = set()
    for f in jpg_files:
        base = os.path.basename(f)
        match = re.search(r"(\d{2})-(\d{2})-(\d{4})", base)
        if match:
            mm, dd, yyyy = match.groups()
            month_set.add(f"{yyyy}-{mm}")
    months = sorted(list(month_set))
    # Menu for all/month
    options = ["Re-rank ALL", "Re-rank by MONTH"]
    menu = TerminalMenu(options, title="Select re-rank mode:")
    idx = menu.show()
    if idx == 0:
        return ("all", None)
    elif idx == 1:
        if not months:
            print("[ERROR] No months found in images.")
            return ("all", None)
        month_menu = TerminalMenu(months, title="Select month (YYYY-MM):")
        m_idx = month_menu.show()
        if m_idx is None:
            print("[ERROR] No month selected. Defaulting to ALL.")
            return ("all", None)
        return ("month", months[m_idx])
    else:
        return ("all", None)

def select_camera_tag(sunset_root_base):
    """
    Scans sunset_root_base for subdirectories (camera tags).
    If multiple exist, prompts user to select one with arrow keys.
    Returns the selected camera_tag and full path.
    """
    # Find all subdirectories in the sunset_root_base
    subdirs = [d for d in os.listdir(sunset_root_base) 
               if os.path.isdir(os.path.join(sunset_root_base, d))]
    
    if not subdirs:
        print(f"[ERROR] No camera directories found in {sunset_root_base}")
        return None, None
    
    if len(subdirs) == 1:
        camera_tag = subdirs[0]
        print(f"[INFO] Auto-selected camera tag: {camera_tag}")
    else:
        print(f"\n[INFO] Multiple camera directories found. Please select one:")
        menu = TerminalMenu(subdirs, title="Select Camera Tag:")
        selected_idx = menu.show()
        if selected_idx is None:
            print("[ERROR] No selection made.")
            return None, None
        camera_tag = subdirs[selected_idx]
        print(f"[INFO] Selected camera tag: {camera_tag}")
    
    sunset_root = os.path.join(sunset_root_base, camera_tag)
    return camera_tag, sunset_root

def filename_to_epoch(filename, camera_tag=None, mode='sunset'):

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

    #Grab lat and lon from camera tag
    intervals = sunset_time(day=day, mode=mode)

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

# Input Directory
sunset_root_base = "/home/dlavoie/Pictures/sunset_images/"
camera_tag, sunset_root = select_camera_tag(sunset_root_base)

if camera_tag is None:
    raise SystemExit("[ERROR] No camera tag selected. Exiting.")

# Delete only data for the selected camera tag
client.query(f'DELETE FROM "sunset_images" WHERE "camera" = \'{camera_tag}\'')
print(f"[INFO] Cleared existing data for camera '{camera_tag}' from InfluxDB 'sunset_images' database.")

print(f"[INFO] Using sunset root: {sunset_root}")

# Detect mode from existing filenames (sunrise vs sunset)
sample_files = glob.glob(os.path.join(sunset_root, "**", "07_*.jpg"), recursive=True)
detected_mode = 'sunset'
for f in sample_files:
    if '07_sunrise' in os.path.basename(f):
        detected_mode = 'sunrise'
        break
print(f"[INFO] Detected mode: {detected_mode}")


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
    for photo_filepath in glob.glob(sunset_list[i], recursive=True):
        photo_filename = os.path.basename(photo_filepath)
        score, final_txt_img, name, hist_h, hist_s, hist_v, combined_mask_full_image, texts, bg_colors = rank_sunset(photo_filepath)
        result = (score, final_txt_img, photo_filename, hist_h, hist_s, hist_v, photo_filepath)
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
# group_scores[0][0][2] is the photo_filename of the first image in 06_*.jpg
# group_scores[0][0][3] is the hist_h of the first image in 06_*.jpg
# group_scores[0][0][4] is the hist_s of the first image in 06_*.jpg
# group_scores[0][0][5] is the hist_v of the first image in 06_*.jpg
# group_scores[0][0][6] is the photo_filepath (full path) of the first image in 06_*.jpg

# Group images by date instead of by index
# Extract date from each image and organize by date
images_by_date = {}

for group_idx in range(len(group_scores)):
    for img_idx, result in enumerate(group_scores[group_idx]):
        if result is None:
            continue
        
        photo_filepath = result[6]
        # Extract date from filename (format: prefix_MM-DD-YYYY.jpg)
        photo_filename = os.path.basename(photo_filepath)
        # Get date part (last part before extension)
        date_part = photo_filename.rsplit('_', 1)[-1].replace('.jpg', '')
        
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
            photo_filename = result[2]
            hist_h = result[3]
            hist_s = result[4]
            hist_v = result[5]
            photo_filepath = result[6]
            photo_dir = os.path.dirname(photo_filepath)  # Get directory path without filename

            #Remove prefix
            clean_name = photo_filename[3:]

            # Clean up existing files with 11_ or 12_ prefix in the output directory
            for existing_file in glob.glob(os.path.join(photo_dir, "11_*.png")):
                os.remove(existing_file)
            for existing_file in glob.glob(os.path.join(photo_dir, "12_*.png")):
                os.remove(existing_file)

            #Generates and saves ranked image and histogram
            histogram_filepath, score_image_filepath = generate_ranked_image(final_txt_img, score, photo_filename, hist_h, hist_s, hist_v, photo_dir)
            
            #Histogram filename
            histogram_filename = os.path.basename(histogram_filepath)
            score_image_filename = os.path.basename(score_image_filepath)

            epoch_time = filename_to_epoch(photo_filepath, mode=detected_mode)

            # Push to Grafana
            print(f"[INFO] Pushing ranked image for {photo_filename} with score {score} at epoch time {epoch_time}")

            influxdb_push(histogram_filepath, epoch_time, histogram_filename, camera_tag, score)
            influxdb_push(score_image_filepath, epoch_time, score_image_filename, camera_tag, score)

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
        photo_filename = all_images_scores[b][i][2]
        photo_filepath = all_images_scores[b][i][6]
        photo_dir = os.path.dirname(photo_filepath)

        epoch_time = filename_to_epoch(photo_filepath, mode=detected_mode)

        print(f"[INFO] Pushing image {photo_filename} with score {score} at epoch time {epoch_time}")
        influxdb_push(photo_filepath, epoch_time, photo_filename, camera_tag, score)




# %%
