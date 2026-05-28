import streamlit as st

def show_page(sunset_data, all_data):

    # Render gallery
    st.markdown("### All Sunset Images")

    # Initialize session state
    if "selected_date" not in st.session_state:
        st.session_state.selected_date = None
    if "selected_index" not in st.session_state:
        st.session_state.selected_index = 0

    columns_num = 7

    # Group sunset_data into rows
    rows = []
    for i in range(0, len(sunset_data), columns_num):
        rows.append(sunset_data[i:i + columns_num])

    # Display each row, inserting expanded view inline when needed
    for row_idx, row in enumerate(rows):
        cols = st.columns(columns_num)
        row_has_selected = False
        
        for col_idx, value in enumerate(row):
            key = row_idx * columns_num + col_idx
            with cols[col_idx]:
                st.markdown(f'<div class="caption-top">{value["Date"]}</div>', unsafe_allow_html=True)
                st.image(value["Image"], use_container_width=True)
                st.markdown(f'<div class="caption">Time: {value["Time"]} | Score: {value["Score"]:.1f}%</div>', unsafe_allow_html=True)
                if st.button("View All", key=f"view_{key}", use_container_width=True):
                    st.session_state.selected_date = value["Date"]
                    st.session_state.selected_index = 0
                    st.rerun()
            
            if value["Date"] == st.session_state.selected_date:
                row_has_selected = True
        
        # Show expanded view inline right after this row if it contains the selected date
        if row_has_selected and st.session_state.selected_date:
            # Get all images for the selected date
            date_images = [img for img in all_data if img["Date"] == st.session_state.selected_date]
            
            # Separate regular images from ranked/histogram images
            regular_images = [img for img in date_images if 'ranked' not in img['Label'].lower() and 'histogram' not in img['Label'].lower()]
            special_images = [img for img in date_images if 'ranked' in img['Label'].lower() or 'histogram' in img['Label'].lower()]
            
            # Sort regular images by time, then append special images at the end
            regular_images = sorted(regular_images, key=lambda x: x["Time"])
            date_images = regular_images + special_images
            
            if date_images:
                # Ensure index is valid
                if st.session_state.selected_index >= len(date_images):
                    st.session_state.selected_index = 0
                
                current_img = date_images[st.session_state.selected_index]
                
                st.markdown("---")
                
                # Header with close button
                col1, col2 = st.columns([6, 1])
                with col1:
                    st.markdown(f"### {current_img['Label'][3:]} - {st.session_state.selected_date}")
                with col2:
                    if st.button("✕ Close", use_container_width=True):
                        st.session_state.selected_date = None
                        st.rerun()
                
                # Navigation and info
                nav_col1, nav_col2, nav_col3 = st.columns([1, 4, 1])
                with nav_col1:
                    if st.button("← Previous", use_container_width=True, disabled=(st.session_state.selected_index == 0)):
                        st.session_state.selected_index -= 1
                        st.rerun()
                with nav_col2:
                    st.markdown(f"<div style='text-align: center; color: #888;'>Image {st.session_state.selected_index + 1} of {len(date_images)} | Time: {current_img['Time']} | Score: {current_img['Score']:.1f}%</div>", unsafe_allow_html=True)
                with nav_col3:
                    if st.button("Next →", use_container_width=True, disabled=(st.session_state.selected_index >= len(date_images) - 1)):
                        st.session_state.selected_index += 1
                        st.rerun()
                
                # Main large image
                img_col1, img_col2, img_col3 = st.columns([1, 4, 1])
                with img_col2:
                    st.image(current_img["Image"], use_container_width=True)
                
                st.markdown("---")
                st.markdown("##### All images from this date:")
                
                # Thumbnail strip
                thumb_cols = st.columns(len(date_images) if len(date_images) <= 10 else 10)
                for idx, img in enumerate(date_images):
                    col_idx = idx % len(thumb_cols)
                    with thumb_cols[col_idx]:
                        is_selected = idx == st.session_state.selected_index
                        if st.button("", key=f"thumb_{idx}", use_container_width=True):
                            st.session_state.selected_index = idx
                            st.rerun()
                        
                        border_style = "border: 3px solid #f39c12;" if is_selected else "border: 2px solid transparent;"
                        st.markdown(f'''
                        <div style="text-align: center; {border_style} border-radius: 6px; padding: 2px; cursor: pointer;">
                            <img src="{img['Image']}" style="width: 100%; border-radius: 4px;" />
                            <div style="font-size: 0.7em; color: white; margin-top: 2px;">{img['Label'][3:]}</div>
                        </div>
                        ''', unsafe_allow_html=True)
                
                st.markdown("---")

    st.markdown("""
    <style>
    .caption-top {
        font-size: 1em;
        font-weight: bold;
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
    
    /* Smaller View All buttons */
    section[data-testid="stMain"] div[data-testid="column"] button[kind="secondary"] {
        font-size: 11px !important;
        padding: 2px 8px !important;
        min-height: 24px !important;
        height: 24px !important;
    }
    </style>
    """, unsafe_allow_html=True)