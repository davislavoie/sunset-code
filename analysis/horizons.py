"""Forecast at every pre shot (2h, 1h, 45m, 30m, 15m, 5m): weather + the HSV scores seen so far.

At each horizon the features are what's known then:
  weather  = clear-path share - 0.5 * RH/100 (ai_judge.predict's simple score, from that capture)
  cur_pct  = this shot's HSV score as a percentile of the camera's past daily-best scores
  max_pct  = the best shot so far today, same scale
Target = the day's best score in the sunset window (15m pre .. 30m post), as a percentile within
the camera. A per-horizon least-squares line (numpy only) maps features -> percentile; the
coefficients go to ai_judge/predict_coefs.json so the NUC needs no sklearn.

    python analysis/horizons.py      # fit, leave-one-month-out backtest, write coefs + horizons.md
"""

import json
import sys

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.metrics import roc_auc_score

import data

sys.path.insert(0, str(data.ROOT))
from ai_judge import predict  # noqa: E402

HORIZONS = ["01_2h_pre", "02_1h_pre", "03_45m_pre", "04_30m_pre", "05_15m_pre", "06_5m_pre"]
BASE = ["weather", "cur_pct", "max_pct"]
# Candidate feature sets; the best (by mean AUC over horizons) goes first in predict_coefs.json,
# with BASE kept as the fallback for shots missing ICON or GOES.
SETS = {"base": BASE,
        "icon": BASE + ["icon_weather"],
        "goes": BASE + ["goes_fan"],
        "icon+goes": BASE + ["icon_weather", "goes_fan"],
        "icon+goes zones": BASE + ["icon_weather", "goes_over", "goes_near", "goes_far"],
        "icon+goes+band": BASE + ["icon_weather", "goes_fan", "horizon_lift"]}
FEATS = BASE
# The vision model's sky read (ai_judge/sky.py) exists only on the 1h/45m/30m/15m shots, so these sets are
# compared and fitted on those horizons alone, on the shots that also have every input of the chosen set above.
SKY = ["sky_gap_thickness", "sky_cloud_cover", "sky_lit", "sky_quality"]
SKY_HORIZONS = HORIZONS[1:5]
SKY_SETS = {"+gap": ["sky_gap_thickness"], "+sky": SKY}
# For the 15m and 5m shots the window target includes shots already seen, so also check against
# only the shots still to come.
AFTER = {"05_15m_pre": data.WINDOW[1:], "06_5m_pre": data.WINDOW[2:]}


def icon_fields(cap):
    """ICON path cloud at 13/40/80 km for each capture, from analysis/models.py's cache (grid bearing
    nearest the sun, at most 10 deg off the exact bearing the live fetch uses)."""
    import models

    out = {f"path{km}_icon_cloud_cover_{l}": [] for km in predict.PATH_KM for l in ("low", "mid")}
    grids = {c: models.fetch(c, "icon_seamless", None, None) for c in set(models.CENTERS.values())}
    for cam, day, t, label in zip(cap.camera, cap.day, cap.t, cap.label):
        g = grids.get(models.CENTERS.get(cam)) if label in HORIZONS else None
        b = min(models.BEARINGS, key=lambda x: abs(x - data.sun_time_and_bearing(day, cam)[1])) if g else None
        for km in predict.PATH_KM:
            h = g[(b, km)] if g else None
            r = h.iloc[h.index.get_indexer([t.floor("min")], method="nearest")[0]] if g else {}
            for l in ("low", "mid"):
                out[f"path{km}_icon_cloud_cover_{l}"].append(r.get(f"cloud_cover_{l}", np.nan) if g else np.nan)
    return cap.assign(**out)


