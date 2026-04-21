import os
import cv2
import numpy as np
from matplotlib import pyplot as plt

def generate_ranked_image(final_txt_img, score, name, hist_h, hist_s, hist_v, photo_dir):

    '''Generates and saves the ranked image and its histograms.'''

    clean_name = name[3:]

    # Display the image with a fixed size
    height, width = final_txt_img.shape[:2]
    dpi = 275  # or 96, or your monitor DPI
    figsize = (width / dpi, height / dpi)

    fig, ax = plt.subplots(figsize=figsize, dpi=dpi)
    ax.imshow(cv2.cvtColor(final_txt_img, cv2.COLOR_BGR2RGB))
    ax.set_title(f"Score: {score}/100 \n {name}")
    ax.axis('off')
    plt.tight_layout(pad=0)
    plt.show()

    # Save to output directory
    score_image_path = os.path.join(photo_dir, f"11_ranked_{clean_name}.png")
    fig.savefig(score_image_path, bbox_inches='tight', pad_inches=0.065, dpi=dpi)
    plt.close(fig)

    # Plot histograms
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

    # Save histogram to output directory
    histogram_path = os.path.join(photo_dir, f"12_histogram_{clean_name}.png")
    fig_hist.savefig(histogram_path, bbox_inches='tight', pad_inches=0.065, dpi=275)
    plt.close(fig_hist)

    return histogram_path, score_image_path