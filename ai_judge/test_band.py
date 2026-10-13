"""Checks for the horizon light band. Run: python -m unittest ai_judge.test_band"""

import io
import unittest

import numpy as np
from PIL import Image

from ai_judge import band, predict


def jpeg(a):
    buf = io.BytesIO()
    Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).save(buf, format="JPEG", quality=95)
    return buf.getvalue()


def scene(strip):
    """1280x720: grey sky, optionally glowing toward a dark shoreline at row 400 (fading up, as a real glow does), then water."""
    a = np.full((720, 1280, 3), 120.0)
    if strip:
        a[340:400] += np.linspace(0, 90, 60)[:, None, None]
    a[400:420] = 30  # far shore, edge to edge
    a[420:] = 90
    return jpeg(a)


class Band(unittest.TestCase):
    def test_bright_strip_above_the_horizon_lifts(self):
        self.assertGreater(band.horizon_lift(scene(strip=True)), 0.1)
        self.assertLess(abs(band.horizon_lift(scene(strip=False))), 0.03)

    def test_missing_photo_sentinel_is_not_a_forecast_input(self):
        self.assertIsNone(predict.features({"horizon_lift": band.GONE}, 0.5, 0.5)["horizon_lift"])
        self.assertEqual(predict.features({"horizon_lift": 0.1}, 0.5, 0.5)["horizon_lift"], 0.1)


if __name__ == "__main__":
    unittest.main()
