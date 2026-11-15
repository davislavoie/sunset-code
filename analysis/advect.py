"""The satellite cloud mask moved forward to sunset with the wind: does it beat today's mask in the forecast?

The cloud that will sit in a zone at sunset is now upwind of it by wind x (time to sunset). For every pre shot
of the sunset cameras, the GOES-East clear-sky mask (ABI-L2-ACMC) from the latest scan landed by the capture
time (ai_analysis/goes.py, as live) is read, and the zones (ai_analysis.goes.zone_masks: near 5-40 km, far
80-300 km, fan 5-300 km, sun bearing +/-30 deg) are evaluated around the camera moved upwind by
speed x dt, the sun azimuth kept. The wind is Open-Meteo's historical forecast at the hour nearest the capture
(the same source as aloft.py; direction = where it blows from, km/h). Two steering choices, fixed in advance:

  adv700_<zone>   700 hPa wind
  advtop_<zone>   by the stored far-zone cloud-top height (goes_top_far): under 2 km 850 hPa, 2-6 km 700 hPa,
                  6 km and up 500 hPa, 700 hPa when it's missing
  rev*_<zone>     the same with the wind reversed (sanity check only)
  *_<zone>_in     share of the displaced zone that fell inside the downloaded window (under 60% -> missing)

As goes.py: wcax_tower_sunset (3 km from btv_echo_cam) is read around btv_echo_cam's position with its own sun
azimuth, so the two cameras share a window. Each window is kept as a compressed .npz (mask as int8 + the
fixed-grid x/y and projection) so the features can be recomputed without downloading.

    python advect.py              # fetch what's missing (resumable, 6 processes), then write advect.md
    python advect.py --recompute  # rebuild shots.jsonl from the saved windows (no downloads), then advect.md
    python advect.py --check      # self-check: wind direction sign, and the window reader matches the live one
"""

import json
import math
import os
import sys
from concurrent.futures import ProcessPoolExecutor
from datetime import timedelta

import numpy as np
import pandas as pd
import requests
from scipy.stats import spearmanr

import data

sys.path.insert(0, str(data.ROOT))
from ai_analysis import goes as G  # noqa: E402

OUT = data.EXPORT / "advect"
WIN = OUT / "windows"
WIN.mkdir(parents=True, exist_ok=True)
SHOTS = OUT / "shots.jsonl"
CENTERS = {"btv_echo_cam": "btv_echo_cam", "wcax_tower_sunset": "btv_echo_cam", "bolton_summit_cam": "bolton_summit_cam"}
HORIZONS = ("01_2h_pre", "02_1h_pre", "03_45m_pre", "04_30m_pre", "05_15m_pre", "06_5m_pre")
LEVELS = ("850hPa", "700hPa", "500hPa")
ZONES = ("near", "far", "fan")
PROJ = ("perspective_point_height", "semi_major_axis", "semi_minor_axis", "longitude_of_projection_origin")
MIN_IN = 0.6
FEATS = [f"{k}{s}_{z}" for k in ("adv", "rev") for s in ("700", "top") for z in ZONES]
CANDIDATES = {"+adv700 far": ["adv700_far"], "+adv700 fan": ["adv700_fan"], "+advtop far": ["advtop_far"],
              "+advtop fan": ["advtop_fan"], "+adv700 change": ["adv700_fan_change"]}
BTV = (44.48, -73.22)
session = requests.Session()


def hourly():
    """Open-Meteo historical-forecast winds per center (the aloft.py request, to 2026-10-16, own cache)."""
    path, centers = OUT / "aloft.json", sorted(set(CENTERS.values()))
    if not path.exists():
        resp = requests.get("https://historical-forecast-api.open-meteo.com/v1/forecast", timeout=300, params={
            "latitude": ",".join(str(data.LOCATION[c][0]) for c in centers),
            "longitude": ",".join(str(data.LOCATION[c][1]) for c in centers),
            "hourly": ",".join(f"wind_{v}_{l}" for l in LEVELS for v in ("speed", "direction")),
            "start_date": "2025-05-15", "end_date": "2026-10-16", "timezone": "GMT", "timeformat": "unixtime"})
        resp.raise_for_status()
        path.write_text(resp.text)
    out = {}
    for c, loc in zip(centers, json.loads(path.read_text())):
        assert all(loc["hourly_units"][f"wind_speed_{l}"] == "km/h" for l in LEVELS), loc["hourly_units"]
        h = pd.DataFrame(loc["hourly"])
        out[c] = h.set_index(pd.to_datetime(h.pop("time"), unit="s", utc=True))
    return out


