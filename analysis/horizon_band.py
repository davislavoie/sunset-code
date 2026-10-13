"""Light band just above the horizon vs the sky higher up, on the 1h/30m-pre thumbs.

Per thumb: horizon from horizon_gap.horizon (per frame, so camera drift is handled); band = the 8 % of sky
just above it; lift = band brightness minus the sky 15-60 % from the top; lift_max = the best of 8 column
slices (where the sun sets); warm = share of red/orange/pink saturated pixels in the band.

    cd analysis && python horizon_band.py > horizon_band.md
"""
import sys; sys.dont_write_bytecode = True
import numpy as np, pandas as pd
from PIL import Image
from scipy.stats import spearmanr
import data, horizon_gap as hg

rows = []
for cam in data.SUNSET_CAMS:
    for label in ("02_1h_pre", "04_30m_pre"):
        for p in sorted((data.EXPORT / "thumbs" / cam).glob(f"*_{label}.jpg")):
            rgb, v = hg.load(p)
            gy, gx = np.gradient(v)
            h = hg.horizon(v, np.hypot(gx, gy) > hg.TEX)
            sat = np.asarray(Image.open(p).convert("HSV"), dtype=float)
            hue, s = sat[..., 0] * 180 / 255, sat[..., 1] / 255
            b0, b1 = max(0, h - int(.08 * h) - 3), h - 3          # band: just above the horizon
            u0, u1 = int(.15 * h), int(.6 * h)                   # sky well above it
            band, up = v[b0:b1], v[u0:u1]
            chunks = np.array_split(np.arange(v.shape[1]), 8)
            lifts = [band[:, c].mean() - up[:, c].mean() for c in chunks]
            warm = ((hue[b0:b1] < 25) | (hue[b0:b1] > 160)) & (s[b0:b1] > .2)
            rows.append({"camera": cam, "day": pd.Timestamp(p.name[:10]).date(), "label": label,
                         "lift": band.mean() - up.mean(), "lift_max": max(lifts), "ratio": band.mean() / max(up.mean(), .02),
                         "warm": warm.mean(), "hz": h / v.shape[0]})
f = pd.DataFrame(rows).pivot_table(index=["camera", "day"], columns="label", values=["lift", "lift_max", "ratio", "warm"])
f.columns = [f"{a}@{'h1' if b == '02_1h_pre' else 'm30'}" for a, b in f.columns]
f = f.reset_index()
d = data.days()[["camera", "day", "y"]]
d["pct"] = d.groupby("camera").y.rank(pct=True)
t = d.merge(f, on=["camera", "day"])
m = pd.read_parquet(data.EXPORT / "metar_shots.parquet")
m = m[m.horizon == "02_1h_pre"][["camera", "day", "goes_near", "goes_far"]]
t = t.merge(m, on=["camera", "day"], how="left")
mine = pd.read_parquet(data.EXPORT / "my_rank_days.parquet").assign(day=lambda x: pd.to_datetime(x.date).dt.date)
t = t.merge(mine[["day", "score"]].assign(camera="btv_echo_cam").rename(columns={"score": "mine"}), on=["camera", "day"], how="left")
feats = [c for c in f.columns if "@" in c]
out = []
for c in feats:
    cloudy = t[t.goes_near >= .5]
    out.append({"feature": c, "all days": spearmanr(t[c], t.pct, nan_policy="omit")[0],
                "cloudy toward sun (goes_near>=.5)": spearmanr(cloudy[c], cloudy.pct, nan_policy="omit")[0],
                "your score (btv)": spearmanr(t[c], t.mine, nan_policy="omit")[0]})
print(len(t), "camera-days;", t.goes_near.notna().sum(), "with GOES;", t.mine.notna().sum(), "ranked")
print(pd.DataFrame(out).round(3).to_markdown(index=False))
# the satellite version of a band: cloudy near, clear far
t["sat_gap"] = t.goes_near - t.goes_far
c = t[t.goes_near >= .5]
print("sat gap (near - far), cloudy days:", round(spearmanr(c.sat_gap, c.pct, nan_policy="omit")[0], 3), len(c))
print("photo lift_max@h1 vs satellite gap:", round(spearmanr(t["lift_max@h1"], t.sat_gap, nan_policy="omit")[0], 3))

import horizons
from sklearn.metrics import roc_auc_score
b = horizons.build()
live = horizons.SETS["icon+goes"]
res = []
for hz, tag in (("02_1h_pre", "h1"), ("04_30m_pre", "m30")):
    g = b[b.horizon == hz].merge(f, on=["camera", "day"]).dropna(subset=live + [f"lift@{tag}", f"warm@{tag}"]).reset_index(drop=True)
    for name, fs in (("live", live), ("live + lift", live + [f"lift@{tag}"]), ("live + lift + warm", live + [f"lift@{tag}", f"warm@{tag}"])):
        p = horizons.lomo(g, fs)
        res.append({"shot": hz, "features": name, "n": len(g), "spearman": spearmanr(p, g.pct)[0], "AUC top25": roc_auc_score(g.pct >= .75, p)})
    print(hz, "lift vs cur_pct:", round(spearmanr(g[f"lift@{tag}"], g.cur_pct)[0], 3), " vs goes_fan:", round(spearmanr(g[f"lift@{tag}"], g.goes_fan)[0], 3))
print(pd.DataFrame(res).round(3).to_markdown(index=False))
