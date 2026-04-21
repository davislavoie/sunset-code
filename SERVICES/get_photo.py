from yt_dlp import YoutubeDL
import matplotlib.pyplot as plt
import os
import cv2
from datetime import date, timedelta, datetime, timezone


def get_photo(photo_interval):
    
    """ Grab image from youtube livestream, save and return  """

    url = "https://www.youtube.com/watch?v=JIE0vE51OKU"
    ydl_opts = {'format': 'best'}

    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        video_url = info['url']

    cap = cv2.VideoCapture(video_url)
    success, frame = cap.read()

    if success:
        filename = photo_interval + "_" + date.today().strftime("%m-%d-%Y") + ".jpg"
        frame, photo_file = image_push(frame, filename)
        cap.release()
        return frame, photo_file

    else:
        print("Failed to grab frame.")
        cap.release()  
        return None, None


def image_push(frame, filename):

    year = date.today().strftime('%Y')
    month = date.today().strftime("%m") + "-" + date.today().strftime("%B")
    day =  date.today().strftime("%m-%d-%Y")

    photo_dir = f"/home/dlavoie/Pictures/sunset_images/{year}/{month}/{day}"
    os.makedirs(photo_dir, exist_ok=True)

    photo_file = os.path.join(photo_dir, filename)    
    cv2.imwrite(photo_file, frame)

    print(f"Frame save to {photo_file}")
    return frame, photo_file
