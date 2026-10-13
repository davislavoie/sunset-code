"""Observed weather at each capture: the latest METAR from the nearest airport (KBTV for all our cameras),
from the Iowa Environmental Mesonet's ASOS archive (free, no key, live within minutes).

Open-Meteo's history is model output, and its visibility in particular misfires (btv 2026-02-01 30m post:
1 km and 45 % low cloud under a clear sky; KBTV reported FEW at 20,000 ft). This is what was measured.
Stored as obs_* fields; the dashboard shows them in place of the model's visibility. Not a forecast input:
METAR added nothing on top of GOES (analysis/metar.md).

ASOS reports cloud only up to 12,000 ft and visibility only up to 10 miles.
"""

import bisect
import csv
import io
import logging
import os
from datetime import datetime, timedelta, timezone

import requests

from . import store

log = logging.getLogger(__name__)

URL = "https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py"
STATION = os.environ.get("METAR_STATION", "BTV")
MAX_AGE = timedelta(minutes=90)    # a report older than this before the capture doesn't count
GIVE_UP = timedelta(days=2)        # captures this old with no report get obs_station "" so they aren't refetched
COVER = {"CLR": 0, "SKC": 0, "NSC": 0, "FEW": .19, "SCT": .44, "BKN": .75, "OVC": 1, "VV": 1}
KT_TO_MPH = 1.15078


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def parse(row):
    """One IEM row -> obs_* fields (numbers where they exist, sky and present weather as text)."""
    layers = [(row[f"skyc{i}"], num(row[f"skyl{i}"])) for i in range(1, 5) if row.get(f"skyc{i}") not in (None, "", "M")]
    ceiling = min([b for c, b in layers if c in ("BKN", "OVC", "VV") and b is not None], default=None)
    fields = {
        "obs_station": STATION,
        "obs_time": row["valid"],
        "obs_visibility_mi": num(row.get("vsby")),
        "obs_temp_f": num(row.get("tmpf")),
        "obs_dewpoint_f": num(row.get("dwpf")),
        "obs_rh": num(row.get("relh")),
        "obs_wind_mph": None if num(row.get("sknt")) is None else round(num(row["sknt"]) * KT_TO_MPH, 1),
        "obs_gust_mph": None if num(row.get("gust")) is None else round(num(row["gust"]) * KT_TO_MPH, 1),
        # float(): a CLR 0 written as an integer once fixes the field's type (obs_cover went that way)
        "obs_cloud": float(max([COVER.get(c, 0) for c, _ in layers], default=0)),
        "obs_ceiling_ft": ceiling,
        "obs_sky": " ".join(f"{c}{'' if b is None else f' {b:.0f}'}" for c, b in layers) or "CLR",
        "obs_wx": "" if row.get("wxcodes") in (None, "M") else row["wxcodes"],  # e.g. -RA, BR, HZ, FU (smoke)
    }
    return {k: v for k, v in fields.items() if v is not None}  # InfluxDB can't store null


def reports(start, end):
    """[(utc datetime, row)] sorted, for start..end (dates, inclusive)."""
    resp = requests.get(URL, timeout=300, params=[
        ("station", STATION), *[("data", d) for d in ("vsby", "tmpf", "dwpf", "relh", "sknt", "gust", "wxcodes")],
        *[("data", f"sky{k}{i}") for k in "cl" for i in range(1, 5)],
        ("year1", start.year), ("month1", start.month), ("day1", start.day),
        ("year2", end.year), ("month2", end.month), ("day2", end.day),
        ("tz", "Etc/UTC"), ("format", "onlycomma"), ("latlon", "no"), ("missing", "M"),
        ("trace", "T"), ("direct", "no"), ("report_type", "3"), ("report_type", "4")])
    resp.raise_for_status()
    rows = [(datetime.strptime(r["valid"], "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc), r)
            for r in csv.DictReader(io.StringIO(resp.text))]
    return sorted(rows, key=lambda x: x[0])


def latest(rows, when, keys=None):
    """The last report at or before when, if it's fresh enough. keys: the rows' times, precomputed."""
    i = bisect.bisect_right(keys or [t for t, _ in rows], when) - 1
    return rows[i][1] if i >= 0 and when - rows[i][0] <= MAX_AGE else None


def fill(client, camera):
    todo = [p for p in store.captures(client, camera)
            if p.get("obs_station") is None or (p["obs_station"] and p.get("obs_cloud") is None)]
    if not todo:
        return 0
    times = {id(p): datetime.fromtimestamp(store.epoch_seconds(p), timezone.utc) for p in todo}
    rows = reports(min(times.values()).date() - timedelta(days=1), max(times.values()).date() + timedelta(days=1))
    now, writes, keys = datetime.now(timezone.utc), [], [t for t, _ in rows]
    for p in todo:
        r = latest(rows, times[id(p)], keys)
        if r:
            writes.append(store.field_point(p, parse(r)))
        elif now - times[id(p)] > GIVE_UP:
            writes.append(store.field_point(p, {"obs_station": ""}))
    if writes:
        client.write_points(writes, batch_size=1000)
    log.info("%s: %s observations on %d of %d captures", camera, STATION, len(writes), len(todo))
    return len(writes)
