# %%
import json
from pathlib import Path

import cv2
import numpy as np

# Every number in the score (hue bands, weights, contrast, soft cap) lives in hsv_score.json, which the
# dashboard reads too (overlay colours, Ranking explained), so a tweak is one edit in one place.
CONFIG = json.loads((Path(__file__).parent / "hsv_score.json").read_text())


def rank_sunset(frame):
    """Score a photo 0-100 from the colours in its sky (top half).

    Returns (score, fields, hist):
      fields: the breakdown stored next to the score in InfluxDB, so the dashboard shows it without
              recomputing: per colour points / coverage / saturation, and the cloud contrast pieces.
      hist:   the sky's hue / saturation / value histograms as shares of the sky (stored separately).
    No images are drawn here any more (the dashboard draws the overlay in the browser); draw_overlay()
    below makes the old annotated image for debugging (tests/sunset_process_testing.py).
    """
    img = cv2.imread(frame)

    if img is None:
        print(f"Error: Could not load image '{frame}'")
        return None

    #horizon_img, horizon_y = find_horizon(img)
    horizon_y = img.shape[0] // 2
    sky_image = img[:horizon_y, :]

    hsv = cv2.cvtColor(sky_image, cv2.COLOR_BGR2HSV)
    h, s, v = hsv[:,:,0], hsv[:,:,1], hsv[:,:,2]
    hist = {name: (cv2.calcHist([c], [0], None, [n], [0, n]).ravel() / c.size).round(5).tolist()
            for name, c, n in (("hue", h, 180), ("saturation", s, 256), ("value", v, 256))}

    total_pixels = img.shape[0] * img.shape[1]

    #RANKING METRICS
    # Ignore near-black pixels: their hue/saturation is noise, which made dark night frames
    # score as vivid red (e.g. a black frame scoring 100). 38 = 15% of full brightness.
    bright = v >= CONFIG["min_brightness"]

    # One mask per hue band (red, orange, pink, yellow). Pink only counts at v >= 128 (half brightness):
    # dim mauve / grey-purple cloud at dusk isn't a pink sunset (analysis/hsv_tuning.md).
    fields = {}
    score = 0.0
    coloured = np.zeros_like(bright)
    for color, band in CONFIG["bands"].items():
        in_band = (h >= band["hue"][0]) & (h <= band["hue"][1]) & (s >= band["sat_min"])
        coloured |= in_band & bright
        mask = in_band & (v >= band["val_min"])
        points = calculate_saturation_weighted_score(mask, s, total_pixels, power=CONFIG["power"]) * band["weight"]
        score += points
        fields[f"{color}_points"] = float(points)
        fields[f"{color}_coverage"] = float(np.count_nonzero(mask) / total_pixels)
        fields[f"{color}_saturation"] = float(s[mask].mean()) if mask.any() else 0.0

    # Cloud colour contrast (analysis/hsv_tuning.md): several hues at once (orange with pink) and lit cloud
    # standing out from the rest of the sky look better than one flat colour. Both fitted to My ranking.
    hue_spread, lit_contrast = 0.0, 0.0
    if coloured.any():
        angle = h[coloured] * (np.pi / 90)  # OpenCV hue 0-179 around the circle, so red and pink are neighbours
        hue_spread = np.sqrt(max(0, -2 * np.log(max(np.hypot(np.cos(angle).mean(), np.sin(angle).mean()), 1e-6))))
        rest = ~coloured & bright
        if rest.any():
            lit_contrast = v[coloured].mean() - v[rest].mean()
    c = CONFIG["contrast"]
    contrast = max(0, c["hue_base"] + c["hue_slope"] * hue_spread) * max(0, c["lit_base"] + c["lit_slope"] * lit_contrast)
    score *= contrast
    fields.update(hue_spread=float(hue_spread), lit_contrast=float(lit_contrast), contrast=float(contrast))

    # Soft cap instead of min(100, score): fitted to the My ranking scores (analysis/my_rank.md, refitted in
    # hsv_tuning.md). Same order, closer to how good the days look, and big days no longer all tie at 100.
    score = round(100 * (1 - np.exp(-score / CONFIG["soft_cap"])), 2)

    return score, fields, hist


