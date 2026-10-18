"""Checks for rescoring, the view rules and weather with a fake InfluxDB and a fake scorer
(no OpenCV, model or database needed). Run: python -m unittest ai_analysis.test_rescore
"""

import os
import tempfile
import unittest
from datetime import date

from ai_analysis import rescore, store, views, weather

BASE = "http://100.107.153.41:8080"


class FakeResult:
    def __init__(self, points):
        self._points = points

    def get_points(self):
        return iter(self._points)


class FakeClient:
    def __init__(self, points=()):
        self.points = list(points)
        self.queries, self.writes = [], []

    def query(self, q, bind_params=None):
        self.queries.append((q, bind_params))
        return FakeResult([dict(p) for p in self.points] if q.startswith("SELECT") else [])

    def write_points(self, points):
        self.writes.extend(points)


def fake_rank_sunset(path, camera=None):
    return (55.5, {"red_points": 1.0}, {"hue": [1.0]})


def capture(label, time, score, **fields):
    return {"label": label, "camera": "cam", "time": time, "score": score, "url": f"{BASE}/sunset_images/cam/{label}", **fields}


# One evening: 8:12 PM EDT on May 16 is 00:12 UTC on May 17.
WALL = capture("06_5m_pre_05-16-2025.jpg", "2025-05-17T00:12:00Z", 90.0, thumb=-1)
SKY_A = capture("07_sunset_05-16-2025.jpg", "2025-05-17T00:17:00Z", 40.0)
SKY_B = capture("08_5m_post_05-16-2025.jpg", "2025-05-17T00:22:00Z", 60.0)
RANKED_WALL = [capture("11_ranked_5m_pre_05-16-2025.png", WALL["time"], 90.0),
               capture("12_histogram_5m_pre_05-16-2025.png", WALL["time"], 90.0)]


class RescoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.environ.update(IMAGE_BASE_URL=BASE, PICTURES_DIR=self.tmp.name)
        self.photo_dir = os.path.join(self.tmp.name, "sunset_images", "cam")
        os.makedirs(self.photo_dir)

    def tearDown(self):
        self.tmp.cleanup()
        del os.environ["IMAGE_BASE_URL"], os.environ["PICTURES_DIR"]

    def test_local_dates_follow_the_camera_not_utc(self):
        self.assertEqual(store.local_date(WALL), date(2025, 5, 16))

    def test_url_maps_back_to_the_photo_on_disk(self):
        self.assertEqual(store.local_path(SKY_A), os.path.join(self.photo_dir, SKY_A["label"]))

    def test_rescore_rewrites_score_breakdown_and_histogram_in_place(self):
        client = FakeClient([WALL, SKY_A, *RANKED_WALL])
        rescore.rescore(client, "cam", rank_sunset=fake_rank_sunset)
        self.assertEqual([q for q, _ in client.queries if not q.startswith("SELECT")], [])  # nothing deleted
        main = [w for w in client.writes if w["measurement"] == store.MEASUREMENT]
        hist = [w for w in client.writes if w["measurement"] == store.HIST_MEASUREMENT]
        # captures only (not the old 11_/12_), same tags and time, so InfluxDB merges the fields
        self.assertEqual([(w["tags"]["label"], w["time"]) for w in main], [(WALL["label"], WALL["time"]), (SKY_A["label"], SKY_A["time"])])
        self.assertEqual(main[0]["fields"], {"score": 55.5, "red_points": 1.0})
        self.assertEqual(hist[0]["fields"], {"hist": '{"hue":[1.0]}'})

    def test_rescore_dry_run_writes_nothing_and_skips_missing_photos(self):
        client = FakeClient([SKY_A, SKY_B])
        rescore.rescore(client, "cam", dry_run=True, rank_sunset=fake_rank_sunset)
        self.assertEqual(client.writes, [])
        client = FakeClient([SKY_A, SKY_B])
        rescore.rescore(client, "cam", rank_sunset=lambda path, camera: None if path.endswith(SKY_B["label"]) else fake_rank_sunset(path))
        self.assertEqual(len(client.writes), 2)  # SKY_A's score + histogram

    def test_drop_ranked_lists_then_deletes_only_the_old_ranked_points_and_pngs(self):
        png = store.local_path(RANKED_WALL[0])
        open(png, "w").close()
        client = FakeClient([WALL, SKY_A, *RANKED_WALL])
        rescore.drop_ranked(client, "cam")
        self.assertFalse([q for q, _ in client.queries if q.startswith("DELETE")])
        self.assertTrue(os.path.exists(png))
        rescore.drop_ranked(client, "cam", delete=True)
        self.assertEqual([q for q, _ in client.queries if q.startswith("DELETE")],
                         [f"DELETE FROM {store.MEASUREMENT} WHERE camera = $camera AND label =~ /^1[12]_/"])
        self.assertFalse(os.path.exists(png))

    def test_best_shot_times_is_each_days_highest_score(self):
        self.assertEqual(store.best_shot_times(FakeClient([WALL, SKY_A, SKY_B, *RANKED_WALL]), "cam"), {WALL["time"]})

    def test_cleanup_lists_entries_whose_photo_is_gone_and_refuses_when_most_are(self):
        for p in (SKY_A, SKY_B):
            open(store.local_path(p), "w").close()
        many = [dict(SKY_A, label=f"{i:02}_x.jpg") for i in range(10)]
        for p in many:
            open(store.local_path(p), "w").close()
        days = store.missing_files(FakeClient([WALL, SKY_A, SKY_B, *many]), "cam")
        self.assertEqual({d: [p["label"] for p in v] for d, v in days.items()}, {date(2025, 5, 16): [WALL["label"]]})
        with self.assertRaises(SystemExit):  # photos folder not mounted: everything looks missing
            store.missing_files(FakeClient([WALL, SKY_A, SKY_B]), "cam", max_share=0.2)

    def test_date_range_filters_by_local_day(self):
        next_day = capture("07_sunset_05-17-2025.jpg", "2025-05-18T00:18:00Z", 30.0)
        client = FakeClient([WALL, next_day])
        found = store.points(client, "cam", since=date(2025, 5, 16), before=date(2025, 5, 17))
        self.assertEqual([p["label"] for p in found], [WALL["label"]])