def read_window(url, lat0, lon0):
    """G.cloud_window, but keeping the window's fixed-grid x/y and projection instead of lat/lon (compact)."""
    import h5py
    f = G.RangeFile(url, session)
    with h5py.File(f, "r") as h:
        scale = lambda v: h[v][:] * h[v].attrs["scale_factor"][0] + h[v].attrs["add_offset"][0]
        x, y = scale("x"), scale("y")
        proj = {k: np.asarray(h["goes_imager_projection"].attrs[k]) for k in PROJ}
        lat, lon = G.latlon_grid(x[::20], y[::20], proj)
        d = (lat - lat0) ** 2 + ((lon - lon0) * math.cos(math.radians(lat0))) ** 2
        iy, ix = (20 * i for i in np.unravel_index(np.nanargmin(d), d.shape))
        ys, xs = slice(max(0, iy - 200), iy + 200), slice(max(0, ix - 200), ix + 200)
        bcm = h["BCM"][ys, xs].astype(np.int8)
    bcm[(bcm < 0) | (bcm > 1)] = -1
    return {"bcm": bcm, "x": x[xs], "y": y[ys], **proj}, f.fetched


def window(url, center):
    """(bcm 0/1/nan, lat, lon, KB downloaded) for one scan around a center; the .npz on disk is reused."""
    path, kb = WIN / f"{center}_{G.scan_start(url):%Y%j%H%M%S}.npz", 0
    if not path.exists():
        w, fetched = read_window(url, *data.LOCATION[center][:2])
        tmp = path.with_suffix(f".{os.getpid()}.tmp")
        with tmp.open("wb") as fh:
            np.savez_compressed(fh, **w)
        os.replace(tmp, path)
        kb = fetched / 1024
    z = np.load(path)
    lat, lon = G.latlon_grid(z["x"], z["y"], {k: z[k] for k in PROJ})
    bcm = z["bcm"].astype(float)
    bcm[bcm < 0] = np.nan
    return bcm, lat, lon, kb


def zone_stats(bcm, lat, lon, lat0, lon0, az):
    """{zone: (cloudy share of valid pixels, pixels of the zone inside the window)}."""
    m = G.zone_masks(lat, lon, lat0, lon0, az)
    return {z: (float(np.nanmean(bcm[m[z]])) if np.isfinite(bcm[m[z]]).any() else None, int(m[z].sum())) for z in ZONES}


def features(bcm, lat, lon, s):
    lat0, lon0, _ = data.LOCATION[s["center"]]
    ref = zone_stats(bcm, lat, lon, lat0, lon0, s["az"])
    row = {f"cur_{z}": ref[z][0] for z in ZONES}
    for tag, lvl in (("700", "700hPa"), ("top", s["top_level"])):
        spd, frm = s["wind"][lvl]
        for kind, bearing in (("adv", frm), ("rev", frm + 180)):  # upwind = toward where the wind blows from
            got = zone_stats(bcm, lat, lon, *data.destination(lat0, lon0, bearing, spd * s["dt"]), s["az"])
            for z in ZONES:
                row[f"{kind}{tag}_{z}"], row[f"{kind}{tag}_{z}_in"] = got[z][0], round(got[z][1] / ref[z][1], 3)
    return row


