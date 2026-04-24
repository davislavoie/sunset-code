# %%
import cv2
import numpy as np
import os

def rank_sunset(frame):
    img = cv2.imread(frame)
    
    if img is None:
        print(f"Error: Could not load image '{frame}'")
        return None
    name = os.path.basename(frame).split('.')[0]

    #horizon_img, horizon_y = find_horizon(img)
    horizon_y = img.shape[0] // 2
    
    height, width = img.shape[:2]

    if horizon_y is not None:
        sky_image = img[:horizon_y, :]
        bot_image = img[horizon_y:, :]
        half_height = horizon_y  # For spread calculations
    else:
        half_height = height // 2 + 30
        sky_image = img[:half_height, :]
        bot_image = img[half_height:, :]

    hsv = cv2.cvtColor(sky_image, cv2.COLOR_BGR2HSV)
    h, s, v = hsv[:,:,0], hsv[:,:,1], hsv[:,:,2]
    hist_h = cv2.calcHist([h], [0], None, [180], [0,180])
    hist_s = cv2.calcHist([s], [0], None, [256], [0,256])
    hist_v = cv2.calcHist([v], [0], None, [256], [0,256])

    total_half_pixels = h.size
    total_pixels = img.shape[0] * img.shape[1]
    
    #RANKING METRICS
    #RED HUE 
    red_mask = (h < 8) & (s >= 20)
    red_score = calculate_saturation_weighted_score(red_mask, s, total_pixels, power=2.0)
    # print(f"Red Score: {red_score}")
     
    #ORANGE HUE
    orange_mask = (h >= 8) & (h < 25) & (s >= 20)
    orange_score = calculate_saturation_weighted_score(orange_mask, s, total_pixels, power=2.0)
    # print(f"Orange Score: {orange_score}")

    #PINK/PURPLE HUE
    pink_mask = (h >= 140) & (h <= 179) & (s >= 20)
    pink_score = calculate_saturation_weighted_score(pink_mask, s, total_pixels, power=2.0)
    # print(f"Pink Score: {pink_score}")
    
    #YELLOW HUE
    yellow_mask = (h >= 25) & (h <= 35) & (s >= 20)
    yellow_score = calculate_saturation_weighted_score(yellow_mask, s, total_pixels, power=2.0)
    # print(f"Yellow Score: {yellow_score}")  
    
    #METRICS
    # 1. Warm Color Ratio (orange/red/yellow)
    warm_pixels = (h >= 0) & (h < 25) & (s >= 70)
    warm_ratio = np.count_nonzero(warm_pixels) / total_pixels

    #2. Warm color low saturation
    warm_dull_pixels = (h >= 0) & (h < 25) & (s < 70) & (s >= 25)
    warm_dull_ratio = np.count_nonzero(warm_dull_pixels) / total_pixels 

    # 3. Pink/Purple Ratio (Hue 160-179)
    pink_pixels = (h >= 135) & (h <= 179) & (s >= 60)  
    pink_ratio = np.count_nonzero(pink_pixels) / total_pixels

    # 4. Pink/Purple low saturation
    pink_dull_pixels = (h >= 135) & (h <= 179) & (s < 60)  & (s >= 25)
    pink_dull_ratio = np.count_nonzero(pink_dull_pixels) / total_pixels

    # 5. Yellow glow
    yellow_pixels = (h >= 25) & (h <= 35)
    yellow_ratio = np.count_nonzero(yellow_pixels) / total_pixels

    #5. Dark Blue Ratio (Hue 100-120) Cloud contrast
    dark_blue_pixels = (h >= 100) & (h <= 120) & (s >= 60) & (v >= 125)
    dark_blue_ratio = np.count_nonzero(dark_blue_pixels) / total_pixels

    # Final Score Calculation
    # score = (
    #     250 * warm_ratio +
    #     100 * warm_dull_ratio +
    #     400 * pink_ratio +
    #     300 * pink_dull_ratio +
    #     150 * yellow_ratio 
    # ) 
    score = (
        red_score * 4 +
        orange_score * 3 +
        yellow_score * 2 +
        pink_score * 9
    )

    score = min(100.0, round(score, 2))  

    ##IMAGE VISUALIZATION
    # Warm and pink pixel overlays
    warm_mask = opacity_overlay(sky_image, warm_pixels, color=(0, 0, 255), opacity=0.3)
    warm_dull_mask = opacity_overlay(warm_mask, warm_dull_pixels, color=(0, 165, 255), opacity=0.3)
    pink_dull_mask = opacity_overlay(warm_dull_mask, pink_dull_pixels, color=(150, 130, 220) , opacity=0.3)
    yellow_mask = opacity_overlay(pink_dull_mask, yellow_pixels, color=(0, 255, 255), opacity=0.3)
    dark_blue_mask = opacity_overlay(yellow_mask, dark_blue_pixels, color=(255, 0, 0), opacity=0.3)
    combined_mask = opacity_overlay(dark_blue_mask, pink_pixels, color=(255, 0, 255), opacity=0.3)
    combined_mask_full_image = np.vstack((combined_mask, bot_image))

    #Add image text
    texts = [
        f"Warm Color Ratio: {warm_ratio:.2%}",
        f"Warm Dull Ratio: {warm_dull_ratio:.2%}",
        f"Pink Color Ratio: {pink_ratio:.2%}",
        f"Pink Dull Ratio: {pink_dull_ratio:.2%}",
        f"Yellow Ratio: {yellow_ratio:.2%}",
        f"Dark Blue Ratio: {dark_blue_ratio:.2%}",

    ]

    bg_colors = [
        (0, 0, 255),  
        (0, 100, 255),  
        (255, 0, 255),   
        (150, 130, 220),
        (0, 255, 255),
        (255, 0, 0),
        (0, 0, 0), 
        (0, 0, 0),  
        (0, 0, 0)  
    ]

    final_txt_img = put_text_with_opacity_bg(combined_mask_full_image, texts, bg_colors)
    
    #Return Images and Data
    return score, final_txt_img, name, hist_h, hist_s, hist_v, combined_mask_full_image, texts, bg_colors

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
    score = (pixel_ratio * (avg_saturation ** power))/40
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
