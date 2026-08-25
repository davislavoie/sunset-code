from yt_dlp import YoutubeDL
import os
import cv2
from datetime import date


def get_video_url(stream_url):
    """
    Get the actual video stream URL.
    First tries yt-dlp (works for YouTube, Twitch, etc).
    If that fails, returns the URL directly (for HLS/RTSP/MJPEG streams).
    """
    # Try yt-dlp first
    try:
        ydl_opts = {'format': 'best', 'quiet': True, 'extractor_args': {'youtube': {'js_runtimes': ['node']}}}
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(stream_url, download=False)
            video_url = info['url']
            print(f"[INFO] yt-dlp extracted stream URL")
            return video_url
    except Exception as e:
        print(f"[INFO] yt-dlp failed ({e}), trying direct URL")

    # Fall back to direct URL (HLS .m3u8, RTSP, MJPEG, etc)
    return stream_url


def get_photo(photo_interval, stream_url, influx_tag):

    """ Grab image from video stream, save and return """

    video_url = get_video_url(stream_url)

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
