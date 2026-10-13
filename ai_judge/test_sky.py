"""Checks for the vision model's sky read. Run: python -m unittest ai_judge.test_sky"""

import unittest

from ai_judge import predict, sky


class Sky(unittest.TestCase):
    def test_answer_becomes_clamped_fields(self):
        f = sky.fields({"gap": "yes", "gap_thickness": 130, "cloud_cover": -5, "cloud_base": "low", "clouds_overhead": True,
                        "underside_lit": "likely", "predicted_quality": 85, "reason": "Lit band under the deck."})
        self.assertEqual((f["sky_gap_thickness"], f["sky_cloud_cover"], f["sky_lit"]), (100.0, 0.0, 1))
        self.assertEqual(f["sky_model"], sky.MODEL)
        self.assertTrue(all(isinstance(v, float) for k, v in f.items() if k not in ("sky_model", "sky_gap", "sky_cloud_base",
                                                                                     "sky_overhead", "sky_reason")))
        x = predict.features(f, 0.5, 0.5)
        self.assertEqual((x["sky_gap_thickness"], x["sky_quality"]), (100.0, 85.0))

    def test_only_the_shots_with_time_to_go(self):
        self.assertEqual([sky.label_of({"label": l}) for l in ("01_2h_pre", "02_1h_pre", "04_30m_pre_06-22-2026.jpg", "05_15m_pre")],
                         [None, "02_1h_pre", "04_30m_pre", None])
        self.assertIn("30 minutes before sunset", sky.PROMPT.format(when=sky.LABELS["04_30m_pre"]))


if __name__ == "__main__":
    unittest.main()
