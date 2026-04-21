import streamlit as st
from influxdb import InfluxDBClient
from datetime import datetime
from urllib.parse import quote, unquote
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

def show_page(sunset_data, all_data, ranked_images):
    st.title("Score Tracker")
    st.write("Track and visualize sunset scores over time")
    
    # Convert to DataFrame and clean data
    data = pd.DataFrame(ranked_images)
    data["Score"] = pd.to_numeric(data["Score"], errors='coerce')
    
    # Convert Date to datetime for proper sorting
    data["dt_local"] = pd.to_datetime(data["dt_local"])
    
    # Extract separate date and time columns for axis options
    data["Date_Only"] = data["Date"]
    data["Time_Only"] = data["Time"]
    
    # Axis selection controls at the top
    col1, col2 = st.columns(2)
    with col1:
        x_axis = st.selectbox("X-Axis:", ["Date Only", "Time Only", "Score"], index=0)
    with col2:
        y_axis = st.selectbox("Y-Axis:", ["Score", "Date Only", "Time Only"], index=0)
    
    st.divider()
         
    if not data.empty:
        # Map axis selections to actual column names
        axis_mapping = {
            "Date Only": "Date_Only", 
            "Time Only": "Time_Only",
            "Score": "Score"
        }
        
        x_col = axis_mapping[x_axis]
        y_col = axis_mapping[y_axis]
        
        # Sort data by X-axis column to prevent crossing lines
        data_sorted = data.sort_values(by=x_col)
        
        # Create tabs for chart and data
        tab1, tab2 = st.tabs(["Line Chart","Data"])
        
        with tab1:
            # Create Plotly figure with click events
            fig = go.Figure()
            
            fig.add_trace(go.Scatter(
                x=data_sorted[x_col],
                y=data_sorted[y_col],
                mode='lines+markers',
                name='Sunset Data',
                customdata=data_sorted.index,  # Store row indices from sorted data
                hovertemplate="<b>%{text}</b><br>" +
                             f"{x_axis}: %{{x}}<br>" +
                             f"{y_axis}: %{{y:.2f}}<br>" +
                             "Click to see image<br>" +
                             "<extra></extra>",
                text=data_sorted["Label"],
                line=dict(width=2),
                marker=dict(size=8)
            ))
            
            fig.update_layout(
                title=f"{y_axis} vs {x_axis} (Click points to see images)",
                xaxis_title=x_axis,
                yaxis_title=y_axis,
                height=600,
                hovermode='closest'
            )
            
            # Add grid lines
            fig.update_xaxes(
                showgrid=True,
                gridwidth=1,
                gridcolor='rgba(128, 128, 128, 0.3)'
            )
            fig.update_yaxes(
                showgrid=True,
                gridwidth=1,
                gridcolor='rgba(128, 128, 128, 0.3)'
            )
            
            # Display chart and capture click events
            clicked_data = st.plotly_chart(fig, use_container_width=True, on_select="rerun")
            
            # Show images when point is clicked
            if clicked_data and clicked_data["selection"]["points"]:
                point_index = clicked_data["selection"]["points"][0]["customdata"]
                selected_row = data.iloc[point_index]  # Use original data index
                
                # Score info on left, images on right
                col1, col2 = st.columns([1, 3])
                
                with col1:
                    st.metric("Selected Score", f"{selected_row['Score']:.2f}")
                    st.write(f"**Label:** {selected_row['Label']}")
                    st.write(f"**Date:** {selected_row['dt_local'].strftime('%Y-%m-%d %H:%M')}")
                    st.write(f"**X-Value:** {selected_row[x_col]}")
                    st.write(f"**Y-Value:** {selected_row[y_col]}")
                
                with col2:
                    # Show both images side by side in right column
                    img_col1, img_col2 = st.columns(2)
                    with img_col1:
                        st.image(selected_row["Ranked Image"], caption="Ranked Image (with analysis)", width=400)
                    
                    with img_col2:
                        if "Raw Image" in selected_row and pd.notna(selected_row["Raw Image"]):
                            st.image(selected_row["Raw Image"], caption="Original Image", width=400)
                        else:
                            st.info("No original image available")
        
        with tab2:
            st.dataframe(
                data[["dt_local", "Date_Only", "Time_Only", "Score", "Label"]].sort_values("dt_local", ascending=False),
                height=400, 
                use_container_width=True
            )
        
        # Summary stats
        st.subheader("Summary Statistics")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Average Score", f"{data['Score'].mean():.1f}")
        with col2:
            st.metric("Highest Score", f"{data['Score'].max():.1f}")
        with col3:
            st.metric("Lowest Score", f"{data['Score'].min():.1f}")
        with col4:
            st.metric("Total Images", len(data))
            
    else:
        st.info("No data available.")