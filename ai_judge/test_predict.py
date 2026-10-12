"""Checks for the sunset forecast. Run: python -m unittest ai_judge.test_predict"""

import unittest
from datetime import date, timedelta
from unittest import mock

from ai_judge import predict


def capture(day, label, score=5.0, low=(0, 0, 0), mid=(0, 0, 0), rh=50, **extra):
    # 22:00 UTC = early evening in Vermont, the same local date
    p = {"time": f"{day}T22:00:00Z", "camera": "btv_echo_cam", "label": label, "score": score,
         "relative_humidity_2m": rh, **extra}
    for km, l, m in zip(predict.PATH_KM, low, mid):
        p[f"path{km}_cloud_cover_low"], p[f"path{km}_cloud_cover_mid"] = l, m
    return p


class PieceTests(unittest.TestCase):
    def test_weather_raw(self):
        self.assertAlmostEqual(predict.weather_raw(capture("2026-09-01", "01_2h_pre", rh=40)), 0.8)
        self.assertAlmostEqual(predict.weather_raw(capture("2026-09-01", "01_2h_pre", low=(90, 0, 0), rh=40)), 2 / 3 - 0.2)
        self.assertAlmostEqual(predict.weather_raw(capture("2026-09-01", "01_2h_pre", mid=(50, 50, 50), rh=100)), -0.5)
        self.assertIsNone(predict.weather_raw({"relative_humidity_2m": 50}))
        self.assertIsNone(predict.weather_raw(capture("2026-09-01", "01_2h_pre", rh=None)))

    def test_percentile_and_calls(self):
        self.assertEqual(predict.percentile([1, 2, 3, 4], 2.5), 0.5)
        self.assertEqual(predict.percentile([1, 2, 3, 4], None), 0)
        self.assertEqual([predict.call(p) for p in (0.1, 0.5, 0.7, 0.9)], ["poor", "maybe", "good", "banger"])

    def test_every_horizon_has_coefficients_and_more_clear_sky_is_never_worse(self):
        for h in predict.HORIZONS:
            self.assertGreaterEqual(predict.forecast(h, 0.8, 0.5, 0.5), predict.forecast(h, -0.5, 0.5, 0.5), h)

    def test_old_labels_with_a_date_suffix_still_match(self):
        self.assertEqual(predict.label_of({"label": "02_1h_pre_05-16-2025.jpg"}), "02_1h_pre")
        self.assertIsNone(predict.label_of({"label": "07_sunset"}))


class FillTests(unittest.TestCase):
    def history(self, n=12):
        start = date(2026, 8, 1)
        return [capture(start + timedelta(days=i), "07_sunset", score=float(i)) for i in range(n)]

    def run_fill(self, points):
        client = mock.Mock()
        with mock.patch.object(predict.store, "captures", return_value=points):
            n = predict.fill(client, "btv_echo_cam")
        return n, ([w for call in client.write_points.call_args_list for w in call.args[0]] if n else [])

    def test_writes_each_pre_shot_with_weather_using_only_earlier_days(self):
        today = [capture("2026-09-01", "01_2h_pre", score=1.0), capture("2026-09-01", "06_5m_pre", score=50.0),
                 capture("2026-09-01", "07_sunset", score=60.0), capture("2026-09-01", "02_1h_pre", rh=None)]
        n, written = self.run_fill(self.history() + today)
        self.assertEqual(n, 2)
        by_label = {w["tags"]["label"]: w["fields"] for w in written}
        self.assertEqual(set(by_label), {"01_2h_pre", "06_5m_pre"})
        self.assertEqual(set(by_label["06_5m_pre"]), {"predicted_pct", "predicted_score", "predicted_call"})
        # The 5m shot beat every past day, so it should be the more hopeful forecast.
        self.assertGreater(by_label["06_5m_pre"]["predicted_pct"], by_label["01_2h_pre"]["predicted_pct"])
        # Scores come from past daily bests (0..11): today's own 60 is not history.
        self.assertLessEqual(by_label["06_5m_pre"]["predicted_score"], 11)

    def test_skips_until_there_is_enough_history_and_already_forecast_shots(self):
        n, _ = self.run_fill(self.history(5) + [capture("2026-09-01", "01_2h_pre")])
        self.assertEqual(n, 0)
        n, _ = self.run_fill(self.history() + [capture("2026-09-01", "01_2h_pre", predicted_pct=40.0)])
        self.assertEqual(n, 0)


if __name__ == "__main__":
    unittest.main()
