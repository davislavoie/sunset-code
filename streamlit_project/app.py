import streamlit as st
from influxdb import InfluxDBClient
from datetime import datetime
from urllib.parse import quote, unquote
import pytz
import numpy as np
from PIL import Image

#Page modules
import sunset_gallery
import ranking_tab
import hsv_tuner
import score_tracker

#http://100.107.153.41:8501/

# Setup timezone and layout

st.set_page_config(layout="wide")

# Sidebar navigation
with st.sidebar:
    st.title("Navigation")
    
    if st.button("Sunset Calander", use_container_width=True):
        st.session_state.page = "Sunset Calander"
    if st.button("Ranked Images", use_container_width=True):
        st.session_state.page = "Ranked Images"
    if st.button("Score Tracker", use_container_width=True):
        st.session_state.page = "Score Tracker" 
    if st.button("HSV Tuner", use_container_width=True):
        st.session_state.page = "HSV Tuner"
    
    page = st.session_state.get("page", "Sunset Calander")

# Connect to InfluxDB
client = InfluxDBClient(host="100.107.153.41", port=8086, database="sunset_images")
results = client.query("SELECT * FROM sunset_images")
local_tz = pytz.timezone("America/New_York")


#Sunset Data
sunset_data = []
for point in results.get_points():
    if point.get("label", "").startswith("07_"):
        dt_utc = datetime.strptime(point["time"], "%Y-%m-%dT%H:%M:%SZ")
        dt_local = dt_utc.replace(tzinfo=pytz.utc).astimezone(local_tz)
        date_str = dt_local.strftime("%Y-%m-%d")
        time_str = dt_local.strftime("%I:%M %p")

        sunset_data.append({
            "Date": date_str,
            "Time": time_str,
            "Label": point["label"],
            "Image": point["url"],
            "Score": 0 if point['score'] is None else point['score'],

            "temperature_2m": point["temperature_2m"],
            "relative_humidity_2m": point["relative_humidity_2m"],
            "dew_point_2m": point["dew_point_2m"],
            "precipitation_probability": point["precipitation_probability"],
            "precipitation": point["precipitation"],
            "rain": point["rain"],
            "showers": point["showers"],
            "snowfall": point["snowfall"],
            "cloud_cover_low": 1, #point["cloud_cover_low"],
            "cloud_cover_mid": point["cloud_cover_mid"],
            "cloud_cover_high": point["cloud_cover_high"],
            "cloud_cover_total": point["cloud_cover_total"],
            "visibility": point["visibility"],   
        })

all_data = []
for point in results.get_points():
    dt_utc = datetime.strptime(point["time"], "%Y-%m-%dT%H:%M:%SZ")
    dt_local = dt_utc.replace(tzinfo=pytz.utc).astimezone(local_tz)
    date_str = dt_local.strftime("%Y-%m-%d")
    time_str = dt_local.strftime("%I:%M %p")

    all_data.append({
        "Date": date_str,
        "Time": time_str,
        "Label": point["label"],
        "Image": point["url"],
        "Score": 0 if point['score'] is None else point['score'],

        "temperature_2m": point["temperature_2m"],
        "relative_humidity_2m": point["relative_humidity_2m"],
        "dew_point_2m": point["dew_point_2m"],
        "precipitation_probability": point["precipitation_probability"],
        "precipitation": point["precipitation"],
        "rain": point["rain"],
        "showers": point["showers"],
        "snowfall": point["snowfall"],
        "cloud_cover_low": 1, #point["cloud_cover_low"],
        "cloud_cover_mid": point["cloud_cover_mid"],
        "cloud_cover_high": point["cloud_cover_high"],
        "cloud_cover_total": point["cloud_cover_total"],
        "visibility": point["visibility"],   
    })
        
ranked_images =[]
for point in results.get_points():
    if point.get("label", "").startswith("11_"):
        dt_utc = datetime.strptime(point["time"], "%Y-%m-%dT%H:%M:%SZ")
        dt_local = dt_utc.replace(tzinfo=pytz.utc).astimezone(local_tz)
        date_str = dt_local.strftime("%Y-%m-%d")
        time_str = dt_local.strftime("%I:%M %p")
        
        #Find matching photo at same time

        epoch_time = point["time"]
        matching_photo = [p for p in results.get_points() if p["time"] == epoch_time and not p.get("label", "").startswith(("11_", "12_"))]
        matching_photo_url = matching_photo[0]["url"] if matching_photo else None

        #Get matching HSV photo
        hsv_photo = [p for p in results.get_points() if p["time"] == epoch_time and p.get("label", "").startswith("12_")]

        ranked_images.append({
            "Ranked Image": f"{point['url']}",
            "Raw Image": matching_photo_url,
            "HSV Image": hsv_photo[0]["url"] if hsv_photo else None,
            "Score": 0 if point['score'] is None else point['score'],
            "Date": date_str,
            "Time": time_str,
            "dt_local": dt_local,
            "Label": point["label"],
            
        })


# Route to the appropriate page
if page == "Sunset Calander":
    sunset_gallery.show_page(sunset_data, all_data)
elif page == "Ranked Images":
    ranking_tab.show_page(sunset_data, all_data, ranked_images)
elif page == "Score Tracker":
    score_tracker.show_page(sunset_data, all_data, ranked_images)
elif page == "HSV Tuner":
    hsv_tuner.show_page()




