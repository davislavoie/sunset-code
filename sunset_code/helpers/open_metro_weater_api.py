import openmeteo_requests
import pandas as pd
import requests_cache
from retry_requests import retry
from timezonefinder import TimezoneFinder
from datetime import datetime, timezone, timedelta
import time
import os
from zoneinfo import ZoneInfo


def weather_fetch(latitude=None, longitude=None, date=None, time_epoch=None):
	# Defaults are worked out per call (a default like time.time() in the signature is
	# evaluated once, at import). Location defaults to the camera's LAT/LON from its config.
	latitude = float(latitude if latitude is not None else os.environ.get("LAT", 44.494563))
	longitude = float(longitude if longitude is not None else os.environ.get("LON", -73.436528))
	time_epoch = time.time() if time_epoch is None else time_epoch

	# Initialize timezone finder
	tf = TimezoneFinder()
	timezone_str = tf.timezone_at(lat=latitude, lng=longitude)

	# The API reads start/end dates in the location's local time ("timezone": "auto"), so the
	# date must be local too. A UTC date is the next day for an evening capture after
	# midnight UTC (8 PM EDT), which returned the next day's midnight weather.
	if date is None:
		date = datetime.fromtimestamp(time_epoch, tz=ZoneInfo(timezone_str)).strftime('%Y-%m-%d')

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

	# Convert UTC times to local timezone
	hourly_dataframe['local_time'] = hourly_dataframe['date'].dt.tz_convert(timezone_str)

	# Get current time in UTC (since our data is in UTC)
	requested_time_utc = datetime.fromtimestamp(time_epoch, tz=timezone.utc)

	# Find the closest time to current hour in our data
	closest_time_idx = (hourly_dataframe['date'] - requested_time_utc).abs().idxmin()
	current_weather = hourly_dataframe.iloc[[closest_time_idx]]

	return current_weather


# ---- Clouds toward the sunset -------------------------------------------------------------
# Low cloud 50-300 km toward where the sun sets (rises, for a sunrise camera) blocks the light
# before it reaches the sky over the camera. On ~480 ranked days it predicted the day's best
# score better than the clouds overhead (median best 7 with >=70% low cloud out there, 31 when
# clear). Stored as path50_/path150_/path300_ + cloud_cover_low/mid/high.

PATH_KM = [50, 150, 300]
# The bearing is rounded to this many degrees (26 km sideways at 300 km), so days share
# locations and a backfill needs far fewer Open-Meteo calls.
BEARING_STEP = 5
PATH_LAYERS = ["cloud_cover_low", "cloud_cover_mid", "cloud_cover_high"]


def sun_bearing(day, latitude, longitude, mode="sunset"):
	"""Compass bearing (to BEARING_STEP degrees) of the sun at that local day's sunset or sunrise."""
	from astral import Observer
	from astral.sun import azimuth, sunrise, sunset
	observer = Observer(latitude=latitude, longitude=longitude)
	# Local time zone: in UTC an evening sunset is on the next date, and some UTC dates have none.
	tz = ZoneInfo(TimezoneFinder().timezone_at(lat=latitude, lng=longitude))
	bearing = azimuth(observer, (sunrise if mode == "sunrise" else sunset)(observer, date=day, tzinfo=tz))
	return round(bearing / BEARING_STEP) * BEARING_STEP


def path_points(latitude, longitude, bearing):
	"""[(km, lat, lon)] along the bearing, on a sphere."""
	import math
	points = []
	for km in PATH_KM:
		d, b = km / 6371.0, math.radians(bearing)
		p1, l1 = math.radians(latitude), math.radians(longitude)
		p2 = math.asin(math.sin(p1) * math.cos(d) + math.cos(p1) * math.sin(d) * math.cos(b))
		l2 = l1 + math.atan2(math.sin(b) * math.sin(d) * math.cos(p1), math.cos(d) - math.sin(p1) * math.sin(p2))
		points.append((km, math.degrees(p2), math.degrees(l2)))
	return points


def path_hourly(latitude, longitude, bearing, start_date, end_date, historical=True):
	"""{unix hour (UTC): {"path50_cloud_cover_low": ..., ...}} for start..end (YYYY-MM-DD, inclusive)."""
	import requests
	points = path_points(latitude, longitude, bearing)
	url = "https://historical-forecast-api.open-meteo.com/v1/forecast" if historical else "https://api.open-meteo.com/v1/forecast"
	resp = requests.get(url, timeout=120, params={
		"latitude": ",".join(f"{lat:.4f}" for _, lat, _ in points),
		"longitude": ",".join(f"{lon:.4f}" for _, _, lon in points),
		"hourly": ",".join(PATH_LAYERS), "start_date": start_date, "end_date": end_date,
		"timezone": "GMT", "timeformat": "unixtime",
	})
	resp.raise_for_status()
	hours = {}
	for (km, _, _), location in zip(points, resp.json()):  # one result per location, in order
		h = location["hourly"]
		for i, t in enumerate(h["time"]):
			for layer in PATH_LAYERS:
				if h[layer][i] is not None:
					hours.setdefault(t, {})[f"path{km}_{layer}"] = float(h[layer][i])
	return hours


def path_clouds(time_epoch=None, latitude=None, longitude=None, mode=None):
	"""Cloud cover along the sunset (or sunrise) direction for the hour nearest time_epoch."""
	latitude = float(latitude if latitude is not None else os.environ.get("LAT", 44.494563))
	longitude = float(longitude if longitude is not None else os.environ.get("LON", -73.436528))
	mode = mode or os.environ.get("MODE", "sunset")
	time_epoch = time.time() if time_epoch is None else time_epoch
	local = datetime.fromtimestamp(time_epoch, tz=ZoneInfo(TimezoneFinder().timezone_at(lat=latitude, lng=longitude)))
	day = local.date()
	bearing = sun_bearing(day, latitude, longitude, mode)
	# A day either side: the hour nearest an evening capture can fall on the next UTC date.
	hours = path_hourly(latitude, longitude, bearing, str(day - timedelta(days=1)), str(day + timedelta(days=1)),
						historical=time_epoch < time.time() - 2 * 24 * 3600)
	return hours.get(round(time_epoch / 3600) * 3600, {})
