from yt_dlp import YoutubeDL
import os
import cv2
from datetime import date


def get_photo(photo_interval, youtube_url, influx_tag):
    
    """ Grab image from youtube livestream, save and return  """

    ydl_opts = {'format': 'best'}

    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(youtube_url, download=False)
        video_url = info['url']

    cap = cv2.VideoCapture(video_url)
    success, frame = cap.read()

    if success:
        filename = photo_interval + "_" + date.today().strftime("%m-%d-%Y") + ".jpg"
        frame, photo_filepath = image_push(frame, filename, influx_tag)
        cap.release()
        return frame, photo_filepath

    else:
        print("Failed to grab frame.")
        cap.release()  
        return None, None


def image_push(frame, filename, influx_tag):

    year = date.today().strftime('%Y')
    month = date.today().strftime("%m") + "-" + date.today().strftime("%B")
    day =  date.today().strftime("%m-%d-%Y")

    pictures_dir = os.environ.get("PICTURES_DIR", os.path.expanduser("~/Pictures"))
    photo_dir = os.path.join(pictures_dir, "sunset_images", influx_tag, year, month, day)
    os.makedirs(photo_dir, exist_ok=True)

    photo_filepath = os.path.join(photo_dir, filename)    
    cv2.imwrite(photo_filepath, frame)

    print(f"Frame save to {photo_filepath}")
    return frame, photo_filepath