def build():
    cap = data.captures()
    cap = cap[cap.camera.isin(data.SUNSET_CAMS)].reset_index(drop=True)
    cap = icon_fields(cap)
    shots = pd.read_json(data.EXPORT / "goes" / "shots.jsonl", lines=True)
    cap = cap.merge(shots.drop_duplicates(["camera", "time"]), on=["camera", "time"], how="left", suffixes=("", "_cache"))
    for c in [c for c in cap if c.endswith("_cache")]:  # newer exports carry goes_* from Influx: fill gaps from the cache
        cap[c[:-6]] = cap[c[:-6]].fillna(cap.pop(c))
    d = data.days(cap)
    best = {(cam, day): y for cam, day, y in d[["camera", "day", "y"]].itertuples(index=False)}
    ok = cap[~cap.excluded]
    rows = []
    for (cam, day), g in cap.groupby(["camera", "day"]):
        # As live: only earlier days are history.
        history = sorted(y for (c, dd), y in best.items() if c == cam and dd < day)
        if len(history) < predict.MIN_DAYS:
            continue
        g = g.set_index("label")
        seen = []
        for h in HORIZONS:
            if h not in g.index:
                continue
            r = g.loc[h]
            shot = 0 if r.excluded else r.score  # as live: shots that can't be the best count as 0
            seen.append(shot)
            point = {k: (None if v != v else v) for k, v in r.items()}
            x = predict.features(point, predict.percentile(history, shot), predict.percentile(history, max(seen)))
            rows.append({"camera": cam, "day": day, "horizon": h, **x})
    t = pd.DataFrame(rows).merge(d[["camera", "day", "y", "month"]], on=["camera", "day"])
    t["pct"] = t.groupby(["camera", "horizon"]).y.rank(pct=True)
    for h, labels in AFTER.items():
        rest = ok[ok.label.isin(labels)].groupby(["camera", "day"]).score.max().rename(f"rest_{h}")
        t = t.join(rest, on=["camera", "day"])
    t["rest"] = np.select([t.horizon == h for h in AFTER], [t[f"rest_{h}"] for h in AFTER], t.y)
    t["rest_pct"] = t.groupby(["camera", "horizon"]).rest.rank(pct=True)
    return t.dropna(subset=["weather"])


def fit(df, target="pct", feats=FEATS):
    X = np.c_[np.ones(len(df)), df[feats].values]
    return np.linalg.lstsq(X, df[target].values, rcond=None)[0]


def apply(coef, df, feats=FEATS):
    return np.clip(np.c_[np.ones(len(df)), df[feats].values] @ coef, 0, 1)


def lomo(df, feats=FEATS):
    pred = pd.Series(np.nan, index=df.index)
    for m in df.month.unique():
        tr, te = df.month != m, df.month == m
        pred[te] = apply(fit(df[tr], feats=feats), df[te], feats)
    return pred


def metrics(g, target="pct"):
    top10 = g[target] >= 0.9
    bang = g.call == "banger"
    return {"days": len(g), "spearman": spearmanr(g.p, g[target])[0],
            "AUC top-25%": roc_auc_score(g[target] >= .75, g.p),
            "MAE (percentile pts)": 100 * (g.p - g[target]).abs().mean(),
            "banger precision (top-10%)": top10[bang].mean() if bang.any() else np.nan,
            "banger recall": bang[top10].mean(),
            "poor calls on top-25% days": (g[g[target] >= .75].call == "poor").mean()}


