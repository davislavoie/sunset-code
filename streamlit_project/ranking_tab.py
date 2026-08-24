import streamlit as st
import pandas as pd
import re


def show_page(sunset_data, all_data, ranked_images):  
    #https://docs.streamlit.io/develop/api-reference/data) 

    st.title("Ranked Images")

    data = pd.DataFrame(ranked_images)
    data["Score"] = pd.to_numeric(data["Score"], errors='coerce')
    
    # Add sorting controls
    col1, col2 = st.columns([1, 1])
    with col1:
        sort_by = st.selectbox("Sort by:", ["Score", "Date", "Time"])
    
    with col2:
        sort_order = st.selectbox("Order:", ["Highest to Lowest", "Lowest to Highest"])
    
    # Apply sorting
    ascending = (sort_order == "Lowest to Highest")
    
    if sort_by == "Score":
        data = data.sort_values(by="Score", ascending=ascending)
    elif sort_by == "Date":
        data = data.sort_values(by="Date", ascending=ascending)
    elif sort_by == "Time":
        data = data.sort_values(by="Time", ascending=ascending)

    st.divider()

    # Create custom layout with columns
    for index, row in data.iterrows():
        col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 1, 2])

        with col1:
            st.image(row["Ranked Image"], width=300)

        with col2:
            if "Raw Image" in row and pd.notna(row["Raw Image"]):
                st.image(row["Raw Image"], width=300)
        
        with col3:
            if "HSV Image" in row and pd.notna(row["HSV Image"]):
                st.image(row["HSV Image"], width=300)
        
        
        with col4:
            st.metric("Score", f"{row['Score']:.2f}%")
        
                        # Weather data
            # Extract date from row label (format MM-DD-YYYY)
            match = re.search(r'(\d{2}-\d{2}-\d{4})', row['Label'])
            if match:
                row_date = match.group(1)
            else:
                row_date = None

            # Find the 07_sunset or 07_sunrise entry for that date
            matching = None
            if row_date:
                for item in sunset_data:
                    label = item.get('Label', '')
                    if (label.startswith('07_sunset') or label.startswith('07_sunrise')) and row_date in label:
                        matching = item
                        break

            temperature = matching.get('temperature_2m', 'N/A') if matching else 'N/A'
            humidity = matching.get('relative_humidity_2m', 'N/A') if matching else 'N/A'
            dew_point = matching.get('dew_point_2m', 'N/A') if matching else 'N/A'
            percipitation_probability = matching.get('precipitation_probability', 'N/A') if matching else 'N/A'
            percipitation = matching.get('precipitation', 'N/A') if matching else 'N/A'
            rain = matching.get('rain', 'N/A') if matching else 'N/A'
            showers = matching.get('showers', 'N/A') if matching else 'N/A'
            snowfall = matching.get('snowfall', 'N/A') if matching else 'N/A'
            cloud_cover_low = matching.get('cloud_cover_low', 'N/A') if matching else 'N/A'
            cloud_cover_mid = matching.get('cloud_cover_mid', 'N/A') if matching else 'N/A'
            cloud_cover_high = matching.get('cloud_cover_high', 'N/A') if matching else 'N/A'
            cloud_cover_total = matching.get('cloud_cover_total', 'N/A') if matching else 'N/A'
            visibility = matching.get('visibility', 'N/A') if matching else 'N/A'

            # st.write(f"**Temperature:** {temperature} °C")
            # st.write(f"**Humidity:** {humidity} %")
            # st.write(f"**Visibility:** {visibility} ")
            # st.write(f"**CC Low:** {cloud_cover_low} %")
            # st.write(f"**CC Mid:** {cloud_cover_mid} %")
            # st.write(f"**CC High:** {cloud_cover_high} %")
    

        with col5:
            st.write(f"**Date:** {row.get('Date', 'N/A')}")
            st.write(f"**Time:** {row.get('Time', 'N/A')}")           
            # Extract label from Raw Image URL instead of using the ranked image label
            if "Raw Image" in row and pd.notna(row["Raw Image"]):
                raw_url = row["Raw Image"]
                raw_filename = raw_url.split('/')[-1]  # Get filename from URL
                raw_label = raw_filename.split('.')[0]  # Remove extension
                st.write(f"**Label:** {raw_label}")
            else:
                st.write(f"**Label:** No raw image")


        st.divider()

    # st.title("Ranked Images")

    # data = pd.DataFrame(ranked_images)
    
    # # Convert Score to numeric
    # data["Score"] = pd.to_numeric(data["Score"], errors='coerce')
    
    # # Sort by Score from highest to lowest
    # data = data.sort_values(by="Score", ascending=False)

    # config = {
    #     "Ranked Image": st.column_config.ImageColumn(
    #         help="Click to view full size"
    #     ),
    #     "Raw Image": st.column_config.ImageColumn(
    #         help="Click to view full size"
    #     ),
    #     "Score": st.column_config.ProgressColumn(
    #         "Score",
    #         min_value=0,
    #         max_value=100,
    #         format="%.2f%%"
    #     ),
    # }

    # # Always use data_editor for better image display
    # st.data_editor(
    #     data, 
    #     column_config=config, 
    #     use_container_width=True,
    #     height=800,
    #     disabled=True  # Makes it read-only but with better styling
    # )
