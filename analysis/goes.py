"""Observed cloud from GOES-East (GOES-19) over the fan toward the sun, plus KBTV METAR cloud layers.

GOES: NOAA's public bucket noaa-goes19, product ABI-L2-ACMC (CONUS clear-sky mask, 2 km, every 5 min).
Reading (HTTP range requests, projection, zones) is ai_judge/goes.py, which the live forecast uses.
For each sunset camera-day, the scan nearest 1 h before sunset (and nearest sunset) gives cloud
fractions (BCM: 0 clear / 1 cloudy) over: overhead (within 10 km), near fan (sun bearing +/-30 deg,
5-40 km), far fan (80-300 km), whole fan (5-300 km). Cached per camera-day in analysis_export/goes/.

METAR: Iowa Environmental Mesonet ASOS download for KBTV, the report nearest 1 h before sunset:
cloud layers (FEW/SCT/BKN/OVC + base ft) -> ceiling and a coverage score.

    python analysis/goes.py [limit]       # fetch (resumable) and evaluate -> goes.md
    python analysis/goes.py --shots       # GOES at every pre-sunset capture, for the forecast fit (horizons.py)
"""

import json
from concurrent.futures import ProcessPoolExecutor
import math
import sys
import time
from datetime import timedelta

import numpy as np
import pandas as pd
import requests

import data

sys.path.insert(0, str(data.ROOT))
from ai_judge import goes as G  # noqa: E402

CACHE = data.EXPORT / "goes"
CACHE.mkdir(parents=True, exist_ok=True)
CENTERS = {"btv_echo_cam": "btv_echo_cam", "wcax_tower_sunset": "btv_echo_cam", "bolton_summit_cam": "bolton_summit_cam"}
session = requests.Session()


def zones(url, lat0, lon0, az):
    """Cloud fractions over the camera's zones from one scan (ai_judge.goes, plus a narrow path)."""
    bcm, lat, lon = G.cloud_window(url, lat0, lon0, session)
    out = {k.replace("goes_", ""): v for k, v in G.zones(bcm, lat, lon, lat0, lon0, az).items()}
    dy, dx = (lat - lat0) * 111.2, (lon - lon0) * 111.2 * math.cos(math.radians(lat0))
    dist, off = np.hypot(dx, dy), np.abs((np.degrees(np.arctan2(dx, dy)) - az + 180) % 360 - 180)
    m = (off <= 10) & (dist >= 40) & (dist <= 300)
    out["path"] = float(np.nanmean(bcm[m])) if np.isfinite(bcm[m]).any() else np.nan
    return out


def fetch(d, limit=None):
    rows, todo = [], d[["camera", "day"]].drop_duplicates()
    if limit:
        todo = todo.sample(frac=1, random_state=0).head(limit)
    for i, (cam, day) in enumerate(todo.itertuples(index=False), 1):
        path = CACHE / f"{cam}_{day}.json"
        if not path.exists():
            when, az = data.sun_time_and_bearing(day, cam)
            lat0, lon0, _ = data.LOCATION[CENTERS[cam]]
            row = {"camera": cam, "day": str(day)}
            started = time.monotonic()
            for tag, back in (("g1h", 1), ("g0", 0)):
                try:
                    url = G.scan_url(when - timedelta(hours=back) + G.LATENCY, session)
                    if url:
                        row.update({f"{k}_{tag}": v for k, v in zones(url, lat0, lon0, az).items()})
                except Exception as e:
                    print(f"  {cam} {day} {tag}: {e}", flush=True)
            row["sec"] = round(time.monotonic() - started, 1)
            path.write_text(json.dumps(row))
            print(i, cam, day, row.get("fan_g1h"), row.get("kb_g1h"), row["sec"], "s", flush=True)
        rows.append(json.loads(path.read_text()))
    return pd.DataFrame(rows)


HORIZONS = ("01_2h_pre", "02_1h_pre", "03_45m_pre", "04_30m_pre", "05_15m_pre", "06_5m_pre")


