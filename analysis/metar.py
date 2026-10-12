"""GOES vs ICON path cloud, and METAR cloud layers from airports toward the sunset, at every pre shot.

1. Agreement: GOES observed cloudy share (goes_over/near/far/fan, shots.jsonl) vs ICON path cloud
   low / mid / high / total (mean of 13/40/80 km toward the sun, models.py cache), and which tracks
   the outcome (the day's best window score as a percentile, horizons.py's target) better.
2. METAR (Iowa Environmental Mesonet ASOS archive): the latest report at or before each capture from
   KBTV, KPBG, KSLK, KOGS, KMSS, KART. Per station: cover of the biggest layer (FEW .19 .. OVC 1),
   ceiling (lowest BKN/OVC, ft) and lowest base. "metar_path" = mean cover of the stations within 20 deg
   of the sun's bearing from the camera. ASOS only reports cloud up to 12,000 ft: CLR means nothing
   below that, so high cloud (the best sunset canvas) is invisible to it.
3. Leave-one-month-out AUC (top 25 %) per horizon, METAR on top of the live icon+goes line.

    python analysis/metar.py      # writes metar.md
"""

import math
import sys
from io import StringIO

import numpy as np
import pandas as pd
import requests
from sklearn.metrics import roc_auc_score

import data
import horizons as H
import models

STATIONS = {"BTV": (44.468, -73.150), "PBG": (44.651, -73.468), "SLK": (44.385, -74.206),
            "OGS": (44.682, -75.466), "MSS": (44.936, -74.846), "ART": (43.992, -76.022)}
COVER = {"CLR": 0, "SKC": 0, "NSC": 0, "FEW": .19, "SCT": .44, "BKN": .75, "OVC": 1, "VV": 1}
CACHE = data.EXPORT / "metar"
CACHE.mkdir(exist_ok=True)


def bearing(lat0, lon0, lat, lon):
    p0, p1, dl = math.radians(lat0), math.radians(lat), math.radians(lon - lon0)
    return math.degrees(math.atan2(math.sin(dl) * math.cos(p1),
                                   math.cos(p0) * math.sin(p1) - math.sin(p0) * math.cos(p1) * math.cos(dl))) % 360


def reports(station, lo, hi):
    path = CACHE / f"{station}.csv"
    if not path.exists():
        resp = requests.get("https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py", timeout=300, params=[
            ("station", station), *[("data", f"sky{k}{i}") for k in "cl" for i in range(1, 5)],
            ("year1", lo.year), ("month1", lo.month), ("day1", lo.day), ("year2", hi.year), ("month2", hi.month),
            ("day2", hi.day), ("tz", "Etc/UTC"), ("format", "onlycomma"), ("latlon", "no"), ("missing", "M"),
            ("trace", "T"), ("direct", "no"), ("report_type", "3"), ("report_type", "4")])
        resp.raise_for_status()
        path.write_text(resp.text)
    m = pd.read_csv(path, na_values="M")
    m["t"] = pd.to_datetime(m.valid, utc=True)
    m = m.dropna(subset=["skyc1"]).set_index("t").sort_index()
    m = m[~m.index.duplicated(keep="last")]
    layers = [[(r[f"skyc{i}"], r[f"skyl{i}"]) for i in range(1, 5) if isinstance(r[f"skyc{i}"], str)]
              for _, r in m.iterrows()]
    return pd.DataFrame({
        "cover": [max([COVER.get(c, 0) for c, _ in l], default=0) for l in layers],
        "ceiling": [min([b for c, b in l if c in ("BKN", "OVC", "VV") and b == b], default=30000) for l in layers],
        "base": [min([b for c, b in l if b == b and COVER.get(c, 0) > 0], default=30000) for l in layers]}, index=m.index)


def add_metar(t):
    lo, hi = min(t.day), max(t.day) + pd.Timedelta(days=1)
    for s in STATIONS:
        r = reports(s, lo, hi)
        i = r.index.get_indexer(t.t, method="pad")
        age = (t.t.values - r.index[i].values) / np.timedelta64(1, "h")
        ok = (i >= 0) & (age <= 2)  # stale reports (station down) count as missing
        for c in r:
            t[f"{s}_{c}"] = np.where(ok, r[c].values[i], np.nan)
    # Stations on the sun's bearing from the camera (within 20 deg), KBTV excluded (it's overhead).
    covs = []
    for cam, az, row in zip(t.camera, t.az, t.itertuples()):
        lat0, lon0, _ = data.LOCATION[cam]
        near = [s for s, (la, lo_) in STATIONS.items()
                if s != "BTV" and abs((bearing(lat0, lon0, la, lo_) - az + 180) % 360 - 180) <= 20]
        v = [getattr(row, f"{s}_cover") for s in near]
        covs.append(np.nanmean(v) if np.isfinite(v).any() else np.nan)
    t["metar_path"] = covs
    t["metar_west"] = t[[f"{s}_cover" for s in STATIONS if s != "BTV"]].mean(axis=1)
    t["metar_ceil"] = t.BTV_ceiling / 30000
    return t