def read_task(task):
    """Shots that share a center and a capture slot (btv + wcax): usually one scan, downloaded once."""
    out = []
    for s in task:
        try:
            url = G.scan_url(pd.Timestamp(s["t"]).to_pydatetime(), session)
            if url:
                bcm, lat, lon, kb = window(url, s["center"])
                out.append({"camera": s["camera"], "time": s["time"], "scan": url.rsplit("/", 1)[1], "kb": round(kb),
                            "dt": s["dt"], "top_level": s["top_level"], **features(bcm, lat, lon, s)})
        except Exception as e:  # S3 slow, odd file: retried next run
            print(f"  {s['camera']} {s['time']}: {e}", flush=True)
    return out


def shot_list(cap):
    w, rows = hourly(), []
    for r in cap[cap.camera.isin(CENTERS) & cap.label.isin(HORIZONS)].itertuples():
        sun, az = data.sun_time_and_bearing(r.day, r.camera)
        h = w[CENTERS[r.camera]]
        i = h.index.get_indexer([r.t], method="nearest")[0]  # the forecast hour nearest the capture
        top = pd.to_numeric(r.goes_top_far, errors="coerce")
        rows.append({"camera": r.camera, "time": r.time, "t": r.t.isoformat(), "day": r.day, "label": r.label,
                     "center": CENTERS[r.camera], "az": az, "dt": round((sun - r.t).total_seconds() / 3600, 3),
                     "top_level": "700hPa" if top != top else "850hPa" if top < 2 else "700hPa" if top < 6 else "500hPa",
                     "wind": {l: (float(h[f"wind_speed_{l}"].iloc[i]), float(h[f"wind_direction_{l}"].iloc[i])) for l in LEVELS}})
    return rows


def fetch(cap):
    done = {(r["camera"], r["time"]) for r in map(json.loads, SHOTS.read_text().splitlines())} if SHOTS.exists() else set()
    todo = [s for s in shot_list(cap) if (s["camera"], s["time"]) not in done]
    tasks = {}
    for s in todo:
        tasks.setdefault((s["center"], s["day"], s["label"]), []).append(s)
    print(f"{len(todo)} shots to read in {len(tasks)} tasks", flush=True)
    # h5py holds a global lock even while it waits on the network (goes.py), so processes, not threads.
    with SHOTS.open("a") as f, ProcessPoolExecutor(6) as pool:
        for i, rows in enumerate(pool.map(read_task, list(tasks.values()), chunksize=2), 1):
            for row in rows:
                f.write(json.dumps(row) + "\n")
            f.flush()
            if i % 100 == 0:
                print(i, "tasks", flush=True)


# ---------------------------------------------------------------- report

def md(df, **kw):
    return df.round(3).to_markdown(**kw)


def shots(cap):
    r = pd.DataFrame(map(json.loads, SHOTS.read_text().splitlines())).drop_duplicates(["camera", "time"], keep="last")
    r = r.merge(cap[["camera", "time", "day", "label", "goes_fan", "goes_far", "goes_near"]], on=["camera", "time"])
    for c in ("goes_fan", "goes_far", "goes_near"):
        r[c] = pd.to_numeric(r[c], errors="coerce")
    r["raw_far"] = r.adv700_far.notna()
    for c in FEATS:
        r.loc[r[f"{c}_in"] < MIN_IN, c] = np.nan
    return r


def sunset_truth(cap):
    """Stored zone values at the capture nearest sunset (07_sunset, else the nearest within 20 min)."""
    c = cap[cap.camera.isin(CENTERS)].copy()
    for z in ZONES:
        c[f"goes_{z}"] = pd.to_numeric(c[f"goes_{z}"], errors="coerce")
    c = c.dropna(subset=["goes_fan"])
    sun = {k: data.sun_time_and_bearing(k[1], k[0])[0] for k in set(zip(c.camera, c.day))}
    c["off"] = [abs((t - sun[k]).total_seconds()) for t, k in zip(c.t, zip(c.camera, c.day))]
    c = c[c.off <= 1200].sort_values("off").drop_duplicates(["camera", "day"])
    return c[["camera", "day"] + [f"goes_{z}" for z in ZONES]].rename(columns={f"goes_{z}": f"sun_{z}" for z in ZONES})