def read_shot(args):
    camera, time_, day, t = args
    lat0, lon0, _ = data.LOCATION[CENTERS[camera]]
    _, az = data.sun_time_and_bearing(day, camera)
    try:
        return {"camera": camera, "time": time_, **(G.observe(t, lat0, lon0, az, requests) or {})}
    except Exception as e:
        print(f"  {camera} {time_}: {e}", flush=True)


def shots():
    """GOES fields for every pre-sunset capture of the sunset cameras, as the live forecast reads them
    (latest scan landed by the capture time). Cached in analysis_export/goes/shots.jsonl."""
    path = CACHE / "shots.jsonl"
    done = {(r["camera"], r["time"]) for r in map(json.loads, path.read_text().splitlines())} if path.exists() else set()
    cap = data.captures()
    cap = cap[cap.camera.isin(CENTERS) & cap.label.isin(HORIZONS)]
    todo = [r for r in cap.itertuples() if (r.camera, r.time) not in done]
    print(f"{len(todo)} captures to read", flush=True)
    # h5py holds a global lock even while waiting on the network, so use processes, 16 at a time.
    with path.open("a") as f, ProcessPoolExecutor(16) as pool:
        for i, row in enumerate(pool.map(read_shot, [(r.camera, r.time, r.day, r.t.to_pydatetime()) for r in todo], chunksize=4), 1):
            if row:
                f.write(json.dumps(row) + chr(10))
                f.flush()
            if i % 100 == 0:
                print(i, flush=True)
    return pd.DataFrame(map(json.loads, path.read_text().splitlines()))


COVER = {"CLR": 0, "SKC": 0, "NSC": 0, "FEW": .19, "SCT": .44, "BKN": .75, "OVC": 1, "VV": 1}


def metar(days):
    """KBTV report nearest 1 h before sunset per day: cover (biggest layer), ceiling and lowest base (ft)."""
    path = CACHE / "kbtv_metar.csv"
    if not path.exists():
        lo, hi = min(days), max(days) + timedelta(days=1)
        resp = session.get("https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py", timeout=300, params=[
            ("station", "BTV"), *[("data", f"sky{k}{i}") for k in "cl" for i in range(1, 5)], ("data", "vsby"),
            ("year1", lo.year), ("month1", lo.month), ("day1", lo.day), ("year2", hi.year), ("month2", hi.month), ("day2", hi.day),
            ("tz", "Etc/UTC"), ("format", "onlycomma"), ("latlon", "no"), ("missing", "M"), ("trace", "T"), ("direct", "no"),
            ("report_type", "3"), ("report_type", "4")])
        resp.raise_for_status()
        path.write_text(resp.text)
    m = pd.read_csv(path, na_values="M")
    m["t"] = pd.to_datetime(m.valid, utc=True)
    m = m.set_index("t").sort_index()
    m = m[~m.index.duplicated()]
    rows = []
    for day in days:
        when, _ = data.sun_time_and_bearing(day, "btv_echo_cam")
        r = m.iloc[m.index.get_indexer([pd.Timestamp(when) - pd.Timedelta(hours=1)], method="nearest")[0]]
        layers = [(r[f"skyc{i}"], r[f"skyl{i}"]) for i in range(1, 5) if isinstance(r[f"skyc{i}"], str)]
        ceil = min([b for c, b in layers if c in ("BKN", "OVC", "VV") and b == b], default=30000)
        rows.append({"day": day, "metar_cover": max([COVER.get(c, 0) for c, _ in layers], default=0),
                     "metar_ceiling": ceil, "metar_base": min([b for c, b in layers if b == b], default=30000),
                     "metar_vis": r.vsby})
    return pd.DataFrame(rows)


