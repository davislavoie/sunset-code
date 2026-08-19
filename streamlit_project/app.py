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

# Connect to InfluxDB
client = InfluxDBClient(host="100.107.153.41", port=8086, database="sunset_images")
local_tz = pytz.timezone("America/New_York")

# Cache the data query to avoid re-fetching on every interaction
@st.cache_data(ttl=300)  # Cache for 5 minutes
def fetch_camera_data(camera_tag):
    """Fetch and process all data for a camera"""
    results = client.query(f"SELECT * FROM sunset_images WHERE camera = '{camera_tag}'")
    
    sunset_data = []
    all_data = []
    ranked_images = []
    
    points_list = list(results.get_points())
    
    for point in points_list:
        dt_utc = datetime.strptime(point["time"], "%Y-%m-%dT%H:%M:%SZ")
        dt_local = dt_utc.replace(tzinfo=pytz.utc).astimezone(local_tz)
        date_str = dt_local.strftime("%Y-%m-%d")
        time_str = dt_local.strftime("%I:%M %p")
        
        data_item = {
            "Date": date_str,
            "Time": time_str,
            "Label": point["label"],
            "Image": point["url"],
            "Score": 0 if point['score'] is None else point['score'],
        }
        
        all_data.append(data_item)
        
        if point.get("label", "").startswith("07_"):
            sunset_data.append(data_item)
        
        if point.get("label", "").startswith("11_"):
            epoch_time = point["time"]
            matching_photo = [p for p in points_list if p["time"] == epoch_time and not p.get("label", "").startswith(("11_", "12_"))]
            matching_photo_url = matching_photo[0]["url"] if matching_photo else None
            hsv_photo = [p for p in points_list if p["time"] == epoch_time and p.get("label", "").startswith("12_")]
            
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
    
    return sunset_data, all_data, ranked_images

# Query available camera tags
camera_query = client.query("SHOW TAG VALUES FROM sunset_images WITH KEY = camera")
camera_tags = [point["value"] for point in camera_query.get_points()]

# Default camera if none found
if not camera_tags:
    camera_tags = ["btv_echo_cam"]

# Sidebar navigation
with st.sidebar:
    st.title("Navigation")
    
    # Camera selection dropdown
    st.subheader("Camera Selection")
    selected_camera = st.selectbox(
        "Select Camera:",
        options=camera_tags,
        index=0,
        key="camera_selector"
    )
    
    st.divider()
    
    if st.button("Sunset Calander", use_container_width=True):
        st.session_state.page = "Sunset Calander"
    if st.button("Ranked Images", use_container_width=True):
        st.session_state.page = "Ranked Images"
    if st.button("Score Tracker", use_container_width=True):
        st.session_state.page = "Score Tracker" 
    if st.button("HSV Tuner", use_container_width=True):
        st.session_state.page = "HSV Tuner"
    
    page = st.session_state.get("page", "Sunset Calander")

# Fetch cached data
sunset_data, all_data, ranked_images = fetch_camera_data(selected_camera)

# Route to the appropriate page
if page == "Sunset Calander":
    sunset_gallery.show_page(sunset_data, all_data)
elif page == "Ranked Images":
    ranking_tab.show_page(sunset_data, all_data, ranked_images)
elif page == "Score Tracker":
    score_tracker.show_page(sunset_data, all_data, ranked_images)
elif page == "HSV Tuner":
    hsv_tuner.show_page(sunset_data, all_data)




