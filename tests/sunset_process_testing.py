# %%

import os
import sys
import glob
import cv2
import numpy as np
from matplotlib import pyplot as plt
import importlib

# Add the parent directory to path for imports
project_root = os.path.dirname(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import sunset_code.helpers.sunset_process
importlib.reload(sunset_code.helpers.sunset_process)

from sunset_code.helpers.sunset_process import rank_sunset
from sunset_code.helpers.sunset_process import put_text_with_opacity_bg


#LOWER
sunset_root1 = "/home/dlavoie/Pictures/sunset_images/btv_echo_cam/2025/12*/12-02-2025"
sunset_root = "/home/dlavoie/Pictures/sunset_images/btv_echo_cam/2025/12*/12-18-2025"

#HIGHER
sunset_root2 = "/home/dlavoie/Pictures/sunset_images/btv_echo_cam/2025/05*/05-16-2025"
#INclude #08 #09 #10

pattern = [
    # os.path.join(sunset_root, "**", "04*.jpg"),
    os.path.join(sunset_root, "**", "07*.jpg")
    # os.path.join(sunset_root, "**", "08*.jpg"),
    # os.path.join(sunset_root, "**", "09*.jpg"),
    # os.path.join(sunset_root, "**", "10*.jpg"),
]


# pattern = "/home/dlavoie/Documents/01_PYTHON/SERVICES/EXAMPLE_IMAGES/*.jpg"
for pattern in pattern:
    for img_path in glob.glob(pattern, recursive=True):

        score, final_txt_img, name, hist_h, hist_s, hist_v, combined_mask_full_image, texts, bg_colors = rank_sunset(img_path)
            
        final_txt_img = put_text_with_opacity_bg(combined_mask_full_image, texts, bg_colors)
        plt.imshow(cv2.cvtColor(final_txt_img, cv2.COLOR_BGR2RGB))
        plt.title(f"{name} \nScore: {score}/100")
        plt.axis('off')
        plt.show()

        #show hsv
        fig_hist, ax_hist = plt.subplots(figsize=(10,5))
        x_h = np.arange(180)
        x_sv = np.arange(256)

        ax_hist.fill_between(x_h, hist_h[:180].flatten(), color='r', alpha=0.4, label="Hue")
        ax_hist.fill_between(x_sv, hist_s.flatten(), color='g', alpha=0.3, label="Saturation")
        ax_hist.fill_between(x_sv, hist_v.flatten(), color='b', alpha=0.2, label="Value")

        ax_hist.plot(hist_h[:180], color='r', alpha=0.5)
        ax_hist.plot(hist_s, color='g', alpha=0.5)
        ax_hist.plot(hist_v, color='b', alpha=0.5)

        ax_hist.set_title(f"{name} — HSV Histograms", fontsize=14)
        ax_hist.set_xlabel("Value", fontsize=12)
        ax_hist.set_ylabel("Pixel Count", fontsize=12)
        ax_hist.set_xlim(0, 255)
        ax_hist.grid(alpha=0.7)
        ax_hist.legend()

        ax_hist.set_xticks(np.arange(0, 256, 25))
        plt.tight_layout(pad=0.1)
        plt.show()








# %%
