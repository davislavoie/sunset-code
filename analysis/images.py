"""Cheap image features from the pre-sunset thumbnails (analysis_export/thumbs/<camera>/<date>_<label>.jpg).

Computed on the top half of the frame (mostly sky on these cameras):
  bright  mean V          sat    mean S           blue  share of blue-hue (180-260 deg) pixels with S>0.15
  gray    share of low-saturation mid-bright pixels (S<0.12, 0.25<V<0.85): grey cloud
  edges   mean gradient magnitude of V: cloud texture / structure
  warm    share of red-orange-pink-magenta (H<50 or H>290) pixels with S>0.25
"""

from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

import data

PRE = {"01_2h_pre": "i2h", "02_1h_pre": "i1h", "04_30m_pre": "i30", "05_15m_pre": "i15"}


def features(path):
    img = Image.open(path).convert("RGB")
    a = np.asarray(img.convert("HSV"), dtype=np.float32)[: img.height // 2] / 255
    h, s, v = a[..., 0] * 360, a[..., 1], a[..., 2]
    gy, gx = np.gradient(v)
    return {
        "bright": v.mean(), "sat": s.mean(),
        "blue": ((h > 180) & (h < 260) & (s > 0.15)).mean(),
        "gray": ((s < 0.12) & (v > 0.25) & (v < 0.85)).mean(),
        "edges": np.hypot(gx, gy).mean(),
        "warm": (((h < 50) | (h > 290)) & (s > 0.25) & (v > 0.2)).mean(),
    }


def table():
    out = data.EXPORT / "image_features.parquet"
    if out.exists():
        return pd.read_parquet(out)
    rows = []
    for cam_dir in (data.EXPORT / "thumbs").iterdir():
        for p in cam_dir.glob("*.jpg"):
            day, label = p.stem[:10], p.stem[11:]
            if label in PRE:
                rows.append({"camera": cam_dir.name, "day": pd.Timestamp(day).date(), "label": label, **features(p)})
    long = pd.DataFrame(rows)
    wide = long.pivot_table(index=["camera", "day"], columns="label").reset_index()
    wide.columns = [f"{f}@{PRE[l]}" if l else f for f, l in wide.columns]
    wide.to_parquet(out)
    return wide


if __name__ == "__main__":
    t = table()
    print(t.shape)
    print(t.describe().T.round(3).head(12))