def sanity(r, cap):
    d = r.merge(sunset_truth(cap), on=["camera", "day"])
    rows = []
    for h in ("01_2h_pre", "02_1h_pre"):
        for steer in ("700", "top"):
            for z in ZONES:
                g = d[d.label == h].dropna(subset=[f"cur_{z}", f"adv{steer}_{z}", f"rev{steer}_{z}", f"sun_{z}"])
                row = {"horizon": h, "steering": steer, "zone": z, "n": len(g)}
                for name, col in (("persist", f"cur_{z}"), ("displaced", f"adv{steer}_{z}"), ("reversed", f"rev{steer}_{z}")):
                    row[f"rho {name}"] = spearmanr(g[col], g[f"sun_{z}"])[0]
                    row[f"MAE {name}"] = (g[col] - g[f"sun_{z}"]).abs().mean()
                row["displaced best"] = bool(row["rho displaced"] > max(row["rho persist"], row["rho reversed"])
                                             and row["MAE displaced"] < min(row["MAE persist"], row["MAE reversed"]))
                rows.append(row)
    return pd.DataFrame(rows)


def dmw_files(when, hours=2):
    """DMWC keys listed for the hours up to `when`."""
    return [k for i in range(hours) for k in G.listing(f"{when - timedelta(hours=i):%Y/%j/%H}", session, "ABI-L2-DMWC")]


def dmw():
    import h5py
    out = ["## Feasibility: GOES derived motion winds (ABI-L2-DMWC)\n"]
    hours = [pd.Timestamp("2026-10-07 20:00", tz="UTC"), pd.Timestamp("2026-10-07 21:00", tz="UTC")]
    resp = [session.get(f"{G.BUCKET}/?list-type=2&prefix=ABI-L2-DMWC/{h:%Y/%j/%H}/", timeout=30).text for h in hours]
    files = pd.DataFrame([{"hour": f"{h:%Y-%m-%d %H}Z", "band": k.split("<Key>")[1].split("-M6")[1][:3], "KB": int(k.split("<Size>")[1].split("<")[0]) / 1024}
                          for h, t in zip(hours, resp) for k in t.split("<Contents>")[1:]])
    out += ["Files per hour by band (the band is in the name, `-M6C14_`), and size:\n",
            md(files.groupby(["hour", "band"]).KB.agg(files="size", median_KB="median").reset_index(), index=False)]
    key = [k for k in dmw_files(hours[1] + timedelta(minutes=59), 1) if "C14" in k][0]
    with h5py.File(G.RangeFile(f"{G.BUCKET}/{key}", session), "r") as h:
        per = [k for k, v in h.items() if hasattr(v, "shape") and len(v.shape) == 1 and v.shape[0] > 100]
        out += [f"\nVariables per wind vector in `{key.rsplit('/', 1)[1]}`: {', '.join(per)} ({h['lat'].shape[0]} vectors, "
                f"speed {h['wind_speed'].attrs['units'].decode()}, pressure {h['pressure'].attrs['units'].decode()}); "
                "plus per-file summaries (vector counts per layer, cloud-top pressure stats).\n"]
    cap = data.captures()
    p = cap[(cap.camera == "btv_echo_cam") & (cap.label == "02_1h_pre")].assign(fan=lambda x: pd.to_numeric(x.goes_fan, errors="coerce")).dropna(subset=["fan"])
    pick = pd.concat([p[p.fan >= .8].sample(4, random_state=1), p[p.fan <= .1].sample(4, random_state=1)])
    rows = []
    for day, fan in zip(pick.day, pick.fan):
        when = data.sun_time_and_bearing(day, "btv_echo_cam")[0] - timedelta(hours=1.5)
        keys = [k for k in dmw_files(when) if G.scan_start(k) <= when - timedelta(minutes=15)]
        row = {"day": day, "fan cloud": fan, "UTC": f"{when:%H:%M}"}
        for band in ("C02", "C07", "C08", "C09", "C10", "C14"):
            ks = [k for k in keys if f"-M6{band}_" in k]
            if not ks:
                row[band] = "no file"
                continue
            with h5py.File(G.RangeFile(f"{G.BUCKET}/{max(ks, key=G.scan_start)}", session), "r") as h:
                lat, lon, pr, q = h["lat"][:], h["lon"][:], h["pressure"][:], h["DQF"][:]
            km = 6371 * 2 * np.arcsin(np.sqrt(np.sin(np.radians(lat - BTV[0]) / 2) ** 2 + np.cos(np.radians(lat)) * math.cos(math.radians(BTV[0]))
                                                * np.sin(np.radians(lon - BTV[1]) / 2) ** 2))
            ok = (km <= 300) & (q == 0)
            row[band] = f"{ok.sum()} ({(pr[ok] >= 700).sum()}/{((pr[ok] >= 400) & (pr[ok] < 700)).sum()}/{(pr[ok] < 400).sum()})"
        rows.append(row)
    out += ["Good-quality (DQF 0) vectors within 300 km of Burlington, latest file of each band landed by 1.5 h before sunset "
            "(4 cloudy and 4 clear days by the 1h-pre GOES fan cloud at btv_echo_cam). Cell: total (low >= 700 hPa / "
            "mid 400-700 / high < 400):\n", md(pd.DataFrame(rows), index=False)]
    return out, pd.DataFrame(rows)


