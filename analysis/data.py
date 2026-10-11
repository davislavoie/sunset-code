"""The InfluxDB export (analysis_export/sunset_images.json) as tidy tables.

captures(): one row per raw capture, labels normalised (older btv labels carry a date suffix).
days():     one row per camera per local day: y = best HSV score among captures that may be the
            day's best shot (store.exclusion: thumbs down / blocked view out, thumbs up overrides),
            plus the stored weather read at the 2h-pre, 1h-pre and sunset captures.
"""

import json
import math
import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
EXPORT = ROOT / "analysis_export"
TZ = ZoneInfo("America/New_York")
SUNSET_CAMS = ["bolton_summit_cam", "btv_echo_cam", "wcax_tower_sunset"]
CAMS = SUNSET_CAMS + ["wcax_tower_sunrise"]
# From config/<camera>.env
LOCATION = {
    "bolton_summit_cam": (44.414868821460125, -72.83398520561539, "sunset"),
    "btv_echo_cam": (44.47664377308622, -73.22124659280774, "sunset"),
    "wcax_tower_sunset": (44.450933, -73.197272, "sunset"),
    "wcax_tower_sunrise": (44.450966, -73.197256, "sunrise"),
}
WEATHER = ["temperature_2m", "relative_humidity_2m", "dew_point_2m", "precipitation", "precipitation_probability",
           "visibility", "cloud_cover_low", "cloud_cover_mid", "cloud_cover_high", "cloud_cover_total"]
PATH = [f"path{km}_cloud_cover_{l}" for km in (13, 40, 80, 50, 150, 300) for l in ("low", "mid", "high")]
READ_AT = {"01_2h_pre": "h2", "02_1h_pre": "h1", "07_sunset": "h0", "07_sunrise": "h0"}


def norm_label(label):
    return re.sub(r"(_\d\d-\d\d-\d{4})?(\.jpg)?$", "", label or "").replace("hr_", "h_")


def excluded(row):
    """store.exclusion without the AI part (ai_view isn't in the export)."""
    thumb = row["thumb"] if row["thumb"] == row["thumb"] and row["thumb"] is not None else 0
    if thumb > 0:
        return False
    return thumb < 0 or bool(row["view_blocked"])


def captures():
    s = json.loads((EXPORT / "sunset_images.json").read_text())["results"][0]["series"][0]
    df = pd.DataFrame(s["values"], columns=s["columns"])
    df["label"] = df["label"].map(norm_label)
    df = df[~df["label"].str.startswith(("11_", "12_"))].copy()
    df["t"] = pd.to_datetime(df["time"], format="ISO8601", utc=True)
    df["day"] = df["t"].dt.tz_convert(TZ).dt.date
    df["excluded"] = df.apply(excluded, axis=1)
    # A day sometimes has a capture twice (old + new label style): keep the first.
    return df.drop_duplicates(["camera", "day", "label"]).reset_index(drop=True)


def days(cap=None):
    cap = captures() if cap is None else cap
    ok = cap[~cap["excluded"]]
    out = ok.groupby(["camera", "day"]).agg(y=("score", "max"), n=("score", "size")).reset_index()
    for label, tag in READ_AT.items():
        cols = [c for c in WEATHER + PATH if c in cap]
        w = cap[cap["label"] == label][["camera", "day", "t"] + cols].rename(
            columns={c: f"{c}@{tag}" for c in cols + ["t"]})
        out = out.merge(w, on=["camera", "day"], how="left", suffixes=("", "_dup"))
        out = out[[c for c in out if not c.endswith("_dup")]]
    # The sunrise camera's "sunset" column came from 07_sunrise; collapse duplicates.
    out = out.loc[:, ~out.columns.duplicated()]
    for tag in ("h2", "h1", "h0"):
        if f"dew_point_2m@{tag}" in out:
            out[f"dewpoint_depression@{tag}"] = out[f"temperature_2m@{tag}"] - out[f"dew_point_2m@{tag}"]
    out["good"] = out.groupby("camera")["y"].transform(lambda y: y >= y.quantile(0.75)).astype(int)
    out["month"] = pd.to_datetime(out["day"]).dt.to_period("M").astype(str)
    return out


def sun_time_and_bearing(day, camera):
    """(UTC datetime, azimuth degrees) of the camera's sunset or sunrise on a local day."""
    from astral import Observer
    from astral.sun import azimuth, sunrise, sunset
    lat, lon, mode = LOCATION[camera]
    obs = Observer(latitude=lat, longitude=lon)
    when = (sunrise if mode == "sunrise" else sunset)(obs, date=day, tzinfo=TZ)
    return when.astimezone(ZoneInfo("UTC")), azimuth(obs, when)


def destination(lat, lon, bearing, km):
    """Point km along bearing on a sphere (same maths as open_metro_weater_api.path_points)."""
    d, b = km / 6371.0, math.radians(bearing)
    p1, l1 = math.radians(lat), math.radians(lon)
    p2 = math.asin(math.sin(p1) * math.cos(d) + math.cos(p1) * math.sin(d) * math.cos(b))
    l2 = l1 + math.atan2(math.sin(b) * math.sin(d) * math.cos(p1), math.cos(d) - math.sin(p1) * math.sin(p2))
    return math.degrees(p2), math.degrees(l2)


if __name__ == "__main__":
    d = days()
    print(d.groupby("camera").agg(days=("y", "size"), median_y=("y", "median"), p75=("y", lambda y: y.quantile(.75))))
    assert norm_label("01_2hr_pre_05-16-2025.jpg") == "01_2h_pre"
    assert norm_label("07_sunset") == "07_sunset"
    lat, lon = destination(44.0, -73.0, 270, 111.2)
    assert abs(lat - 44.0) < 0.05 and abs(lon + 74.39) < 0.05, (lat, lon)
