"""Checks for re-ranking, the thumbs/view rules and weather with a fake InfluxDB and a fake pipeline
(no OpenCV, model or database needed). Run: python -m unittest ai_judge.test_rerank
"""

import os
import tempfile
import unittest
from datetime import date

from ai_judge import rerank, store, views, weather

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


class FakePipeline:
    def __init__(self):
        self.calls = []

    def rank_sunset(self, path):
        self.calls.append(("rank_sunset", path))
        return (55.5, "img", os.path.basename(path).rsplit(".", 1)[0], "h", "s", "v", None, None, None)

    def generate_ranked_image(self, img, score, name, h, s, v, photo_dir):
        self.calls.append(("generate", photo_dir))
        return os.path.join(photo_dir, f"12_histogram_{name[3:]}.png"), os.path.join(photo_dir, f"11_ranked_{name[3:]}.png")

    def influxdb_push(self, path, epoch, label, camera, score):
        self.calls.append(("push", label, epoch))


def capture(label, time, score, **fields):
    return {"label": label, "camera": "cam", "time": time, "score": score, "url": f"{BASE}/sunset_images/cam/{label}", **fields}


# One evening: 8:12 PM EDT on May 16 is 00:12 UTC on May 17.
WALL = capture("06_5m_pre_05-16-2025.jpg", "2025-05-17T00:12:00Z", 90.0, thumb=-1)
SKY_A = capture("07_sunset_05-16-2025.jpg", "2025-05-17T00:17:00Z", 40.0)
SKY_B = capture("08_5m_post_05-16-2025.jpg", "2025-05-17T00:22:00Z", 60.0)
RANKED_WALL = [capture("11_ranked_5m_pre_05-16-2025.png", WALL["time"], 90.0),
               capture("12_histogram_5m_pre_05-16-2025.png", WALL["time"], 90.0)]


class RerankTests(unittest.TestCase):
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

    def test_wall_best_shot_is_replaced_by_the_best_sky_capture(self):
        open(os.path.join(self.photo_dir, "11_ranked_old.png"), "w").close()
        pipeline = FakePipeline()
        msg = rerank.rerank_day(FakeClient(), "cam", [WALL, SKY_A, SKY_B, *RANKED_WALL], pipeline)
        self.assertTrue(msg.startswith("picked 08_5m_post"), msg)
        self.assertEqual(pipeline.calls[0], ("rank_sunset", store.local_path(SKY_B)))
        # histogram pushed before the ranked image, at the sky capture's time
        pushes = [c for c in pipeline.calls if c[0] == "push"]
        self.assertEqual([c[1][:3] for c in pushes], ["12_", "11_"])
        self.assertEqual({c[2] for c in pushes}, {store.epoch_seconds(SKY_B)})
        self.assertFalse(os.path.exists(os.path.join(self.photo_dir, "11_ranked_old.png")))

    def test_hsv_only_picks_by_hsv_score_alone(self):
        msg = rerank.rerank_day(FakeClient(), "cam", [WALL, SKY_A, SKY_B, *RANKED_WALL], FakePipeline(), use_rules=False)
        self.assertTrue(msg.startswith("unchanged: 06_5m_pre"), msg)

    def test_already_correct_day_is_left_alone(self):
        ranked = [dict(r, time=SKY_B["time"]) for r in RANKED_WALL]
        pipeline = FakePipeline()
        msg = rerank.rerank_day(FakeClient(), "cam", [WALL, SKY_A, SKY_B, *ranked], pipeline)
        self.assertTrue(msg.startswith("unchanged"), msg)
        self.assertEqual(pipeline.calls, [])

    def test_day_with_no_sky_is_not_ranked_at_all(self):
        client = FakeClient()
        msg = rerank.rerank_day(client, "cam", [WALL, *RANKED_WALL], FakePipeline())
        self.assertIn("ranking removed", msg)
        deletes = [b["label"] for q, b in client.queries if q.startswith("DELETE")]
        self.assertEqual(sorted(deletes), sorted(r["label"] for r in RANKED_WALL))

    def test_dry_run_changes_nothing(self):
        client, pipeline = FakeClient(), FakePipeline()
        msg = rerank.rerank_day(client, "cam", [WALL, SKY_A, SKY_B, *RANKED_WALL], pipeline, dry_run=True)
        self.assertTrue(msg.startswith("would pick 08_5m_post"), msg)
        self.assertEqual((pipeline.calls, client.queries, client.writes), ([], [], []))

    def test_rescore_saves_new_hsv_scores_before_picking(self):
        client = FakeClient()
        rerank.rerank_day(client, "cam", [dict(SKY_A), dict(SKY_B), *RANKED_WALL], FakePipeline(), rescore=True)
        self.assertEqual([w["fields"] for w in client.writes], [{"score": 55.5}, {"score": 55.5}])

    def test_unranked_days_are_left_alone_unless_fill_missing(self):
        pipeline = FakePipeline()
        msg = rerank.rerank_day(FakeClient(), "cam", [SKY_A, SKY_B], pipeline)
        self.assertTrue(msg.startswith("not ranked"), msg)
        self.assertEqual(pipeline.calls, [])
        msg = rerank.rerank_day(FakeClient(), "cam", [SKY_A, SKY_B], pipeline, fill_missing=True)
        self.assertTrue(msg.startswith("picked 08_5m_post"), msg)

    def test_rules_hsv_decides_unless_thumbs_or_dark(self):
        pick = lambda *caps: rerank.pick(list(caps))["label"]
        # The AI calling a frame "obstructed" or "no sunset" no longer matters; HSV decides.
        self.assertEqual(pick(dict(SKY_B, ai_view="obstructed"), SKY_A), SKY_B["label"])
        self.assertEqual(pick(dict(SKY_B, ai_view="dark"), SKY_A), SKY_A["label"])
        self.assertEqual(pick(dict(SKY_B, view_blocked=True), SKY_A), SKY_A["label"])
        # A thumbs up beats a higher score, and overrides a bad view.
        self.assertEqual(pick(SKY_B, dict(SKY_A, thumb=1, view_blocked=True)), SKY_A["label"])
        self.assertIsNone(rerank.pick([WALL]))

    def test_gate_only_acts_on_ranked_days_whose_best_shot_changed(self):
        made = []
        factory = lambda: made.append(FakePipeline()) or made[-1]
        right = [dict(r, time=SKY_B["time"]) for r in RANKED_WALL]
        rerank.gate_days(FakeClient([WALL, SKY_A, SKY_B, *right]), "cam", factory)
        rerank.gate_days(FakeClient([WALL, SKY_A, SKY_B]), "cam", factory)  # not ranked yet (today)
        self.assertEqual(made, [])
        rerank.gate_days(FakeClient([WALL, SKY_A, SKY_B, *RANKED_WALL]), "cam", factory)
        self.assertEqual(len(made), 1)  # the pipeline's pick was thumbed down

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
