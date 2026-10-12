"""Can a model that bends beat the live straight line? (follows metar.py / photo_truth.py)

The live forecast (horizons.py, icon+goes) is one least-squares line per horizon: more cloud = worse.
A great sunset is "some cloud, lit from below through a clear gap toward the sun", which a line
can't express. Here, on the same shots, leave-one-month-out:
  - the live line
  - the line + sky-shape features:
      lit_canvas  = goes_over * (1 - goes_far)    cloud overhead, clear toward the sun
      icon_canvas = (icon_mid + icon_high) * (1 - icon_low)    cloud up high, no low deck
      ceil        = KBTV ceiling / 30000 ft (1 = no ceiling below 12,000 ft)
      lowdeck     = KBTV cover * (ceiling < 5,000 ft)
      cover_mid   = goes_fan * (1 - goes_fan) * 4   peaks at half cover
  - gradient-boosted trees (shallow, sklearn), per horizon and pooled over horizons
Reads analysis_export/metar_shots.parquet (run metar.py first).

    python analysis/nonlinear.py      # writes nonlinear.md
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import roc_auc_score

import data
import horizons as H

LIVE = H.SETS["icon+goes"]
SHAPE = ["lit_canvas", "icon_canvas", "ceil", "lowdeck", "cover_mid"]
RAW = ["goes_over", "goes_near", "goes_far", "icon_low", "icon_mid", "icon_high", "BTV_cover", "metar_west"]


def gbm():
    return HistGradientBoostingRegressor(max_depth=3, learning_rate=0.05, max_iter=200, min_samples_leaf=20,
                                         l2_regularization=1.0, random_state=0)


def lomo_gbm(df, feats):
    pred = pd.Series(np.nan, index=df.index)
    for m in df.month.unique():
        tr, te = df.month != m, df.month == m
        pred[te] = np.clip(gbm().fit(df.loc[tr, feats], df.loc[tr, "pct"]).predict(df.loc[te, feats]), 0, 1)
    return pred


def main():
    t = pd.read_parquet(data.EXPORT / "metar_shots.parquet")
    t["lit_canvas"] = t.goes_over * (1 - t.goes_far)
    t["icon_canvas"] = (t.icon_mid + t.icon_high) / 2 * (1 - t.icon_low)
    t["ceil"] = t.BTV_ceiling / 30000
    t["lowdeck"] = t.BTV_cover * (t.BTV_ceiling < 5000)
    t["cover_mid"] = t.goes_fan * (1 - t.goes_fan) * 4
    t["h"] = t.horizon.map({h: i for i, h in enumerate(H.HORIZONS)})
    t = t.dropna(subset=LIVE + SHAPE + RAW).reset_index(drop=True)

    preds = {"live line (icon+goes)": {}, "line + sky shape": {}, "trees, live inputs": {},
             "trees, live + sky shape + raw cloud": {}}
    for h in H.HORIZONS:
        g = t[t.horizon == h]
        preds["live line (icon+goes)"][h] = H.lomo(g, LIVE)
        preds["line + sky shape"][h] = H.lomo(g, LIVE + SHAPE)
        preds["trees, live inputs"][h] = lomo_gbm(g, LIVE)
        preds["trees, live + sky shape + raw cloud"][h] = lomo_gbm(g, LIVE + SHAPE + RAW)
    # Pooled: one tree model over all horizons (6x the rows), horizon as an input.
    pooled = lomo_gbm(t, ["h"] + LIVE + SHAPE + RAW)
    preds["trees pooled over horizons"] = {h: pooled[t.horizon == h] for h in H.HORIZONS}
    # Blend: average of the live line and the pooled trees.
    preds["blend: live line + pooled trees"] = {h: (preds["live line (icon+goes)"][h] + pooled[t.horizon == h]) / 2
                                                for h in H.HORIZONS}

    rows = []
    for name, ph in preds.items():
        for h, p in ph.items():
            g = t.loc[p.index]
            rows.append({"model": name, "horizon": h, "AUC": roc_auc_score(g.pct >= .75, p),
                         "AUC top-10%": roc_auc_score(g.pct >= .9, p),
                         "spearman": p.corr(g.pct, method="spearman"), "MAE": 100 * (p - g.pct).abs().mean()})
    r = pd.DataFrame(rows)
    out = [f"# A model that bends vs the live line ({len(t)} shots, {t.groupby(['camera', 'day']).ngroups} camera-days, "
           f"leave-one-month-out, same rows for every model)\n"]
    for metric in ("AUC", "AUC top-10%", "spearman", "MAE"):
        side = r.pivot_table(index="model", columns="horizon", values=metric, sort=False)
        side["mean"] = side.mean(axis=1)
        out += [f"\n## {metric}" + (" (top 25 %)" if metric == "AUC" else "") + (" (percentile pts, lower is better)" if metric == "MAE" else "")
                + "\n", side.round(3).to_markdown()]
    # Which inputs the pooled trees lean on (permutation importance on the full fit, AUC drop).
    from sklearn.inspection import permutation_importance
    feats = ["h"] + LIVE + SHAPE + RAW
    m = gbm().fit(t[feats], t.pct)
    imp = permutation_importance(m, t[feats], t.pct, n_repeats=5, random_state=0)
    out += ["\n## What the pooled trees use (permutation importance, drop in R2, in-sample)\n",
            pd.Series(imp.importances_mean, feats).sort_values(ascending=False).round(4).to_frame("importance").to_markdown()]
    # Is "some cloud" better than none? Outcome by GOES fan cover band, and by lit_canvas.
    t["fan_band"] = pd.cut(t.goes_fan, [-.01, .1, .3, .5, .7, .9, 1], labels=["0-10", "10-30", "30-50", "50-70", "70-90", "90-100"])
    t["ceil_band"] = pd.cut(t.BTV_ceiling, [0, 3000, 6000, 12000, 30001], labels=["<3k", "3-6k", "6-12k", "none <12k"])
    h1 = t[t.horizon == "02_1h_pre"]
    out += ["\n## Outcome by GOES fan cloud, 1 h pre (mean percentile, share of top-25 % days)\n",
            h1.groupby("fan_band", observed=True).agg(n=("pct", "size"), mean_pct=("pct", "mean"),
                                                     top25=("pct", lambda x: (x >= .75).mean())).round(2).to_markdown(),
            "\n## Outcome by KBTV ceiling, 1 h pre\n",
            h1.groupby("ceil_band", observed=True).agg(n=("pct", "size"), mean_pct=("pct", "mean"),
                                                      top25=("pct", lambda x: (x >= .75).mean())).round(2).to_markdown()]
    text = "\n".join(out)
    (data.ROOT / "analysis" / "nonlinear.md").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
