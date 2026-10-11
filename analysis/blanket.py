"""A dense blanket of cloud readings toward the sun, from Open-Meteo's historical-forecast API.

Points sit on a fixed fan of absolute compass bearings (every 10 deg) x distances around each
camera, so one request covers a month of days even though the sun's bearing moves daily; a day's
"sun +/- N deg" reading is the grid bearing nearest to it (at most 5 deg off). wcax_tower_sunset
shares btv_echo_cam's fan (3 km apart). Responses are cached under analysis_export/openmeteo/.

    python analysis/blanket.py          # fetch (resumable; backs off on 429)
"""

import calendar
import json
import time
from datetime import date, timedelta

import numpy as np
import pandas as pd
import requests

import data

URL = "https://historical-forecast-api.open-meteo.com/v1/forecast"
KM = [5, 13, 25, 40, 60, 80, 120, 160, 220, 300]
OFFSETS = [-30, -20, -10, 0, 10, 20, 30]
LAYERS = ["cloud_cover_low", "cloud_cover_mid", "cloud_cover_high"]
HOURS = {"h0": 0, "h1": 1, "h2": 2}  # hours before the sunset / sunrise
CENTER = {"btv_echo_cam": "btv_echo_cam", "wcax_tower_sunset": "btv_echo_cam",
          "bolton_summit_cam": "bolton_summit_cam", "wcax_tower_sunrise": "wcax_tower_sunrise"}
CACHE = data.EXPORT / "openmeteo"
CHUNK = 60  # locations per request
CACHE.mkdir(parents=True, exist_ok=True)


def plan(days):
    """[(center, month, [bearings], start, end)] covering every camera-day."""
    jobs = {}
    for cam, day in days[["camera", "day"]].itertuples(index=False):
        _, az = data.sun_time_and_bearing(day, cam)
        key = (CENTER[cam], day.strftime("%Y-%m"))
        lo, hi = jobs.get(key, (999, -999))
        jobs[key] = (min(lo, az), max(hi, az))
    out = []
    for (center, month), (lo, hi) in sorted(jobs.items()):
        bearings = list(range(int(np.floor((lo - 35) / 10) * 10), int(np.ceil((hi + 35) / 10) * 10) + 1, 10))
        y, m = map(int, month.split("-"))
        start = date(y, m, 1) - timedelta(days=1)
        end = min(date(y, m, calendar.monthrange(y, m)[1]) + timedelta(days=1), date.today() - timedelta(days=1))
        out.append((center, month, bearings, start, end))
    return out


def fetch(center, month, bearings, start, end):
    lat0, lon0, _ = data.LOCATION[center]
    points = [(b % 360, km, *data.destination(lat0, lon0, b, km)) for b in bearings for km in KM]
    rows = []
    for i in range(0, len(points), CHUNK):
        chunk = points[i:i + CHUNK]
        path = CACHE / f"{center}_{month}_{i // CHUNK}_{bearings[0]}-{bearings[-1]}.json"
        if not path.exists():
            for attempt in range(30):
                resp = requests.get(URL, timeout=180, params={
                    "latitude": ",".join(f"{p[2]:.4f}" for p in chunk),
                    "longitude": ",".join(f"{p[3]:.4f}" for p in chunk),
                    "hourly": ",".join(LAYERS), "start_date": str(start), "end_date": str(end),
                    "timezone": "GMT", "timeformat": "unixtime"})
                if resp.status_code == 429:
                    reason = resp.json().get("reason", "")
                    wait = 60 if "Minutely" in reason else 600
                    print(f"  429 ({reason}); waiting {wait}s", flush=True)
                    time.sleep(wait)
                    continue
                resp.raise_for_status()
                path.write_text(resp.text)
                time.sleep(6)
                break
            else:
                raise SystemExit("gave up on rate limit")
        result = json.loads(path.read_text())
        result = result if isinstance(result, list) else [result]
        for (b, km, _, _), loc in zip(chunk, result):
            h = loc["hourly"]
            for j, t in enumerate(h["time"]):
                rows.append((center, b, km, t, *(h[l][j] for l in LAYERS)))
    return rows


def grid():
    """All cached readings: center, bearing, km, unix hour, low, mid, high."""
    days = data.days()
    rows = []
    for job in plan(days):
        print(job[0], job[1], f"{len(job[2]) * len(KM)} points", flush=True)
        rows += fetch(*job)
    g = pd.DataFrame(rows, columns=["center", "bearing", "km", "t"] + LAYERS)
    return g.drop_duplicates(["center", "bearing", "km", "t"])


def features(days, g):
    """Per camera-day: blanket readings at sun+offset x km x layer x hour-before-sun,
    as columns like  low_o0_k80_h0  (low cloud, on the sun's bearing, 80 km out, at sunset)."""
    idx = g.set_index(["center", "bearing", "km", "t"]).sort_index()
    out = []
    for cam, day in days[["camera", "day"]].itertuples(index=False):
        when, az = data.sun_time_and_bearing(day, cam)
        sun_hour = round(when.timestamp() / 3600) * 3600
        mode = data.LOCATION[cam][2]
        row = {"camera": cam, "day": day, "sun_az": az}
        for tag, hrs in HOURS.items():
            # Before a sunrise is earlier too: the forecast that a pre-dawn reading would see.
            t = sun_hour - hrs * 3600
            for off in OFFSETS:
                b = int(round((az + off) / 10) * 10) % 360
                for km in KM:
                    try:
                        vals = idx.loc[(CENTER[cam], b, km, t)]
                    except KeyError:
                        continue
                    for layer in LAYERS:
                        row[f"{layer.split('_')[-1]}_o{off}_k{km}_{tag}"] = vals[layer]
        out.append(row)
    return pd.DataFrame(out)


if __name__ == "__main__":
    g = grid()
    g.to_parquet(data.EXPORT / "blanket_grid.parquet")
    f = features(data.days(), g)
    f.to_parquet(data.EXPORT / "blanket_features.parquet")
    print(g.shape, f.shape, f.isna().mean().mean())