class WeatherTests(unittest.TestCase):
    def test_each_capture_gets_its_nearest_utc_hour_without_nulls(self):
        # The pipeline's old weather_fetch asked for the capture's UTC date in local time, so a
        # capture after 8 PM EDT (after midnight UTC) got the next local day's midnight weather.
        hours = {1747440000: {"cloud_cover_low": 10, "visibility": None},   # 2025-05-17 00:00 UTC
                 1747443600: {"cloud_cover_low": 80, "visibility": 9000}}   # 01:00 UTC
        self.assertEqual(weather.weather_for(SKY_A, hours), {"cloud_cover_low": 10.0})
        late = dict(SKY_A, time="2025-05-17T00:40:00Z")
        self.assertEqual(weather.weather_for(late, hours), {"cloud_cover_low": 80.0, "visibility": 9000.0})


    def test_path_follows_the_sun_by_season_and_mode(self):
        import math
        from sunset_code.helpers.open_metro_weater_api import path_points, sun_bearing
        btv = (44.4766, -73.2212)
        # Summer sunsets are northwest, winter southwest, sunrises east; local dates, so a June
        # evening (after midnight UTC) still has a sunset.
        self.assertTrue(300 <= sun_bearing(date(2026, 6, 21), *btv) <= 306)
        self.assertTrue(235 <= sun_bearing(date(2025, 12, 21), *btv) <= 240)
        self.assertTrue(50 <= sun_bearing(date(2026, 6, 21), *btv, "sunrise") <= 60)
        km, lat, lon = path_points(*btv, 270)[-1]
        self.assertEqual(km, 80)
        self.assertAlmostEqual(lat, btv[0], delta=0.05)  # due west stays near the same latitude
        self.assertAlmostEqual((btv[1] - lon) * 111.3 * math.cos(math.radians(lat)), 80, delta=1)


class ViewTests(unittest.TestCase):
    def scene(self, shift=0, sky=(120, 140, 200), seed=0):
        import io
        import numpy as np
        from PIL import Image
        rng = np.random.default_rng(seed)
        ground = np.kron(rng.integers(0, 255, (9, 16)), np.ones((40, 40)))  # blocky "scenery"
        img = np.zeros((720, 640, 3), np.uint8)
        img[:360] = sky
        img[360:] = np.roll(ground, shift, axis=1)[:, :640, None]
        buf = io.BytesIO()
        Image.fromarray(img).save(buf, format="JPEG")
        return buf.getvalue()

    def test_same_view_matches_under_any_sky_and_other_views_dont(self):
        bad = dict(SKY_A, bad_view=True, view_fp=views.fingerprint(self.scene()))
        same = dict(SKY_B, view_fp=views.fingerprint(self.scene(shift=3, sky=(250, 120, 60))))
        other = dict(WALL, view_fp=views.fingerprint(self.scene(seed=1)))
        dark = dict(WALL, time="x", view_fp="")
        flags = views.blocked_flags([bad, same, other, dark])
        self.assertEqual(flags, {bad["time"]: True, same["time"]: True, other["time"]: False, "x": False})


if __name__ == "__main__":
    unittest.main()
