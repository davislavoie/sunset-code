"""Does GOES cloud *thickness* toward the sun add to the live forecast? Coverage (goes_far, goes_fan) can't tell
thin cirrus, which lets the sun through and lights up, from a thick deck that blocks it; optical depth can.

Product ABI-L2-CODC (CONUS cloud optical depth at 640 nm, 2 km, every 5 min, ~4.7 MB) on noaa-goes19, read
with ai_analysis/goes.py's RangeFile / scan_url / latlon_grid / zone_masks. COD and DQF are stored in chunks
of 52 full rows, so only the rows the zones need are read. For every pre shot of the sunset cameras, the latest
COD scan that had landed by the capture time (as analysis/goes.py --shots), per zone (over / near / far / fan,
same centres and sun bearing as goes_*):

  cod_valid_<z>  share of the zone's pixels with a COD value
  cod_med_<z>    median COD of pixels with COD > 0
  cod_thin_<z>   share of the zone's pixels with 0 < COD < 5 (THIN)
  cod_thick_<z>  share with COD >= 20 (THICK)            (both thresholds fixed before looking at results)
  cod_log_<z>    mean log1p(COD) over the zone, clear (COD 0) and missing pixels as 0
  cod_good_<z>   share the quality flag marks good (DQF & 4 == 0)
  cod_day_<z>    share retrieved by the day algorithm (DQF & 1 == 0): a diagnostic, not a candidate

Cached per shot in analysis_export/thickness/shots.jsonl (resumable). Then: comparability by horizon and by
sun elevation, Spearman with the outcome, and extra.report on a pre-declared list of candidate sets.

    ../.venv/Scripts/python -W ignore thickness.py --probe   # bytes per scan on a few scans
    ../.venv/Scripts/python -W ignore thickness.py --fetch   # download (resumable, ~1 h+)
    ../.venv/Scripts/python -W ignore thickness.py           # evaluate -> thickness.md
"""

import json
import math
import sys
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import requests
from scipy.stats import spearmanr

import data
from goes import CENTERS, HORIZONS

sys.path.insert(0, str(data.ROOT))
from ai_analysis import goes as G  # noqa: E402

PRODUCT = "ABI-L2-CODC"
THIN, THICK = 5, 20
ZONES = ("over", "near", "far", "fan")
CACHE = data.EXPORT / "thickness"
SHOTS = CACHE / "shots.jsonl"
CACHE.mkdir(parents=True, exist_ok=True)
FETCH = HORIZONS  # cut to 2h/1h/30m/15m if a scan costs over ~1.5 MB
CANDIDATES = {"+thick far": ["cod_thick_far"], "+thin far": ["cod_thin_far"], "+thin+thick far": ["cod_thin_far", "cod_thick_far"],
              "+log far": ["cod_log_far"], "+thin over+thick far": ["cod_thin_over", "cod_thick_far"]}
# Written after reading the numbers above (run of 2026-11-14); re-read them if the data changes.
VERDICT = """**No: thickness does not help the forecast, and it should not go live.**

- Score: every candidate set's gain in AUC top-25% is between -0.004 and +0.007, and the mean gain over the
  horizons is at or below the mean "shuffled 95%" for every set (best: +thin over+thick far, +0.002 vs 0.003).
  The few single horizons that beat the shuffle do so by 0.001-0.007 out of ~50 comparisons: noise.
- Why: the thickness numbers mostly repeat coverage. log1p(COD) correlates 0.84-0.88 with goes_far per horizon and
  thick far 0.65-0.67 on the day-algorithm horizons. On their own they rank the outcome only a little better than
  coverage (log far rho -0.56 vs goes_far -0.51 at 2 h and 1 h), and that edge vanishes once the live line
  (which has goes_fan and the HSV scores) is in the fit.
- Comparability: the shots straddle the product's algorithm switch at sun elevation 8 deg. 2 h and 1 h before
  sunset (sun ~19 and ~8.5 deg up) are the day algorithm (1 h only just: its
  sun sits 0-1.5 deg above the switch), 45 min is mixed, 30/15/5 min are all the night
  algorithm. The night algorithm gives no value on clear pixels (valid share = cloud share, rho 0.96-1.0 with
  goes_far), never gave COD of 20 or more here (cod_thick_far is 0 on every 15 and 5 min shot) and puts nearly all cloud
  under 5, so 'thin' then means 'cloudy'. No day-algorithm pixel is flagged good at these sun angles
  (twilight, solar zenith 65-90 deg); 'good' only appears on night-algorithm pixels.
  So the 2 h and the 15 min readings are not the same measurement, and a feature like cod_thick_far would carry
  a different meaning by horizon and, near 1 h / 45 min, by season.
- What is left: only the day-algorithm horizons (2 h, 1 h) measure thickness as intended, and there thick far
  (rho -0.52/-0.53 with pct) is about as predictive as log far (-0.56) yet adds nothing on top of the live line.
"""