def report(cap):
    import extra
    r = shots(cap)
    pre = cap[cap.camera.isin(CENTERS) & cap.label.isin(HORIZONS)]
    cov = pd.DataFrame({"pre shots": pre.groupby("label").size(), "read": r.groupby("label").size(),
                        "adv700 value read": r.groupby("label").raw_far.sum(),
                        **{f"{c} kept": r.groupby("label")[c].count() for c in ("adv700_far", "adv700_fan", "advtop_far", "advtop_fan")},
                        "adv700_far dropped (<60% in window)": r.groupby("label").apply(lambda g: (g.adv700_far_in < MIN_IN).sum()),
                        "advtop_far dropped": r.groupby("label").apply(lambda g: (g.advtop_far_in < MIN_IN).sum()),
                        "median dt h": r.groupby("label").dt.median()})
    lvl = r.groupby("label").top_level.value_counts().unstack(fill_value=0)
    agree = r.dropna(subset=["cur_fan", "goes_fan"])
    s = sanity(r, cap)

    t = extra.table()
    f = r[["camera", "day", "label"] + FEATS].rename(columns={"label": "horizon"})
    t = t.merge(f, on=["camera", "day", "horizon"], how="left")
    t["adv700_fan_change"] = t.adv700_fan - t.goes_fan
    cols = ["adv700_far", "adv700_fan", "adv700_near", "advtop_far", "advtop_fan", "advtop_near", "adv700_fan_change", "goes_fan", "goes_far"]
    rho = pd.DataFrame({h: {c: spearmanr(g[c], g.pct, nan_policy="omit")[0] for c in cols} for h, g in t.groupby("horizon")}).T
    e = extra.evaluate(t, CANDIDATES)
    rep = extra.report(t, CANDIDATES)
    dmw_text, dmw_rows = dmw()

    ok = s["displaced best"].sum()
    far_fan = s[s.zone != "near"]
    gains = e.dropna(subset=["AUC gain"]).assign(beat=lambda x: x["AUC gain"] > x["shuffled 95%"])
    per = gains.groupby("set", sort=False).agg(n=("beat", "size"), beat=("beat", "sum"), gain=("AUC gain", "mean"), null=("shuffled 95%", "mean"))
    verdict = [f"- Projection check: the displaced mask beats both persistence and the reversed wind (higher Spearman and lower MAE "
               f"against the sunset value) in {ok} of {len(s)} horizon/steering/zone rows ({far_fan['displaced best'].sum()} of "
               f"{len(far_fan)} for far and fan). Mean Spearman over the far/fan rows: persistence {far_fan['rho persist'].mean():.3f}, "
               f"displaced {far_fan['rho displaced'].mean():.3f}, reversed {far_fan['rho reversed'].mean():.3f}; "
               f"mean MAE {far_fan['MAE persist'].mean():.3f} / {far_fan['MAE displaced'].mean():.3f} / {far_fan['MAE reversed'].mean():.3f}."]
    if far_fan["displaced best"].mean() < .5:
        verdict.append("- **The projection does not work: on most far/fan rows the displaced value does not beat both persistence "
                       "and the reversed wind, so the forecast test below is not meaningful.**")
    for name, g in per.iterrows():
        verdict.append(f"- {name}: mean AUC gain {g.gain:+.3f} vs mean shuffled 95% {g.null:+.3f}; beats the shuffle on "
                       f"{int(g.beat)} of {int(g.n)} horizon fits.")
    helps = (per.beat >= per.n / 2) & (per.gain > per.null)
    verdict.append("- Overall: " + ("the projected mask beats the shuffled-input null on most horizons for " + ", ".join(per.index[helps])
                                    if helps.any() else "no candidate's gain clears the shuffled 95% on most horizons: the projected mask "
                                    "adds nothing over the live line's current goes_fan beyond noise") + ".")
    c14 = dmw_rows["C14"].str.split(" ").str[0].astype(float) if "C14" in dmw_rows else pd.Series(dtype=float)
    verdict.append(f"- DMW: C14 (IR cloud-drift) vectors within 300 km at 1.5 h before sunset, median {c14.median():.0f} over the 8 times "
                   f"(min {c14.min():.0f}); see the table for the other bands.")

    text = "\n".join([
        f"# Cloud mask moved forward to sunset with the wind ({len(r)} pre shots read)\n",
        "\n\n".join(__doc__.split("\n\n")[1:4]).strip() + "\n",
        "## Verdict\n", *verdict,
        "\n## Coverage per horizon\n", md(cov),
        f"\nSteering level picked by cloud-top height (advtop):\n\n{md(lvl)}\n",
        f"Reader check: this script's undisplaced fan vs the stored goes_fan at the same shot: Spearman "
        f"{spearmanr(agree.cur_fan, agree.goes_fan)[0]:.3f}, MAE {(agree.cur_fan - agree.goes_fan).abs().mean():.3f} ({len(agree)} shots; "
        "wcax is read around btv_echo_cam here, around its own spot live). "
        f"Download: {r.kb[r.kb > 0].mean():.0f} KB per scan on average, {(r.kb > 0).sum()} windows downloaded, the rest shared with another camera.\n",
        "## Sanity check: does the displaced mask predict the zone's cloud at sunset?\n",
        "Truth: the stored zone value at the 07_sunset capture (else the capture nearest sunset, within 20 min). "
        "persist = today's zone value at the shot; displaced = the zone moved upwind by wind x dt; reversed = moved downwind.\n",
        md(s, index=False),
        "\n## Spearman with the outcome (pct) per horizon\n", md(rho),
        "\n## Forecast test (extra.report: live line + the new input, leave-one-month-out, 30 shuffles)\n", rep,
        "\n", *dmw_text])
    (data.ROOT / "analysis" / "advect.md").write_text(text, encoding="utf-8")
    print(text)


def check():
    lat, lon = data.destination(44.5, -73.2, 270, 100)  # a west wind: the upwind cloud is to the west
    assert lon < -74 and abs(lat - 44.5) < .1, (lat, lon)
    url = G.scan_url(pd.Timestamp("2026-10-07 21:00", tz="UTC").to_pydatetime(), session)
    bcm, lat, lon = G.cloud_window(url, *data.LOCATION["btv_echo_cam"][:2], session)
    b2, la2, lo2, _ = window(url, "btv_echo_cam")
    assert np.allclose(lat, la2, equal_nan=True) and np.allclose(lon, lo2, equal_nan=True) and np.allclose(bcm, b2, equal_nan=True)
    print("ok")


if __name__ == "__main__":
    if "--check" in sys.argv:
        check()
        raise SystemExit
    cap = data.captures()
    if "--recompute" in sys.argv and SHOTS.exists():
        SHOTS.unlink()
    fetch(cap)
    report(cap)
