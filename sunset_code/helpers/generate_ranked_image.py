import os
import cv2
import numpy as np
from matplotlib import pyplot as plt

def generate_ranked_image(final_txt_img, score, name, hist_h, hist_s, hist_v, photo_dir):

    '''Generates and saves the ranked image and its histograms.

    Both are saved at the photo's exact size (e.g. 1920x1080) so they line up
    with the original in the dashboard. Matplotlib's bbox_inches="tight" used
    to recrop them (1760x1115 and 2780x1406), so it is no longer used.'''

    clean_name = name[3:]
    height, width = final_txt_img.shape[:2]

    # Ranked image: draw the score and name onto the annotated photo itself
    # (instead of a matplotlib title above it), keeping its exact dimensions.
    ranked = draw_title_bar(final_txt_img, f"Score: {score}/100", name)
    score_image_path = os.path.join(photo_dir, f"11_ranked_{clean_name}.png")
    cv2.imwrite(score_image_path, ranked)

    # Histograms: a figure of exactly width x height pixels (figsize * dpi),
    # saved at the same dpi without tight cropping.
    dpi = 100
    fig_hist, ax_hist = plt.subplots(figsize=(width / dpi, height / dpi), dpi=dpi)
    x_h = np.arange(180)
    x_sv = np.arange(256)

    ax_hist.fill_between(x_h, hist_h[:180].flatten(), color='r', alpha=0.4, label="Hue")
    ax_hist.fill_between(x_sv, hist_s.flatten(), color='g', alpha=0.3, label="Saturation")
    ax_hist.fill_between(x_sv, hist_v.flatten(), color='b', alpha=0.2, label="Value")

    ax_hist.plot(hist_h[:180], color='r', alpha=0.5)
    ax_hist.plot(hist_s, color='g', alpha=0.5)
    ax_hist.plot(hist_v, color='b', alpha=0.5)

    # Font sizes scale with the image so labels stay readable at any resolution.
    scale = width / 1920
    ax_hist.set_title(f"{name} — HSV Histograms", fontsize=28 * scale)
    ax_hist.set_xlabel("Value", fontsize=22 * scale)
    ax_hist.set_ylabel("Pixel Count", fontsize=22 * scale)
    ax_hist.tick_params(labelsize=16 * scale)
    ax_hist.set_xlim(0, 255)
    ax_hist.grid(alpha=0.7)
    ax_hist.legend(fontsize=18 * scale)

    ax_hist.set_xticks(np.arange(0, 256, 25))
    fig_hist.tight_layout(pad=1.0)  # rearranges inside the figure; doesn't change its size

    histogram_path = os.path.join(photo_dir, f"12_histogram_{clean_name}.png")
    fig_hist.savefig(histogram_path, dpi=dpi)
    plt.close(fig_hist)

    return histogram_path, score_image_path


def draw_title_bar(image, title, subtitle):
    '''Returns a copy of image with a translucent bar along the bottom holding the
    title (large) and subtitle (smaller). Same size as the input.'''
    img = image.copy()
    height, width = img.shape[:2]
    scale = width / 1920
    font = cv2.FONT_HERSHEY_DUPLEX
    title_scale, sub_scale = 1.6 * scale, 0.9 * scale
    title_thick, sub_thick = max(1, round(3 * scale)), max(1, round(2 * scale))
    pad = round(18 * scale)

    (_, title_h), _ = cv2.getTextSize(title, font, title_scale, title_thick)
    (_, sub_h), sub_base = cv2.getTextSize(subtitle, font, sub_scale, sub_thick)
    bar_h = pad * 3 + title_h + sub_h + sub_base

    # Darken the bottom strip so white text reads on any sky
    bar = img[height - bar_h:, :]
    img[height - bar_h:, :] = (bar * 0.45).astype(img.dtype)

    title_y = height - bar_h + pad + title_h
    sub_y = title_y + pad + sub_h
    cv2.putText(img, title, (pad, title_y), font, title_scale, (255, 255, 255), title_thick, cv2.LINE_AA)
    cv2.putText(img, subtitle, (pad, sub_y), font, sub_scale, (210, 210, 210), sub_thick, cv2.LINE_AA)
    return img