def cod_window(url, lat0, lon0, az, session=requests):
    """(COD, nan where missing; DQF; lat; lon; bytes fetched) over the rows the zones need, from one scan."""
    import h5py

    f = G.RangeFile(url, session)
    with h5py.File(f, "r") as h:
        scale = lambda v: h[v][:] * h[v].attrs["scale_factor"][0] + h[v].attrs["add_offset"][0]
        x, y = scale("x"), scale("y")
        proj = dict(h["goes_imager_projection"].attrs)
        lat, lon = G.latlon_grid(x[::20], y[::20], proj)  # coarse locate, as cloud_window
        d = (lat - lat0) ** 2 + ((lon - lon0) * math.cos(math.radians(lat0))) ** 2
        iy, ix = (20 * i for i in np.unravel_index(np.nanargmin(d), d.shape))
        ys, xs = slice(max(0, iy - 200), iy + 200), slice(max(0, ix - 200), ix + 200)
        lat, lon = G.latlon_grid(x[xs], y[ys], proj)
        rows = np.flatnonzero(np.logical_or.reduce(list(G.zone_masks(lat, lon, lat0, lon0, az).values())).any(axis=1))
        r = slice(ys.start + rows[0], ys.start + rows[-1] + 1)
        raw, dqf = h["COD"][r, xs], h["DQF"][r, xs]
        cod = np.where(raw == h["COD"].attrs["_FillValue"][0], np.nan, raw * h["COD"].attrs["scale_factor"][0])
    return cod, dqf, lat[rows[0]:rows[-1] + 1], lon[rows[0]:rows[-1] + 1], f.fetched


def features(cod, dqf, lat, lon, lat0, lon0, az):
    out = {}
    for z, m in G.zone_masks(lat, lon, lat0, lon0, az).items():
        m &= np.isfinite(lat)
        c, q = cod[m], dqf[m]
        if not c.size:
            continue
        pos = c[c > 0]
        out |= {f"cod_valid_{z}": np.isfinite(c).mean(), f"cod_med_{z}": np.median(pos) if pos.size else None,
                f"cod_thin_{z}": ((c > 0) & (c < THIN)).mean(), f"cod_thick_{z}": (c >= THICK).mean(),
                f"cod_log_{z}": np.nan_to_num(np.log1p(c)).mean(), f"cod_good_{z}": (np.isfinite(c) & (q & 4 == 0)).mean(),
                f"cod_day_{z}": (np.isfinite(c) & (q & 1 == 0)).mean()}
    return {k: None if v is None else round(float(v), 3) for k, v in out.items()}


def read_scan(job):
    """All shots that share one scan, centre and bearing: one download."""
    url, center, az, shots = job
    lat0, lon0, _ = data.LOCATION[center]
    try:
        *w, kb = cod_window(url, lat0, lon0, az)
        f = features(*w, lat0, lon0, az)
        return [{"camera": c, "time": t, "url": url.rsplit("/", 1)[1], "kb": round(kb / 1e3), **f} for c, t in shots]
    except Exception as e:  # S3 hiccup, odd file: retried on the next run
        print(f"  {url}: {e}", flush=True)
        return []


def fetch():
    done = {(r["camera"], r["time"]) for r in map(json.loads, SHOTS.read_text().splitlines())} if SHOTS.exists() else set()
    cap = data.captures()
    cap = cap[cap.camera.isin(CENTERS) & cap.label.isin(FETCH)]
    todo = [r for r in cap.itertuples() if (r.camera, r.time) not in done]
    print(f"{len(todo)} shots to read", flush=True)
    s = requests.Session()

    def locate(r):
        try:
            return r, G.scan_url(r.t.to_pydatetime(), s, PRODUCT)
        except Exception as e:
            print(f"  {r.camera} {r.time}: no listing ({e})", flush=True)
            return r, None

    jobs = {}
    with ThreadPoolExecutor(6) as pool:
        for r, url in pool.map(locate, todo):
            if url:  # echo and wcax are 3 km apart, share a centre (as goes_*) and usually a scan
                az = round(data.sun_time_and_bearing(r.day, r.camera)[1])
                jobs.setdefault((url, CENTERS[r.camera], az), []).append((r.camera, r.time))
    print(f"{len(jobs)} scans to download", flush=True)
    # h5py holds a global lock even while waiting on the network, so processes (as goes.py), 6 at a time.
    with SHOTS.open("a") as f, ProcessPoolExecutor(6) as pool:
        for i, rows in enumerate(pool.map(read_scan, [(*k, v) for k, v in jobs.items()]), 1):
            f.writelines(json.dumps(r) + "\n" for r in rows)
            f.flush()
            if i % 100 == 0:
                print(i, flush=True)


def probe(n=5):
    """Bytes per scan on n shots spread over the year."""
    cap = data.captures()
    cap = cap[cap.camera.eq("btv_echo_cam") & cap.label.isin(HORIZONS)].sample(n, random_state=1)
    lat0, lon0, _ = data.LOCATION["btv_echo_cam"]
    for r in cap.itertuples():
        url = G.scan_url(r.t.to_pydatetime(), requests, PRODUCT)
        az = data.sun_time_and_bearing(r.day, r.camera)[1]
        cod, dqf, lat, lon, kb = cod_window(url, lat0, lon0, az)
        print(r.day, r.label, f"az {az:.0f}", f"{kb / 1e6:.2f} MB", cod.shape, features(cod, dqf, lat, lon, lat0, lon0, az))


