"""Checks for the GOES-East reader and the ICON path fetch (no network). Run: python -m unittest ai_judge.test_goes"""

import sys
import types
import unittest
from datetime import datetime, timezone
from unittest import mock

import numpy as np

from ai_judge import goes, weather


def key(start):
    return f"ABI-L2-ACMC/2026/008/20/OR_ABI-L2-ACMC-M6_G19_s{start}_e20260082003546_c20260082005087.nc"


class FakeResponse:
    def __init__(self, text="", content=b"", headers=None):
        self.text, self.content, self.headers = text, content, headers or {}

    def raise_for_status(self):
        pass

    def json(self):
        return self._json


class Projection(unittest.TestCase):
    def test_matches_the_goes_r_pug_worked_example(self):
        proj = {"perspective_point_height": [35786023.0], "semi_major_axis": [6378137.0],
                "semi_minor_axis": [6356752.31414], "longitude_of_projection_origin": [-75.0]}
        lat, lon = goes.latlon_grid(np.array([-0.024052]), np.array([0.095340]), proj)
        self.assertAlmostEqual(lat[0, 0], 33.846162, places=4)
        self.assertAlmostEqual(lon[0, 0], -84.690932, places=4)


class Zones(unittest.TestCase):
    def test_cloud_only_far_toward_the_sun(self):
        lat0, lon0 = 44.48, -73.22
        lat, lon = np.meshgrid(np.linspace(41.5, 47.5, 301), np.linspace(-77.5, -69, 301), indexing="ij")
        dy, dx = (lat - lat0) * 111.2, (lon - lon0) * 111.2 * np.cos(np.radians(lat0))
        west = np.abs((np.degrees(np.arctan2(dx, dy)) - 270 + 180) % 360 - 180) <= 30
        bcm = (west & (np.hypot(dx, dy) >= 100)).astype(float)
        z = goes.zones(bcm, lat, lon, lat0, lon0, 270)
        self.assertEqual((z["goes_over"], z["goes_near"]), (0, 0))
        self.assertGreater(z["goes_far"], 0.9)
        self.assertTrue(0 < z["goes_fan"] < z["goes_far"])

    def test_zone_with_no_valid_pixels_is_none(self):
        lat, lon = np.meshgrid(np.linspace(44, 45, 11), np.linspace(-74, -73, 11), indexing="ij")
        self.assertIsNone(goes.zones(np.full(lat.shape, np.nan), lat, lon, 44.5, -73.5, 270)["goes_over"])


class Scans(unittest.TestCase):
    def test_picks_the_latest_scan_landed_by_the_capture(self):
        listing = "".join(f"<Key>{key(s)}</Key>" for s in ("20260082001173", "20260082006173", "20260082011173"))
        goes._listings.clear()
        session = mock.Mock(get=mock.Mock(return_value=FakeResponse(text=listing)))
        # 20:13 capture: the 20:11 scan hasn't landed yet (5 min latency), so 20:06.
        url = goes.scan_url(datetime(2026, 1, 8, 20, 13, tzinfo=timezone.utc), session)
        self.assertTrue(url.endswith(key("20260082006173")))
        goes._listings.clear()
        self.assertIsNone(goes.scan_url(datetime(2026, 1, 8, 20, 5, tzinfo=timezone.utc),
                                        mock.Mock(get=mock.Mock(return_value=FakeResponse(text=f"<Key>{key('20260082011173')}</Key>")))))

    def test_range_file_reads_across_blocks(self):
        blob = bytes(range(256)) * 4096  # 1 MiB
        def get(url, headers, timeout):
            lo, hi = map(int, headers["Range"].split("=")[1].split("-"))
            return FakeResponse(content=blob[lo:hi + 1], headers={"Content-Range": f"bytes {lo}-{hi}/{len(blob)}"})
        f = goes.RangeFile("u", mock.Mock(get=mock.Mock(side_effect=get)))
        f.seek(goes.RangeFile.BLOCK - 3)
        self.assertEqual(f.read(6), blob[goes.RangeFile.BLOCK - 3:goes.RangeFile.BLOCK + 3])
        f.seek(-2, 2)
        self.assertEqual(f.read(10), blob[-2:])


def fake_pipeline():
    """Stand-in for sunset_code.helpers.open_metro_weater_api (needs packages the tests don't)."""
    mod = types.ModuleType("open_metro_weater_api")
    mod.sun_bearing = lambda day, lat, lon, mode="sunset": 270.0
    mod.path_points = lambda lat, lon, bearing: [(13, 44.4, -73.4), (40, 44.4, -73.7), (80, 44.4, -74.2)]
    mod.PATH_LAYERS = ["cloud_cover_low", "cloud_cover_mid", "cloud_cover_high"]
    return mock.patch.dict(sys.modules, {"sunset_code": types.ModuleType("sunset_code"),
                                         "sunset_code.helpers": types.ModuleType("sunset_code.helpers"),
                                         "sunset_code.helpers.open_metro_weater_api": mod})


class Fill(unittest.TestCase):
    def test_writes_goes_fields_on_captures_lacking_them_and_skips_failures(self):
        points = [{"time": "2026-09-01T22:00:00Z", "camera": "btv_echo_cam", "label": "02_1h_pre"},
                  {"time": "2026-09-01T22:30:00Z", "camera": "btv_echo_cam", "label": "04_30m_pre"},
                  {"time": "2026-09-01T23:30:00Z", "camera": "btv_echo_cam", "label": "07_sunset"},
                  {"time": "2026-09-01T21:00:00Z", "camera": "btv_echo_cam", "label": "01_2h_pre", "goes_fan": 0.5}]
        reading = {"goes_over": 1.0, "goes_near": 0.5, "goes_far": None, "goes_fan": 0.4}
        client = mock.Mock()
        with fake_pipeline(), mock.patch.object(goes.store, "captures", return_value=points), \
                mock.patch.object(weather, "camera_config", return_value={"LAT": "44.47", "LON": "-73.22"}), \
                mock.patch.object(goes, "observe", side_effect=[reading, TimeoutError("S3 slow"), reading]) as observe:
            self.assertEqual(goes.fill(client, "btv_echo_cam"), 2)
        self.assertEqual(observe.call_count, 3)  # the shot that already had GOES is skipped
        (written,), _ = client.write_points.call_args
        self.assertEqual([w["tags"]["label"] for w in written], ["02_1h_pre", "07_sunset"])
        self.assertEqual(written[0]["fields"], {"goes_over": 1.0, "goes_near": 0.5, "goes_fan": 0.4})


class Icon(unittest.TestCase):
    def test_icon_path_hourly_asks_for_icon_and_names_fields(self):
        resp = FakeResponse()
        resp._json = [{"hourly": {"time": [3600], "cloud_cover_low": [10], "cloud_cover_mid": [None], "cloud_cover_high": [70]}}] * 3
        with fake_pipeline(), mock.patch.object(weather.requests, "get", return_value=resp) as get:
            hours = weather.icon_path_hourly(44.47, -73.22, 270, "2026-09-01", "2026-09-02")
        self.assertEqual(get.call_args.kwargs["params"]["models"], "icon_seamless")
        self.assertEqual(hours[3600], {"path13_icon_cloud_cover_low": 10.0, "path13_icon_cloud_cover_high": 70.0,
                                       "path40_icon_cloud_cover_low": 10.0, "path40_icon_cloud_cover_high": 70.0,
                                       "path80_icon_cloud_cover_low": 10.0, "path80_icon_cloud_cover_high": 70.0})


if __name__ == "__main__":
    unittest.main()