def evaluate(g, t):
    from analyze import ENGINEERED, MET, STORED_PATH, cv, scores
    g = g.assign(day=pd.to_datetime(g.day).dt.date)
    d = t.merge(g, on=["camera", "day"]).merge(metar(sorted(set(t.day))), on="day")
    d = d.dropna(subset=["fan_g1h"]).reset_index(drop=True)
    v = pd.DataFrame(map(json.loads, (data.EXPORT / "vision_qwen3-vl_4b.jsonl").read_text().splitlines()))
    v = v.drop_duplicates(["camera", "day"], keep="last").assign(day=lambda x: pd.to_datetime(x.day).dt.date)
    dv = d.merge(v[["camera", "day", "cloud_cover"]], on=["camera", "day"])
    rho = lambda df, a, b: df[a].corr(df[b], method="spearman")
    zones = [f"{z}_g1h" for z in ("over", "near", "far", "fan", "path")]
    mcols = ["metar_cover", "metar_ceiling", "metar_base", "metar_vis"]
    out = [f"# GOES-East observed cloud and KBTV METAR ({len(d)} sunset camera-days)\n",
           f"Cost: {d.kb_g1h.mean():.0f} KB and {d.sec.mean() / 2:.1f} s per scan on average (HTTP range reads of a 4 MB file).\n",
           "## Agreement (Spearman)\n",
           pd.DataFrame({z: {"Open-Meteo total @h1": rho(d, z, "cloud_cover_total@h1"), "Open-Meteo blanket @h1": rho(d, z, "blanket_any_h1"),
                             "AI photo cover (160 days)": rho(dv, z, "cloud_cover"), "METAR cover": rho(d, z, "metar_cover")}
                         for z in zones}).round(2).to_markdown(),
           "\n## The 9 days Open-Meteo called clear but the photos were cloudy\n"]
    missed = [("btv_echo_cam", "2026-09-01"), ("bolton_summit_cam", "2026-09-01"), ("btv_echo_cam", "2026-08-23"),
              ("btv_echo_cam", "2026-04-05"), ("wcax_tower_sunset", "2026-08-31"), ("wcax_tower_sunset", "2026-10-10"),
              ("btv_echo_cam", "2025-12-15"), ("bolton_summit_cam", "2026-04-24"), ("btv_echo_cam", "2026-08-31")]
    keys = pd.DataFrame(missed, columns=["camera", "day"]).assign(day=lambda x: pd.to_datetime(x.day).dt.date)
    out += [keys.merge(d, on=["camera", "day"], how="left")[["camera", "day", "cloud_cover_total@h1", "over_g1h", "fan_g1h", "metar_cover",
                                                               "metar_ceiling"]].round(2).to_markdown(index=False),
            "\n## Spearman with the outcome (sunset-window best, percentile)\n",
            pd.Series({c: rho(d, c, "y_pct") for c in zones + [z.replace("g1h", "g0") for z in zones] + mcols}).round(3).to_frame("rho").to_markdown()]
    for cam in CENTERS:
        d[f"is_{cam}"] = (d.camera == cam).astype(int)
    cams = [f"is_{c}" for c in CENTERS]
    base = [f"{e}_h1" for e in ENGINEERED] + [c for c in STORED_PATH + MET if c.endswith("h1")] + cams
    res = []
    for name, feats in (("weather", base), ("weather + GOES", base + zones), ("weather + METAR", base + mcols),
                        ("weather + GOES + METAR", base + zones + mcols), ("GOES only", zones + cams), ("METAR only", mcols + cams)):
        for kind in ("ridge", "gbm"):
            res.append({"features": name, "model": kind, **scores(d, cv(d, feats, "y_pct", kind))})
    out += ["\n## Leave-one-month-out (1 h before sunset)\n", pd.DataFrame(res).round(3).to_markdown(index=False)]
    text = "\n".join(out)
    (data.ROOT / "analysis" / "goes.md").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    if "--shots" in sys.argv:
        shots()
        raise SystemExit
    t = pd.read_parquet(data.EXPORT / "analysis_table.parquet")
    t = t[t.camera.isin(CENTERS)].dropna(subset=["y_pct"])
    g = fetch(t, int(sys.argv[1]) if len(sys.argv) > 1 else None)
    evaluate(g, t)
