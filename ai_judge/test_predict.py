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
        clear = {"weather": 0.8, "icon_weather": 0.8, "cur_pct": .5, "max_pct": .5,
                 "goes_over": 0, "goes_near": 0, "goes_far": 0, "goes_fan": 0}
        grey = dict(clear, weather=-0.5, icon_weather=-0.5, goes_over=1, goes_near=1, goes_far=1, goes_fan=1)
        for m in predict.MODELS:  # the vision sky read only exists on the 1h-15m shots
            want = predict.HORIZONS[1:5] if any(f.startswith("sky_") for f in m["features"]) else predict.HORIZONS
            self.assertEqual(set(m["coefs"]), set(want), m["name"])
        for h in predict.HORIZONS:
            for drop in ([], [k for k in clear if k.startswith(("goes", "icon"))]):  # best set, then the fallback
                c, g = ({k: v for k, v in x.items() if k not in drop} for x in (clear, grey))
                self.assertGreaterEqual(predict.forecast(h, c)[0], predict.forecast(h, g)[0], (h, drop))

    def test_uses_the_best_set_it_has_inputs_for(self):
        x = {"weather": 0.5, "cur_pct": .5, "max_pct": .5}
        self.assertEqual(predict.forecast("02_1h_pre", x)[1], "base")
        full = dict(x, icon_weather=0.5, goes_over=0.2, goes_near=0.2, goes_far=0.2, goes_fan=0.2, horizon_lift=0.05)
        sky = dict(full, sky_gap_thickness=20.0, sky_cloud_cover=50.0, sky_lit=1.0, sky_quality=70.0)
        self.assertEqual(predict.forecast("02_1h_pre", sky)[1], predict.MODELS[0]["name"])
        self.assertEqual(predict.forecast("01_2h_pre", sky)[1], "icon+goes+band")  # no sky coefficients at 2h
        self.assertEqual(predict.forecast("02_1h_pre", full)[1], "icon+goes+band")  # sky not read yet: next set
        self.assertEqual(predict.forecast("02_1h_pre", dict(full, horizon_lift=None))[1], "icon+goes")  # band missing: next set
        self.assertEqual(predict.forecast("02_1h_pre", {"cur_pct": .5, "max_pct": .5}), (None, None))

    def test_features_read_icon_and_goes_fields(self):
        p = capture("2026-09-01", "02_1h_pre", rh=40, goes_fan=0.3,
                    **{f"path{km}_icon_cloud_cover_{l}": 90 for km in predict.PATH_KM for l in ("low", "mid")})
        x = predict.features(p, 0.1, 0.2)
        self.assertAlmostEqual(x["weather"], 0.8)
        self.assertAlmostEqual(x["icon_weather"], -0.2)
        self.assertEqual((x["goes_fan"], x["goes_near"], x["cur_pct"]), (0.3, None, 0.1))

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
        self.assertEqual(set(by_label["06_5m_pre"]), {"predicted_pct", "predicted_score", "predicted_call", "predicted_with"})
        self.assertEqual(by_label["06_5m_pre"]["predicted_with"], "base")
        # The 5m shot beat every past day, so it should be the more hopeful forecast.
        self.assertGreater(by_label["06_5m_pre"]["predicted_pct"], by_label["01_2h_pre"]["predicted_pct"])
        # Scores come from past daily bests (0..11): today's own 60 is not history.
        self.assertLessEqual(by_label["06_5m_pre"]["predicted_score"], 11)

    def test_skips_until_there_is_enough_history_and_already_forecast_shots(self):
        n, _ = self.run_fill(self.history(5) + [capture("2026-09-01", "01_2h_pre")])
        self.assertEqual(n, 0)
        n, _ = self.run_fill(self.history() + [capture("2026-09-01", "01_2h_pre", predicted_pct=40.0)])
        self.assertEqual(n, 0)
        n, _ = self.run_fill(self.history() + [capture("2026-09-01", "01_2h_pre", predicted_pct=40.0, predicted_with="base")])
        self.assertEqual(n, 0)

    def test_redoes_a_forecast_when_better_inputs_arrive(self):
        late = capture("2026-09-01", "02_1h_pre", predicted_pct=40.0, predicted_with="base", goes_over=0.1, goes_near=0.1,
                       goes_far=0.1, goes_fan=0.1, **{f"path{km}_icon_cloud_cover_{l}": 0 for km in predict.PATH_KM for l in ("low", "mid")})
        n, written = self.run_fill(self.history() + [late])
        self.assertEqual(n, int(predict.MODELS[0]["name"] != "base"))


if __name__ == "__main__":
    unittest.main()
