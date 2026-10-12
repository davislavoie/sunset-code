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
FEATS = ["weather", "cur_pct", "max_pct"]
# For the 15m and 5m shots the window target includes shots already seen, so also check against
# only the shots still to come.
AFTER = {"05_15m_pre": data.WINDOW[1:], "06_5m_pre": data.WINDOW[2:]}


def build():
    cap = data.captures()
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
            w = predict.weather_raw({k: (None if v != v else v) for k, v in r.items()})
            rows.append({"camera": cam, "day": day, "horizon": h, "weather": w,
                         "cur_pct": predict.percentile(history, shot),
                         "max_pct": predict.percentile(history, max(seen))})
    t = pd.DataFrame(rows).merge(d[["camera", "day", "y", "month"]], on=["camera", "day"])
    t["pct"] = t.groupby(["camera", "horizon"]).y.rank(pct=True)
    for h, labels in AFTER.items():
        rest = ok[ok.label.isin(labels)].groupby(["camera", "day"]).score.max().rename(f"rest_{h}")
        t = t.join(rest, on=["camera", "day"])
    t["rest"] = np.select([t.horizon == h for h in AFTER], [t[f"rest_{h}"] for h in AFTER], t.y)
    t["rest_pct"] = t.groupby(["camera", "horizon"]).rest.rank(pct=True)
    return t.dropna(subset=["weather"])


def fit(df, target="pct"):
    X = np.c_[np.ones(len(df)), df[FEATS].values]
    return np.linalg.lstsq(X, df[target].values, rcond=None)[0]


def apply(coef, df):
    return np.clip(np.c_[np.ones(len(df)), df[FEATS].values] @ coef, 0, 1)


def lomo(df):
    pred = pd.Series(np.nan, index=df.index)
    for m in df.month.unique():
        tr, te = df.month != m, df.month == m
        pred[te] = apply(fit(df[tr]), df[te])
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
    coefs, rows, per_cam = {}, [], []
    for h in HORIZONS:
        g = t[t.horizon == h].copy()
        g["p"] = lomo(g)
        g["call"] = [predict.call(p) for p in g.p]
        rows.append({"horizon": h, **metrics(g)})
        if h in AFTER:
            rows.append({"horizon": h + " (vs shots still to come)", **metrics(g.assign(pct=g.rest_pct), "pct")})
        for cam, gg in g.groupby("camera"):
            per_cam.append({"horizon": h, "camera": cam, **metrics(gg)})
        coefs[h] = [round(float(c), 4) for c in fit(g)]
    (data.ROOT / "ai_judge" / "predict_coefs.json").write_text(json.dumps(
        {"features": ["intercept"] + FEATS, "coefs": coefs}, indent=1) + "\n")
    res = pd.DataFrame(rows)
    text = ("# Forecast at each pre shot (sunset cameras, leave-one-month-out)\n\n"
            "Target: the day's best score from 15m pre to 30m post, as a percentile within the camera.\n\n"
            + res.round(3).to_markdown(index=False)
            + "\n\n## Per camera\n\n" + pd.DataFrame(per_cam).round(3).to_markdown(index=False)
            + "\n\n## Coefficients (intercept, weather, cur_pct, max_pct)\n\n"
            + "\n".join(f"- {h}: {c}" for h, c in coefs.items()))
    (data.ROOT / "analysis" / "horizons.md").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
