"""Checks for the simple sunset forecast. Run: python -m unittest ai_judge.test_predict"""

import unittest
from unittest import mock

from ai_judge import predict


def capture(low=(0, 0, 0), mid=(0, 0, 0), rh=50, label="02_1h_pre", **extra):
    p = {"time": "2026-09-01T22:30:00Z", "camera": "btv_echo_cam", "label": label, "relative_humidity_2m": rh, **extra}
    for km, l, m in zip(predict.PATH_KM, low, mid):
        p[f"path{km}_cloud_cover_low"], p[f"path{km}_cloud_cover_mid"] = l, m
    return p


class SimpleScoreTests(unittest.TestCase):
    def test_clear_dry_path_is_good(self):
        self.assertEqual(predict.simple_score(capture(rh=40)), (86.7, "good"))

    def test_low_cloud_everywhere_is_poor(self):
        self.assertEqual(predict.simple_score(capture(low=(90, 80, 100), rh=90)), (3.3, "poor"))

    def test_mid_cloud_counts_against_a_point(self):
        score, cls = predict.simple_score(capture(mid=(50, 0, 0), rh=40))
        self.assertEqual(cls, "maybe")
        self.assertAlmostEqual(score, 64.4)

    def test_no_weather_yet_gives_none(self):
        self.assertIsNone(predict.simple_score({"label": "02_1h_pre", "relative_humidity_2m": 50}))
        self.assertIsNone(predict.simple_score(capture(rh=None)))


class FillTests(unittest.TestCase):
    def test_writes_only_pre_captures_with_weather_and_no_forecast(self):
        points = [capture(label="01_2h_pre"), capture(label="02_1h_pre", predicted_score=50.0),
                  capture(label="07_sunset"), {"time": "t", "camera": "c", "label": "01_2h_pre"}]
        client = mock.Mock()
        with mock.patch.object(predict.store, "captures", return_value=points):
            self.assertEqual(predict.fill(client, "btv_echo_cam"), 1)
        (written,), _ = client.write_points.call_args
        self.assertEqual(written[0]["tags"]["label"], "01_2h_pre")
        self.assertEqual(set(written[0]["fields"]), {"predicted_score", "predicted_class"})


if __name__ == "__main__":
    unittest.main()