def elevation(t, camera):
    from astral import Observer
    from astral.sun import elevation as el
    lat, lon, _ = data.LOCATION[camera]
    return el(Observer(latitude=lat, longitude=lon), t.to_pydatetime())


def evaluate():
    import extra

    c = pd.read_json(SHOTS, lines=True, dtype=False).drop_duplicates(["camera", "time"], keep="last")
    cap = data.captures()[["camera", "time", "day", "label", "t"]]
    c = c.merge(cap, on=["camera", "time"]).rename(columns={"label": "horizon"})
    c["sun_elev"] = [elevation(t, cam) for t, cam in zip(c.t, c.camera)]
    feats = [k for k in c if k.startswith("cod_")]
    for k in feats:
        c[k] = c[k].astype(float)
    t = extra.table()
    shots = t.groupby("horizon").size()
    t = t.merge(c[["camera", "day", "horizon", "sun_elev", "kb"] + feats], on=["camera", "day", "horizon"], how="left")
    q = lambda s: f"{s.quantile(.25):.2f} / {s.median():.2f} / {s.quantile(.75):.2f}"
    band = pd.cut(c.sun_elev, [-10, 0, 4, 8, 12, 16, 25, 90])
    diag = lambda by: c.groupby(by, observed=True).agg(
        cached_shots=("time", "size"), sun_elev=("sun_elev", q), day_algo=("cod_day_far", q),
        good=("cod_good_far", q), valid=("cod_valid_far", q), median_cod=("cod_med_far", q), thick=("cod_thick_far", q))
    rho = lambda g, a: spearmanr(g[a], g.pct, nan_policy="omit")[0]
    corr = t[feats + ["goes_far", "goes_fan"]].corr("spearman").loc[[f for f in feats if "_far" in f or "_fan" in f], ["goes_far", "goes_fan"]]
    rep = extra.report(t, CANDIDATES)
    out = ["# Cloud thickness (GOES optical depth) toward the sun\n", __doc__.split("\n\n")[0] + "\n",
           "Features per zone (over within 10 km, near 5-40 km, far 80-300 km, fan 5-300 km, sun bearing +/-30 deg):\n",
           "\n".join(f"- {l.strip()}" for l in __doc__.split("\n\n")[2].splitlines()) + "\n",
           f"## Download cost\n\nCOD and DQF are gzip chunks of 52 x 2500 (full rows); the reader takes only the rows any zone "
           f"touches. Mean {c.kb.mean() / 1e3:.2f} MB per scan (median {c.kb.median() / 1e3:.2f}, max {c.kb.max() / 1e3:.2f}), "
           f"including the 0.26 MB header block, vs the 4.7 MB file. {c.url.nunique()} scans downloaded for {len(c)} shots.\n",
           "## Coverage (pre shots in extra.table() with a COD reading)\n",
           pd.DataFrame({"shots": shots, "with COD": t.dropna(subset=["cod_valid_far"]).groupby("horizon").size()}).fillna(0).astype(int).to_markdown(),
           "\n## Comparability\n",
           "Product attributes: the day algorithm (visible reflectance) runs where the solar zenith angle is under 82 deg "
           "(sun elevation over 8 deg), the night algorithm (infrared brightness-temperature differences) above it; "
           "DQF marks pixels with solar zenith 65-90 deg (sun 0-25 deg up) as degraded by twilight, so 'good' only "
           "happens with the sun over 25 deg or below the horizon. Far zone, quartiles (25% / median / 75%):\n",
           "### By horizon\n", diag("horizon").to_markdown(), "\n### By sun elevation at the camera (deg)\n", diag(band).to_markdown(),
           "\n### Spearman with the existing coverage (all shots)\n", corr.round(2).to_markdown(),
           "\nPer horizon (far zone): with the night algorithm, clear pixels have no COD, so the 'valid' share becomes the "
           "cloud mask's cloudy share; with the day algorithm, clear pixels read 0 and valid is ~1.\n",
           t.groupby("horizon").apply(lambda g: pd.Series({k: g[k].corr(g.goes_far, method="spearman") for k in
                                                           ("cod_valid_far", "cod_thin_far", "cod_thick_far", "cod_log_far")})).round(2).to_markdown(),
           "\n## Spearman with the outcome (pct) per horizon\n",
           t.groupby("horizon").apply(lambda g: pd.Series({f: rho(g, f) for f in feats + ["goes_far", "goes_fan"] if "_far" in f or "_over" in f or "_fan" in f})).T.round(3).to_markdown(),
           "\n## extra.report (leave-one-month-out; gain in AUC top-25% vs the 95th percentile of the gain with the new inputs shuffled)\n",
           rep, "\n## Verdict\n\n" + VERDICT]
    (data.ROOT / "analysis" / "thickness.md").write_text("\n".join(out), encoding="utf-8")
    print("\n".join(out))


if __name__ == "__main__":
    {"--probe": probe, "--fetch": fetch}.get(sys.argv[1] if len(sys.argv) > 1 else "", evaluate)()