def draw_overlay(frame):
    """Debug view only, not used by the pipeline: the photo with the counted sky pixels painted in
    (red, orange, pink, yellow) and the coverage of each written on it."""
    img = cv2.imread(frame)
    sky_image = img[:img.shape[0] // 2]
    bot_image = img[img.shape[0] // 2:]
    hsv = cv2.cvtColor(sky_image, cv2.COLOR_BGR2HSV)
    h, s, v = hsv[:,:,0], hsv[:,:,1], hsv[:,:,2]
    paint = {"red": (0, 0, 255), "orange": (0, 140, 255), "pink": (255, 0, 255), "yellow": (0, 255, 255)}
    out, texts, bg_colors = sky_image, [], []
    for color, band in CONFIG["bands"].items():
        mask = (h >= band["hue"][0]) & (h <= band["hue"][1]) & (s >= band["sat_min"]) & (v >= band["val_min"])
        out = opacity_overlay(out, mask, color=paint[color], opacity=0.5)
        texts.append(f"{color.title()}: {np.count_nonzero(mask) / img[:, :, 0].size:.2%}")
        bg_colors.append(paint[color])
    return put_text_with_opacity_bg(np.vstack((out, bot_image)), texts, bg_colors)

#Helper functions
def opacity_overlay(image, mask, color=(0, 0, 255), opacity=0.5):
    overlay = image.copy()
    mask_bool = mask.astype(bool)
    color_arr = np.array(color, dtype=np.float32)
    
    overlay[mask_bool] = (opacity * color_arr + (1 - opacity) * overlay[mask_bool]).astype(np.uint8)
    
    return overlay
def put_text_with_opacity_bg(image, texts,  bg_colors, position=(5, 50),font_scale=1.55, thickness=3, 
                             line_spacing=31, bg_opacity=0.4,):
   
    img = image.copy()
    x, y = position
    font=cv2.FONT_HERSHEY_COMPLEX_SMALL
    text_color=(255, 255, 255)

    for i, text in enumerate(texts):
        (text_w, text_h), baseline = cv2.getTextSize(text, font, font_scale, thickness)
        y_pos = y + i * (text_h + line_spacing)
        
        # Define mask for background rectangle region
        top_left = (x - 5, y_pos - text_h - baseline - 5)
        bottom_right = (x + text_w + 5, y_pos + baseline + 5)
        
        # Create mask of zeros with same shape as image, single channel
        mask = np.zeros(img.shape[:2], dtype=bool)
        mask[top_left[1]:bottom_right[1], top_left[0]:bottom_right[0]] = True
        
        # Apply semi-transparent background using your opacity_overlay function
        img = opacity_overlay(img, mask, color=bg_colors[i], opacity=bg_opacity)
        
        # Draw the text on top
        cv2.putText(img, text, (x, y_pos), font, font_scale, text_color, thickness, cv2.LINE_AA)
        
    return img
def find_horizon(image):
    def get_horizon_line(img, min_line_length):
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=16, minLineLength=min_line_length, maxLineGap=15)
        best_line = None
        max_length = 0
        horizon_y = None
        if lines is not None:
            for line in lines:
                x1, y1, x2, y2 = line[0]
                dy = abs(y2 - y1)
                dx = abs(x2 - x1)
                length = np.hypot(dx, dy)
                if dy < 5 and length > max_length and min(y1, y2) > img.shape[0] * 0.15 and max(y1, y2) < img.shape[0] * 0.85:
                    max_length = length
                    best_line = (x1, y1, x2, y2)
            if best_line:
                horizon_y = int((best_line[1] + best_line[3]) / 2)
                cv2.line(img, (0, horizon_y), (img.shape[1], horizon_y), (0,255,0), 2)
        return img, horizon_y

    min_line_length = 500
    result_img, horizon_y = get_horizon_line(image, min_line_length)
    while horizon_y is None and min_line_length > 250:
        min_line_length -= 50
        result_img, horizon_y = get_horizon_line(image, min_line_length)
    return result_img, horizon_y

def calculate_saturation_weighted_score(mask, s, total_pixels, power=2.0, bin_size=32):
    """
    Calculate score based on saturation
    """
   
    if np.count_nonzero(mask) == 0:
        return 0.0
    
    avg_saturation = s[mask].mean()
    #print(f"Average Saturation: {avg_saturation}")
    pixel_ratio = np.count_nonzero(mask) / total_pixels
    
    # Apply non-linear weighting: higher saturation values are amplified exponentially
    score = (pixel_ratio * (avg_saturation ** power)) / CONFIG["divisor"]
    return score


    # yellow_mask = (h >= 25) & (h <= 35) & (s >= 15)
    # yellow_count = np.count_nonzero(yellow_mask)
    # if yellow_count == 0:
    #     yellow_score = 0.0
    # else:
    #     yellow_pixel_ratio = yellow_count / total_pixels
    #     yellow_avg_saturation = s[yellow_mask].mean()
    #     yellow_score = yellow_pixel_ratio * yellow_avg_saturation
    # print(f"Yellow Score: {yellow_score}")  



# %%
