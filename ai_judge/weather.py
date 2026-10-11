"""Hourly weather for each capture, from Open-Meteo (free, no key), merged onto the
capture's point under the field names helpers.influxdb_push had commented out.

One request per camera covers its whole history: the historical-forecast API keeps
the forecasts as they were issued, up to today, so training data matches what a
live prediction would see. Each capture gets the hour nearest its own UTC time.
"""

import logging
import os
from datetime import timedelta
from pathlib import Path

import requests

from . import store

log = logging.getLogger(__name__)

URL = "https://historical-forecast-api.open-meteo.com/v1/forecast"
FIELDS = ["temperature_2m", "relative_humidity_2m", "dew_point_2m", "precipitation_probability",
          "precipitation", "rain", "showers", "snowfall", "cloud_cover_low", "cloud_cover_mid",
          "cloud_cover_high", "cloud_cover", "visibility"]
# Stored as cloud_cover_total, the name the commented-out pipeline code used.
STORED = {"cloud_cover": "cloud_cover_total"}


def camera_location(camera):
    """LAT/LON from config/<camera>.env (the files the dashboard's Config page manages)."""
    config = Path(os.environ.get("CONFIG_DIR", "config")) / f"{camera}.env"
    values = dict(line.strip().split("=", 1) for line in config.read_text().splitlines()
                  if "=" in line and not line.lstrip().startswith("#"))
    return float(values["LAT"]), float(values["LON"])


def hourly(lat, lon, start, end):
    """{unix hour: {field: value}} for start..end (dates, inclusive), in UTC."""
    resp = requests.get(URL, timeout=120, params={
        "latitude": lat, "longitude": lon, "hourly": ",".join(FIELDS),
        "start_date": start.isoformat(), "end_date": end.isoformat(),
        "timezone": "GMT", "timeformat": "unixtime",
        "temperature_unit": "fahrenheit", "wind_speed_unit": "mph",
    })
    resp.raise_for_status()
    data = resp.json()["hourly"]
    return {t: {STORED.get(f, f): data[f][i] for f in FIELDS} for i, t in enumerate(data["time"])}


def weather_for(point, hours):
    """The fields for the hour nearest the capture, minus missing values (InfluxDB can't store null)."""
    hour = round(store.epoch_seconds(point) / 3600) * 3600
    return {k: float(v) for k, v in hours.get(hour, {}).items() if v is not None}


def fill(client, camera, since=None, before=None, refill=False):
    """Add weather to the camera's captures that don't have it yet. Returns how many got it."""
    todo = [p for p in store.captures(client, camera, since=since, before=before)
            if refill or p.get("cloud_cover_total") is None]
    if not todo:
        return 0
    days = [store.local_date(p) for p in todo]
    # A day either side: an evening's UTC hours fall on the next UTC date.
    hours = hourly(*camera_location(camera), min(days) - timedelta(days=1), max(days) + timedelta(days=1))
    writes = [store.field_point(p, f) for p in todo if (f := weather_for(p, hours))]
    client.write_points(writes, batch_size=1000)
    log.info("%s: weather added to %d of %d captures", camera, len(writes), len(todo))
    return len(writes)
