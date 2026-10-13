"""Checks for the METAR observations. Run: python -m unittest ai_judge.test_metar"""

import unittest
from datetime import datetime, timedelta, timezone

from ai_judge import metar


def row(valid, **kw):
    r = {"valid": valid, "vsby": "10.00", "tmpf": "12.0", "dwpf": "0.0", "relh": "59", "sknt": "10", "gust": "M",
         "wxcodes": "M", **{f"sky{k}{i}": "M" for k in "cl" for i in range(1, 5)}}
    r.update(kw)
    return r


class Metar(unittest.TestCase):
    def test_parse_btv_2026_02_01(self):
        f = metar.parse(row("2026-02-01 22:54", skyc1="FEW", skyl1="20000.00"))
        self.assertEqual(f["obs_visibility_mi"], 10.0)
        self.assertEqual(f["obs_sky"], "FEW 20000")
        self.assertEqual(f["obs_cover"], .19)
        self.assertNotIn("obs_ceiling_ft", f)  # FEW isn't a ceiling
        self.assertNotIn("obs_gust_mph", f)    # missing: left out, InfluxDB can't store null
        self.assertAlmostEqual(f["obs_wind_mph"], 11.5)
        f = metar.parse(row("x", skyc1="SCT", skyl1="900", skyc2="OVC", skyl2="2500", wxcodes="-RA BR", vsby="2.50"))
        self.assertEqual((f["obs_ceiling_ft"], f["obs_cover"], f["obs_wx"]), (2500, 1, "-RA BR"))

    def test_latest_report_at_or_before_and_fresh(self):
        t0 = datetime(2026, 2, 1, 21, 54, tzinfo=timezone.utc)
        rows = [(t0, "a"), (t0 + timedelta(hours=1), "b")]
        self.assertEqual(metar.latest(rows, t0 + timedelta(minutes=50)), "a")
        self.assertEqual(metar.latest(rows, t0 + timedelta(hours=1)), "b")
        self.assertIsNone(metar.latest(rows, t0 - timedelta(minutes=1)))
        self.assertIsNone(metar.latest(rows, t0 + timedelta(hours=3)))  # stale


if __name__ == "__main__":
    unittest.main()
