import cv2
import numpy as np
from PIL import Image
import streamlit as st
import os

def apply_hsv_mask(img, h_min, h_max, s_min, s_max, v_min, v_max):
    """Apply HSV mask to an image and return the result."""
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    lower = np.array([h_min, s_min, v_min])
    upper = np.array([h_max, s_max, v_max])
    mask = cv2.inRange(hsv, lower, upper)
    result = cv2.bitwise_and(img, img, mask=mask)
    return result

def show_page():
    st.title("HSV Mask Tuner for Sunset Analysis")

    # HSV sliders - show these first
    st.subheader("HSV Range Controls")
    col_h1, col_h2 = st.columns(2)
    with col_h1:
        h_min = st.slider("Hue Min", 0, 179, 0)
    with col_h2:
        h_max = st.slider("Hue Max", 0, 179, 179)
    
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        s_min = st.slider("Sat Min", 0, 255, 0)
    with col_s2:
        s_max = st.slider("Sat Max", 0, 255, 255)
    
    col_v1, col_v2 = st.columns(2)
    with col_v1:
        v_min = st.slider("Val Min", 0, 255, 0)
    with col_v2:
        v_max = st.slider("Val Max", 0, 255, 255)

    st.divider()
    
    # Display fixed images with mask applied
    st.subheader("Fixed Reference Images")
    col1, col2 = st.columns(2)
    
    with col1:
        if os.path.exists("stock_images/color_wheel.jpg"):
            img_cw = cv2.imread("stock_images/color_wheel.jpg")
            result_cw = apply_hsv_mask(img_cw, h_min, h_max, s_min, s_max, v_min, v_max)
            st.image(cv2.cvtColor(result_cw, cv2.COLOR_BGR2RGB), caption="Color Wheel (Masked)")
    
    with col2:
        if os.path.exists("stock_images/hsv_cone.jpg"):
            img_cone = cv2.imread("stock_images/hsv_cone.jpg")
            result_cone = apply_hsv_mask(img_cone, h_min, h_max, s_min, s_max, v_min, v_max)
            st.image(cv2.cvtColor(result_cone, cv2.COLOR_BGR2RGB), caption="HSV Cone (Masked)")

    st.divider()

    # Upload section
    st.subheader("Upload Your Own Image")
    uploaded = st.file_uploader("Upload an image", type=["jpg", "jpeg", "png"])

    if uploaded:
        file_bytes = np.asarray(bytearray(uploaded.read()), dtype=np.uint8)
        img = cv2.imdecode(file_bytes, 1)
        img = cv2.resize(img, (800, 600))
        
        result = apply_hsv_mask(img, h_min, h_max, s_min, s_max, v_min, v_max)
        st.image(cv2.cvtColor(result, cv2.COLOR_BGR2RGB), caption="Uploaded Image (Masked)")
