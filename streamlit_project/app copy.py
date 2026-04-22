import streamlit as st
from influxdb import InfluxDBClient
from datetime import datetime
from urllib.parse import quote, unquote
import pytz
import cv2
import numpy as np
from PIL import Image
import os
import glob

#http://100.107.153.41:8501/

# Setup timezone and layout
local_tz = pytz.timezone("America/New_York")
st.set_page_config(layout="wide")

sunset_root = "/home/dlavoie/Pictures/sunset_images/btv_echo_cam"
all_files = glob.glob(os.path.join(sunset_root, "**", "*.jpg"), recursive=True)

all_data = []
sunset_data = []

for img_path in all_files:
    # Extract info from filename and path
    filename = os.path.basename(img_path)
    directory = os.path.dirname(img_path)
    
    # Parse filename (e.g., "07_sunset_05-16-2025.jpg")
    parts = filename.replace('.jpg', '').split('_')
    if len(parts) >= 3:
        time_slot = parts[0]  # "06", "07", "08", "09"
        label_type = parts[1]  # "sunset", "15m_post", etc.
        date_part = parts[2]  # "05-16-2025"
        
        try:
            # Convert date format
            date_obj = datetime.strptime(date_part, "%m-%d-%Y")
            date_str = date_obj.strftime("%Y-%m-%d")
            
            # Map time slots to display times
            time_mapping = {
                "06": "06:00 AM", "07": "07:00 AM", 
                "08": "08:00 AM", "09": "09:00 AM"
            }
            time_str = time_mapping.get(time_slot, f"{time_slot}:00 AM")
            
            entry = {
                "Date": date_str,
                "Time": time_str,
                "Label": f"{time_slot}_{label_type}",
                "Image": img_path,
                "Score": 0,
                "Cloud Cover": "Working on it"
            }
            
            all_data.append(entry)
            
            # Add to sunset_data if it's a sunset image
            if label_type == "sunset":
                sunset_data.append(entry)
                
        except ValueError:
            # Skip files that don't match expected format
            continue
    
    
    
    
    
    if point.get("label") == "07_sunset":
        dt_utc = datetime.strptime(point["time"], "%Y-%m-%dT%H:%M:%SZ")
        dt_local = dt_utc.replace(tzinfo=pytz.utc).astimezone(local_tz)
        date_str = dt_local.strftime("%Y-%m-%d")
        time_str = dt_local.strftime("%I:%M %p")

        sunset_data.append({
            "Date": date_str,
            "Time": time_str,
            "Label": point["label"],
            "Image": point["url"],
            "Score": 0,
            "Cloud Cover": "Working on it"
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
        "Score": 0,
        "Cloud Cover": "Working on it"
    })

# Render gallery
st.markdown("### Sunset Images")

tab1, tab2 = st.tabs(["Sunset Gallery", "Zoomed Images"])


columns_num = 7
cols = st.columns(columns_num)

# Display sunset images in a grid in tab1
with tab1:
    for key, value in enumerate(sunset_data):
        with cols[key % columns_num]:
            img_encoded = quote(value["Image"])
            date_encoded = quote(value["Date"])
            label_encoded = quote(value["Label"][3:])

            st.markdown(f"""
            <div class="zoom-container">
                <div class="caption-top">{value['Date']}</div>
                <a href="?img={img_encoded}&date={date_encoded}&label={label_encoded}" target="_self">
                    <img src="{value['Image']}" style="width: 100%; border-radius: 6px; cursor: pointer;" />
                </a>
                <div class="caption">Time: {value['Time']} | Score: {value['Score']}% | Clouds: {value['Cloud Cover']}</div>
            </div>
            """, unsafe_allow_html=True)

with tab2:
    # FULL IMAGE DISPLAY
    img_param = st.query_params.get("img", None)
    date_str = st.query_params.get("date", None)
    label = st.query_params.get("label", None)

    if img_param:
        expanded_url = unquote(img_param)

        st.markdown('<a name="full"></a>', unsafe_allow_html=True)  # Scroll anchor
        st.markdown("---")
        st.markdown(f"### {label} from {date_str}")

        if st.button("Hide Full Image"):
            st.query_params.clear()
            st.rerun()

        st.markdown(f"""
        <div style="text-align: center;">
            <img src="{expanded_url}" style="width: 70%; border-radius: 8px;" />
        </div>
        """, unsafe_allow_html=True)

        # SUB IMAGE DISPLAY
        st.markdown("---")
        st.markdown("### Pre/Post Sunset")

    sub_cols = 5
    sub_image_col = st.columns(sub_cols)
    col_index = 0

    for sub_value in all_data:
        if sub_value["Date"] == date_str:
            with sub_image_col[col_index % sub_cols]:
                sub_img_encoded = quote(sub_value["Image"])
                sub_label_encoded = quote(sub_value["Label"][3:])

                label = st.query_params.get("label", None)

                highlight_style = "border-radius: 6px;" 
                if sub_value["Image"] == expanded_url:
                    highlight_style = "box-shadow: 0 0 0 4px #f39c12; border-radius: 6px;"  # highlight

                st.markdown(f"""
                <div class="zoom-container">
                    <div class="caption-top">{sub_value['Label'][3:]}</div>
                    <a href="?img={sub_img_encoded}&date={date_str}&label={sub_label_encoded}" target="_self">
                        <img src="{sub_value['Image']}" style="width: 100%; cursor: pointer; {highlight_style}" />
                    </a>
                    <div class="caption">Time: {sub_value['Time']}</div>
                </div>
                """, unsafe_allow_html=True)
            col_index += 1



        # Clean the URL hash after scroll
        st.markdown("""
        <script>
        setTimeout(() => {
            history.replaceState(null, "", window.location.pathname + window.location.search);
        }, 500);
        </script>
        """, unsafe_allow_html=True)


st.markdown("""
<style>
.zoom-container {
    overflow: visible;
    margin-bottom: 16px;
    text-align: center;
}

.zoom-container img {
    transition: transform 0.3s ease;
    display: block;
    margin: 0 auto;
    max-width: 100%;
    height: auto;
}

.zoom-container:hover img {
    transform: scale(1.03);
}

.caption-top {
    font-size: 1em;
    font-weight: bold;
    color: #333;
    margin-bottom: 6px;
    text-align: left;
    padding-left: 10px;     
    color: white;
}

.caption {
    margin-top: 8px;
    font-size: 0.9em;
    color: #555;
    text-align: center;
}
</style>
""", unsafe_allow_html=True)



st.title("HSV Mask Tuner for Sunset Analysis")

uploaded = st.file_uploader("Upload an image", type=["jpg", "jpeg", "png"])

if uploaded:
    file_bytes = np.asarray(bytearray(uploaded.read()), dtype=np.uint8)
    img = cv2.imdecode(file_bytes, 1)
    img = cv2.resize(img, (800, 600))
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    # HSV sliders
    h_min = st.slider("Hue Min", 0, 179, 0)
    h_max = st.slider("Hue Max", 0, 179, 179)
    s_min = st.slider("Sat Min", 0, 255, 0)
    s_max = st.slider("Sat Max", 0, 255, 255)
    v_min = st.slider("Val Min", 0, 255, 0)
    v_max = st.slider("Val Max", 0, 255, 255)

    lower = np.array([h_min, s_min, v_min])
    upper = np.array([h_max, s_max, v_max])
    mask = cv2.inRange(hsv, lower, upper)
    result = cv2.bitwise_and(img, img, mask=mask)

    #esult
    st.image(cv2.cvtColor(result, cv2.COLOR_BGR2RGB), caption="Masked Result")
