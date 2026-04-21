import streamlit as st
from influxdb import InfluxDBClient
from datetime import datetime
from urllib.parse import quote, unquote

def show_page(sunset_data, all_data):

    # Render gallery
    st.markdown("### All Sunset Images")

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
                    <div class="caption">Time: {value['Time']} | Score: {value['Score']}%</div>
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
                        <div class="caption">Time: {sub_value['Time']} | Score: {sub_value['Score']}%</div>
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