def add_icon(t):
    grids = {c: models.fetch(c, "icon_seamless", None, None) for c in set(models.CENTERS.values())}
    out = {l: [] for l in ("low", "mid", "high", "total")}
    for cam, az, ts in zip(t.camera, t.az, t.t):
        g = grids[models.CENTERS[cam]]
        b = min(models.BEARINGS, key=lambda x: abs(x - az))
        rows = [g[(b, km)].iloc[g[(b, km)].index.get_indexer([ts.floor("min")], method="nearest")[0]] for km in (13, 40, 80)]
        for l in out:
            out[l].append(np.mean([r["cloud_cover" if l == "total" else f"cloud_cover_{l}"] for r in rows]) / 100)
    return t.assign(**{f"icon_{l}": v for l, v in out.items()})


def auc(y, p):
    ok = np.isfinite(p)
    return roc_auc_score(y[ok], p[ok])


def main():
    t = H.build()
    cap = data.captures()
    cap = cap[cap.label.isin(H.HORIZONS)][["camera", "day", "label", "t"]].rename(columns={"label": "horizon"})
    t = t.merge(cap, on=["camera", "day", "horizon"], how="left").dropna(subset=["t"]).reset_index(drop=True)
    t["az"] = [data.sun_time_and_bearing(d, c)[1] for c, d in zip(t.camera, t.day)]
    t = add_metar(add_icon(t))
    t.to_parquet(data.EXPORT / "metar_shots.parquet")
    top = (t.pct >= .75).astype(int)
    goes, icon = ["goes_over", "goes_near", "goes_far", "goes_fan"], ["icon_low", "icon_mid", "icon_high", "icon_total"]
    met = ["BTV_cover", "metar_path", "metar_west"]
    out = [f"# GOES vs ICON, and METAR toward the sunset ({t.groupby(['camera', 'day']).ngroups} sunset camera-days, "
           f"{len(t)} pre shots)\n",
           "## 1. Agreement, all pre shots (Spearman)\n",
           t[goes + met].corrwith(t[icon[0]], method="spearman").rename(icon[0]).to_frame()
           .join([t[goes + met].corrwith(t[c], method="spearman").rename(c) for c in icon[1:]]).round(2).to_markdown(),
           "\n### GOES vs METAR\n",
           pd.DataFrame({m: t[goes].corrwith(t[m], method="spearman") for m in met}).round(2).to_markdown(),
           "\n## 2. Which tracks the outcome: Spearman with the percentile / AUC for a top-25 % day (cloud alone, "
           "lower = better sunset, so AUC is of -cloud)\n"]
    rows = []
    for h, g in t.groupby("horizon"):
        y = (g.pct >= .75).astype(int).values
        for c in goes + icon + met + ["metar_ceil", "icon_weather", "weather"]:
            sign = 1 if c in ("metar_ceil", "icon_weather", "weather") else -1
            rows.append({"horizon": h, "feature": c, "rho": g[c].corr(g.pct, method="spearman"),
                         "AUC": auc(y, sign * g[c].values), "n": int(g[c].notna().sum())})
    r = pd.DataFrame(rows)
    out += ["AUC by horizon:\n", r.pivot(index="feature", columns="horizon", values="AUC").round(3).to_markdown(),
            "\nSpearman by horizon:\n", r.pivot(index="feature", columns="horizon", values="rho").round(3).to_markdown()]

    # 3. LOMO on top of the live line, same rows for every set.
    base = H.SETS["icon+goes"]
    sets = {"icon+goes (live)": base,
            "+ KBTV cover/ceiling": base + ["BTV_cover", "metar_ceil"],
            "+ METAR on-bearing": base + ["metar_path"],
            "+ METAR west mean": base + ["metar_west"],
            "+ KBTV + on-bearing + west": base + ["BTV_cover", "metar_ceil", "metar_path", "metar_west"],
            "+ ICON high": base + ["icon_high"],
            "base + icon + METAR (no GOES)": H.BASE + ["icon_weather", "metar_west", "BTV_cover"]}
    full = t.dropna(subset=sorted({f for fs in sets.values() for f in fs})).reset_index(drop=True)
    comp = []
    for name, feats in sets.items():
        for h in H.HORIZONS:
            g = full[full.horizon == h].copy()
            g["p"] = H.lomo(g, feats)
            comp.append({"features": name, "horizon": h, "AUC": roc_auc_score(g.pct >= .75, g.p),
                         "spearman": g.p.corr(g.pct, method="spearman"), "n": len(g)})
    comp = pd.DataFrame(comp)
    side = comp.pivot_table(index="horizon", columns="features", values="AUC", sort=False)[list(sets)]
    side.loc["mean"] = side.mean()
    out += [f"\n## 3. Leave-one-month-out AUC (top 25 %), {full.groupby('horizon').size().min()}-"
            f"{full.groupby('horizon').size().max()} shots per horizon with every input\n",
            side.round(3).T.to_markdown(),
            "\nSpearman:\n", comp.pivot_table(index="features", columns="horizon", values="spearman", sort=False)
            .loc[list(sets)].round(3).to_markdown(),
            "\nStation coverage (share of shots with a fresh report): "
            + ", ".join(f"K{s} {t[f'{s}_cover'].notna().mean():.0%}" for s in STATIONS)
            + f"; on-bearing station available {t.metar_path.notna().mean():.0%}."]
    text = "\n".join(out)
    (data.ROOT / "analysis" / "metar.md").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
