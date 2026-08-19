import cv2
import numpy as np
from PIL import Image
import streamlit as st
import os
import requests
from io import BytesIO

def apply_hsv_mask(img, h_min, h_max, s_min, s_max, v_min, v_max):
    """Apply HSV mask to an image and return the result."""
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    lower = np.array([h_min, s_min, v_min])
    upper = np.array([h_max, s_max, v_max])
    mask = cv2.inRange(hsv, lower, upper)
    result = cv2.bitwise_and(img, img, mask=mask)
    return result

def load_image_from_url(url):
    """Load an image from a URL and convert to OpenCV format."""
    try:
        response = requests.get(url)
        img = Image.open(BytesIO(response.content))
        img_array = np.array(img)
        # Convert RGB to BGR for OpenCV
        img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        return img_bgr
    except Exception as e:
        st.error(f"Error loading image: {e}")
        return None

def show_page(sunset_data=None, all_data=None):
    st.title("HSV Mask Tuner for Sunset Analysis")

    # Create layout: sliders on left, reference images on right
    slider_col, ref_col = st.columns([2, 1])
    
    with slider_col:
        st.subheader("HSV Range Controls")
        col_h1, col_h2 = st.columns(2)
        with col_h1:
            h_min = st.slider("Hue Min", 0, 179, 0)
        with col_h2:
            h_max = st.slider("Hue Max", 0, 179, 179)
        
        st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)
        
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            s_min = st.slider("Sat Min", 0, 255, 0)
        with col_s2:
            s_max = st.slider("Sat Max", 0, 255, 255)
        
        st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)
        
        col_v1, col_v2 = st.columns(2)
        with col_v1:
            v_min = st.slider("Val Min", 0, 255, 0)
        with col_v2:
            v_max = st.slider("Val Max", 0, 255, 255)
    
    with ref_col:
        st.subheader("Fixed Reference Images")
        ref_img_col1, ref_img_col2 = st.columns(2)
        
        with ref_img_col1:
            if os.path.exists("stock_images/color_wheel.jpg"):
                img_cw = cv2.imread("stock_images/color_wheel.jpg")
                result_cw = apply_hsv_mask(img_cw, h_min, h_max, s_min, s_max, v_min, v_max)
                st.image(cv2.cvtColor(result_cw, cv2.COLOR_BGR2RGB), caption="Color Wheel", width=180)
        
        with ref_img_col2:
            if os.path.exists("stock_images/hsv_cone.jpg"):
                img_cone = cv2.imread("stock_images/hsv_cone.jpg")
                result_cone = apply_hsv_mask(img_cone, h_min, h_max, s_min, s_max, v_min, v_max)
                st.image(cv2.cvtColor(result_cone, cv2.COLOR_BGR2RGB), caption="HSV Cone", width=180)

    st.divider()
    
    # Gallery Image Selection
    if all_data and len(all_data) > 0:
        st.subheader("Load Image from Gallery")
        
        # Initialize session state for gallery image
        if "gallery_image_url" not in st.session_state:
            st.session_state.gallery_image_url = None
        if "gallery_image_data" not in st.session_state:
            st.session_state.gallery_image_data = None
        
        col_search1, col_search2, col_search3 = st.columns([2, 1, 1])
        with col_search1:
            # Create a list of image options with date and time
            image_options = []
            for idx, item in enumerate(all_data):
                label = item.get("Label", "")
                # Clean up the label for display
                display_label = label[3:] if label.startswith(("07_", "11_", "12_")) else label
                option_text = f"{item['Date']} {item['Time']} - {display_label} (Score: {item['Score']:.1f}%)"
                image_options.append(option_text)
            
            selected_option = st.selectbox(
                "Select an image from the gallery:",
                options=["None"] + image_options,
                key="gallery_selector"
            )
        
        with col_search2:
            st.markdown("<div style='margin-top: 32px;'></div>", unsafe_allow_html=True)
            if st.button("Load Image", use_container_width=True, disabled=(selected_option == "None")):
                if selected_option != "None":
                    # Find the index of the selected image
                    selected_idx = image_options.index(selected_option)
                    st.session_state.gallery_image_url = all_data[selected_idx]["Image"]
                    st.session_state.gallery_image_data = None  # Reset to force reload
                    st.rerun()
        
        with col_search3:
            st.markdown("<div style='margin-top: 32px;'></div>", unsafe_allow_html=True)
            if st.button("Clear", use_container_width=True, disabled=(st.session_state.gallery_image_url is None)):
                st.session_state.gallery_image_url = None
                st.session_state.gallery_image_data = None
                st.rerun()
        
        # Load and cache the gallery image
        if st.session_state.gallery_image_url and st.session_state.gallery_image_data is None:
            with st.spinner("Loading image from gallery..."):
                st.session_state.gallery_image_data = load_image_from_url(st.session_state.gallery_image_url)

    st.divider()
    
    # Display gallery image if loaded
    if st.session_state.get("gallery_image_data") is not None:
        st.subheader("Gallery Image")
        gallery_img = st.session_state.gallery_image_data
        # Resize if needed for display
        max_width = 800
        if gallery_img.shape[1] > max_width:
            aspect_ratio = gallery_img.shape[0] / gallery_img.shape[1]
            new_height = int(max_width * aspect_ratio)
            gallery_img = cv2.resize(gallery_img, (max_width, new_height))
        
        result_gallery = apply_hsv_mask(gallery_img, h_min, h_max, s_min, s_max, v_min, v_max)
        
        # Show original and masked side by side
        col_orig, col_mask = st.columns(2)
        with col_orig:
            st.image(cv2.cvtColor(gallery_img, cv2.COLOR_BGR2RGB), caption="Gallery Image (Original)")
        with col_mask:
            st.image(cv2.cvtColor(result_gallery, cv2.COLOR_BGR2RGB), caption="Gallery Image (Masked)")
    

    # Upload section
    st.subheader("Upload Your Own Image")
    uploaded = st.file_uploader("Upload an image", type=["jpg", "jpeg", "png"])

    if uploaded:
        file_bytes = np.asarray(bytearray(uploaded.read()), dtype=np.uint8)
        img = cv2.imdecode(file_bytes, 1)
        
        # Resize if needed
        max_width = 800
        if img.shape[1] > max_width:
            aspect_ratio = img.shape[0] / img.shape[1]
            new_height = int(max_width * aspect_ratio)
            img = cv2.resize(img, (max_width, new_height))
        
        result = apply_hsv_mask(img, h_min, h_max, s_min, s_max, v_min, v_max)
        
        # Show original and masked side by side
        col_orig, col_mask = st.columns(2)
        with col_orig:
            st.image(cv2.cvtColor(img, cv2.COLOR_BGR2RGB), caption="Uploaded Image (Original)")
        with col_mask:
            st.image(cv2.cvtColor(result, cv2.COLOR_BGR2RGB), caption="Uploaded Image (Masked)")
