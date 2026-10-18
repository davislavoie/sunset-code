"""Glass-lake reflections on btv_echo_cam vs wind.

btv_echo_cam cycles through PTZ presets, so there is no fixed sky / lake region. Instead every thumb is
searched for the row that best acts as a mirror (ai_analysis/reflect.py, which shows the result as a badge).
A calm lake mirroring the sky scores high; ripples, docks, boats and trees score low. Wind (10 m, km/h) at sunset comes from Open-Meteo's historical-forecast API
at the camera and 10 km out over the lake toward the sun, cached in analysis_export/openmeteo/.

    python analysis/reflection.py
"""

import json
import sys

import numpy as np
import pandas as pd
import requests

import data

sys.path.insert(0, str(data.ROOT))
from ai_analysis import reflect  # noqa: E402

CAM = "btv_echo_cam"
THUMBS = data.EXPORT / "thumbs" / CAM
LABELS = ["05_15m_pre", "07_sunset"]


def mirror_score(path):
    """(best correlation, mirror row as a fraction of height) for one thumb: ai_analysis.reflect's detector."""
    return reflect.mirror_score(open(path, "rb").read())


def wind(days):
    path = data.EXPORT / "openmeteo" / f"wind_{CAM}.json"
    lat0, lon0, _ = data.LOCATION[CAM]
    if not path.exists():
        pts = [(lat0, lon0), data.destination(lat0, lon0, 245, 10)]
        resp = requests.get("https://historical-forecast-api.open-meteo.com/v1/forecast", timeout=120, params={
            "latitude": ",".join(f"{p[0]:.4f}" for p in pts), "longitude": ",".join(f"{p[1]:.4f}" for p in pts),
            "hourly": "wind_speed_10m,wind_gusts_10m,wind_direction_10m", "start_date": str(min(days)),
            "end_date": str(max(days)), "timezone": "GMT", "timeformat": "unixtime"})
        resp.raise_for_status()
        path.write_text(resp.text)
    rows = []
    for where, loc in zip(("cam", "lake"), json.loads(path.read_text())):
        h = pd.DataFrame(loc["hourly"])
        h["t"] = pd.to_datetime(h.time, unit="s", utc=True)
        rows.append(h.set_index("t").drop(columns="time").add_prefix(f"{where}_"))
    hourly = pd.concat(rows, axis=1)
    out = []
    for day in days:
        when, _ = data.sun_time_and_bearing(day, CAM)
        out.append({"day": day, **hourly.iloc[hourly.index.get_indexer([pd.Timestamp(when)], method="nearest")[0]].to_dict()})
    return pd.DataFrame(out)


def main():
    d = data.days()
    d = d[d.camera == CAM].copy()
    d["pct"] = d.y.rank(pct=True)
    for label in LABELS:
        res = {day: mirror_score(THUMBS / f"{day}_{label}.jpg") for day in d.day if (THUMBS / f"{day}_{label}.jpg").exists()}
        d[f"mirror_{label}"] = d.day.map(lambda x: res.get(x, (np.nan,))[0])
    d["mirror"] = d[[f"mirror_{l}" for l in LABELS]].max(axis=1)
    d = d.merge(wind(list(d.day)), on="day")
    d["lake_wind"] = d[["cam_wind_speed_10m", "lake_wind_speed_10m"]].max(axis=1)
    d.to_parquet(data.EXPORT / "reflection.parquet")
    return d


if __name__ == "__main__":
    if len(sys.argv) > 1:  # python reflection.py <thumb> : score one image
        print(mirror_score(sys.argv[1]))
    else:
        main()