def main():
    t = build()
    t = t[t.camera.isin(data.SUNSET_CAMS)].reset_index(drop=True)
    # Compare feature sets on the shots that have every input (ICON + GOES), same rows for all.
    full = t.dropna(subset=sorted({f for fs in SETS.values() for f in fs})).reset_index(drop=True)
    compare = []
    for name, feats in SETS.items():
        for h in HORIZONS:
            g = full[full.horizon == h].copy()
            g["p"] = lomo(g, feats)
            g["call"] = [predict.call(p) for p in g.p]
            compare.append({"features": name, "horizon": h, **metrics(g)})
    compare = pd.DataFrame(compare)
    best = compare.groupby("features", sort=False)["AUC top-25%"].mean().idxmax()
    sky_sets = {best: SETS[best], **{best + k: SETS[best] + v for k, v in SKY_SETS.items()}}
    sky_full = t[t.horizon.isin(SKY_HORIZONS)].dropna(subset=SETS[best] + SKY).reset_index(drop=True)
    sky_compare = []
    for name, feats in sky_sets.items():
        for h in SKY_HORIZONS:
            g = sky_full[sky_full.horizon == h].copy()
            g["p"] = lomo(g, feats)
            g["call"] = [predict.call(p) for p in g.p]
            sky_compare.append({"features": name, "horizon": h, **metrics(g)})
    sky_compare = pd.DataFrame(sky_compare)
    sky_best = sky_compare.groupby("features", sort=False)["AUC top-25%"].mean().idxmax()
    models, rows, per_cam = [], [], []
    if sky_best != best:  # first in line on the sky horizons only; predict.forecast skips it elsewhere
        models.append({"name": sky_best, "features": sky_sets[sky_best],
                       "coefs": {h: [round(float(c), 4) for c in fit(sky_full[sky_full.horizon == h], feats=sky_sets[sky_best])]
                                 for h in SKY_HORIZONS}})
    for name in dict.fromkeys([best, "icon+goes", "base"]):  # fallbacks for shots missing an input
        feats, src = SETS[name], (full if name != "base" else t)
        coefs = {}
        for h in HORIZONS:
            g = src[src.horizon == h].copy()
            coefs[h] = [round(float(c), 4) for c in fit(g, feats=feats)]
            if name == best:
                g["p"] = lomo(g, feats)
                g["call"] = [predict.call(p) for p in g.p]
                rows.append({"horizon": h, **metrics(g)})
                if h in AFTER:
                    rows.append({"horizon": h + " (vs shots still to come)", **metrics(g.assign(pct=g.rest_pct), "pct")})
                for cam, gg in g.groupby("camera"):
                    per_cam.append({"horizon": h, "camera": cam, **metrics(gg)})
        models.append({"name": name, "features": feats, "coefs": coefs})
    (data.ROOT / "ai_judge" / "predict_coefs.json").write_text(json.dumps({"models": models}, indent=1) + "\n")
    side = compare.pivot_table(index="horizon", columns="features", values="AUC top-25%", sort=False)[list(SETS)]
    text = (f"# Forecast at each pre shot (sunset cameras, leave-one-month-out)\n\n"
            "Target: the day's best score from 15m pre to 30m post, as a percentile within the camera.\n\n"
            f"## Feature sets compared (AUC top-25 %, {full.groupby('horizon').size().min()}-"
            f"{full.groupby('horizon').size().max()} shots per horizon that have ICON and GOES)\n\n"
            + side.round(3).to_markdown()
            + "\n\n## Before (base) vs after (" + best + "), same shots\n\n"
            + compare[compare.features.isin(["base", best])].round(3).to_markdown(index=False)
            + f"\n\n## Chosen set ({best}): all metrics\n\n" + pd.DataFrame(rows).round(3).to_markdown(index=False)
            + f"\n\n## Vision sky read on top of {best} (1h-15m shots that have it, "
            f"{sky_full.groupby('horizon').size().min()}-{sky_full.groupby('horizon').size().max()} per horizon; "
            + ", ".join(f"{c} {n}" for c, n in sky_full[sky_full.horizon == SKY_HORIZONS[0]].camera.value_counts().items())
            + f"); {'using ' + sky_best if sky_best != best else 'not used: no gain'}\n\n"
            + sky_compare.round(3).to_markdown(index=False)
            + "\n\n## Per camera\n\n" + pd.DataFrame(per_cam).round(3).to_markdown(index=False)
            + "\n\n## Coefficients (intercept, then the features in order)\n\n"
            + "\n".join(f"- {m['name']} {m['features']}: " + "; ".join(f"{h} {c}" for h, c in m["coefs"].items()) for m in models))
    (data.ROOT / "analysis" / "horizons.md").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
