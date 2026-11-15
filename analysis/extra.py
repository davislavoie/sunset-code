"""Does a new per-shot input help the forecast? The shared test for trend.py, thickness.py and advect.py.

    t = extra.table()                       # one row per pre shot: camera, day, horizon, the live inputs, pct (target)
    t = t.merge(my_features, on=["camera", "day", "horizon"], how="left")
    print(extra.report(t, {"+trend": ["goes_far_trend"]}))

Each candidate set is the live line (icon+goes+band, and with the sky read on the 1h-15m shots) plus the new
inputs, fitted leave-one-month-out on the shots that have every input, so all sets see the same rows.
"shuffled" is the same fit with the new inputs shuffled between days: what a useless input scores by chance.
A gain smaller than the shuffled spread is noise.
"""

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.metrics import roc_auc_score

import horizons
from horizons import HORIZONS, SETS, SKY, SKY_HORIZONS, lomo

LIVE = SETS["icon+goes+band"]
BASES = {"live": (LIVE, HORIZONS), "live+sky": (LIVE + SKY, SKY_HORIZONS)}
SHUFFLES = 30


def table():
    return horizons.build()


def score(g, feats):
    p = lomo(g, feats)
    return {"spearman": spearmanr(p, g.pct)[0], "AUC top-25%": roc_auc_score(g.pct >= .75, p),
            "AUC top-10%": roc_auc_score(g.pct >= .9, p), "MAE": 100 * (p - g.pct).abs().mean()}


def evaluate(t, extras):
    """One row per (base, horizon, candidate set): its scores, the gain in AUC top-25% over the base, and the
    95th percentile of that gain with the new inputs shuffled."""
    new = sorted({f for fs in extras.values() for f in fs})
    rng, out = np.random.default_rng(0), []
    for base_name, (base, hs) in BASES.items():
        rows = t.dropna(subset=base + new)
        for h in hs:
            g = rows[rows.horizon == h].reset_index(drop=True)
            if len(g) < 100:
                continue
            ref = score(g, base)
            out.append({"set": base_name, "horizon": h, "n": len(g), **ref})
            for name, feats in extras.items():
                got = score(g, base + feats)
                null = []
                for _ in range(SHUFFLES):
                    s = g.copy()
                    s[feats] = s[feats].values[rng.permutation(len(s))]
                    null.append(score(s, base + feats)["AUC top-25%"] - ref["AUC top-25%"])
                out.append({"set": base_name + name, "horizon": h, "n": len(g), **got,
                            "AUC gain": got["AUC top-25%"] - ref["AUC top-25%"], "shuffled 95%": np.quantile(null, .95)})
    return pd.DataFrame(out)


def report(t, extras):
    """Markdown: the full table, then each set's mean gain over the horizons."""
    e = evaluate(t, extras)
    gains = e.dropna(subset=["AUC gain"]).groupby("set", sort=False).agg(
        horizons=("horizon", "size"), mean_gain=("AUC gain", "mean"), mean_shuffled_95=("shuffled 95%", "mean"),
        beats_shuffle=("AUC gain", lambda s: int((s > e.loc[s.index, "shuffled 95%"]).sum())))
    return e.round(3).to_markdown(index=False) + "\n\n### Mean gain in AUC top-25%\n\n" + gains.round(3).to_markdown()


if __name__ == "__main__":
    # Self-check: an input the line already has adds nothing; the answer itself adds a lot.
    t = table()
    e = evaluate(t.assign(copy=t.goes_fan, answer=t.pct), {"+copy": ["copy"], "+answer": ["answer"]})
    gain = e.groupby("set")["AUC gain"].mean()
    assert abs(gain["live+copy"]) < 1e-6 and gain["live+answer"] > 0.1, gain
    print(report(t.assign(noise=np.random.default_rng(1).random(len(t))), {"+noise": ["noise"]}))
