import openmeteo_requests
import pandas as pd
import requests_cache
from retry_requests import retry
from timezonefinder import TimezoneFinder
from datetime import datetime, timezone
import time


def weather_fetch(latitude= 44.494563, longitude = -73.436528, date = pd.Timestamp.now().strftime('%Y-%m-%d'), time_epoch = time.time()):
	# Initialize timezone finder
	tf = TimezoneFinder()

	# Setup the Open-Meteo API client with cache and retry on error
	cache_session = requests_cache.CachedSession('.cache', expire_after = 3600)
	retry_session = retry(cache_session, retries = 5, backoff_factor = 0.2)
	openmeteo = openmeteo_requests.Client(session = retry_session)

	# Make sure all required weather variables are listed here
	# The order of variables in hourly or daily is important to assign them correctly below
	two_days = 24*60*60*2

	if time_epoch < (time.time() - two_days):
		url =  "https://historical-forecast-api.open-meteo.com/v1/forecast"

	else:
		url = "https://api.open-meteo.com/v1/forecast"

	params = {
		"latitude": latitude,
		"longitude": longitude,
		"timezone": "auto",

		"hourly": ["temperature_2m", "relative_humidity_2m", "dew_point_2m", "precipitation_probability", 
		"precipitation", "rain", "showers", "snowfall", "cloud_cover_low", "cloud_cover_high", "cloud_cover_mid", 
		"cloud_cover", "visibility"],

		"start_date": date,
		"end_date": date,	
		"wind_speed_unit": "mph",
		"temperature_unit": "fahrenheit",
	}

	responses = openmeteo.weather_api(url, params=params)

	# Process first location. Add a for-loop for multiple locations or weather models
	response = responses[0]

	# Process hourly data. The order of variables needs to be the same as requested.
	hourly = response.Hourly()
	hourly_temperature_2m = hourly.Variables(0).ValuesAsNumpy()
	hourly_relative_humidity_2m = hourly.Variables(1).ValuesAsNumpy()
	hourly_dew_point_2m = hourly.Variables(2).ValuesAsNumpy()
	hourly_precipitation_probability = hourly.Variables(3).ValuesAsNumpy()
	hourly_precipitation = hourly.Variables(4).ValuesAsNumpy()
	hourly_rain = hourly.Variables(5).ValuesAsNumpy()
	hourly_showers = hourly.Variables(6).ValuesAsNumpy()
	hourly_snowfall = hourly.Variables(7).ValuesAsNumpy()
	hourly_cloud_cover_low = hourly.Variables(8).ValuesAsNumpy()
	hourly_cloud_cover_high = hourly.Variables(9).ValuesAsNumpy()
	hourly_cloud_cover_mid = hourly.Variables(10).ValuesAsNumpy()
	hourly_total_cloud_cover = hourly.Variables(11).ValuesAsNumpy()
	hourly_visibility = hourly.Variables(12).ValuesAsNumpy()

	hourly_data = {"date": pd.date_range(
		start = pd.to_datetime(hourly.Time(), unit = "s", utc = True),
		end = pd.to_datetime(hourly.TimeEnd(), unit = "s", utc = True),
		freq = pd.Timedelta(seconds = hourly.Interval()),
		inclusive = "left"
	)}

	hourly_data["temperature_2m"] = hourly_temperature_2m
	hourly_data["relative_humidity_2m"] = hourly_relative_humidity_2m
	hourly_data["dew_point_2m"] = hourly_dew_point_2m
	hourly_data["precipitation_probability"] = hourly_precipitation_probability
	hourly_data["precipitation"] = hourly_precipitation
	hourly_data["rain"] = hourly_rain
	hourly_data["showers"] = hourly_showers
	hourly_data["snowfall"] = hourly_snowfall
	hourly_data["cloud_cover_low"] = hourly_cloud_cover_low
	hourly_data["cloud_cover_high"] = hourly_cloud_cover_high
	hourly_data["cloud_cover_mid"] = hourly_cloud_cover_mid
	hourly_data["cloud_cover_total"] = hourly_total_cloud_cover
	hourly_data["visibility"] = hourly_visibility

	hourly_dataframe = pd.DataFrame(data = hourly_data)

	# Get timezone for the specified coordinates
	latitude = params["latitude"]
	longitude = params["longitude"]
	timezone_str = tf.timezone_at(lat=latitude, lng=longitude)

	# Convert UTC times to local timezone
	hourly_dataframe['local_time'] = hourly_dataframe['date'].dt.tz_convert(timezone_str)

	# Get current time in UTC (since our data is in UTC)
	requested_time_utc = datetime.fromtimestamp(time_epoch, tz=timezone.utc)

	# Find the closest time to current hour in our data
	closest_time_idx = (hourly_dataframe['date'] - requested_time_utc).abs().idxmin()
	current_weather = hourly_dataframe.iloc[[closest_time_idx]]

	return current_weather
