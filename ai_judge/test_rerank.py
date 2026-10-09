"""Checks for re-ranking and the AI gate with a fake InfluxDB and a fake pipeline
(no OpenCV, model or database needed). Run: python -m unittest ai_judge.test_rerank
"""

import os
import tempfile
import unittest
from datetime import date

from ai_judge import rerank, store

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


def capture(label, time, score, ai=None):
    p = {"label": label, "camera": "cam", "time": time, "score": score, "url": f"{BASE}/sunset_images/cam/{label}"}
    if ai is not None:
        p.update(ai_is_sunset=ai, ai_model="m")
    return p


# One evening: 8:12 PM EDT on May 16 is 00:12 UTC on May 17.
WALL = capture("06_5m_pre_05-16-2025.jpg", "2025-05-17T00:12:00Z", 90.0, ai=False)
SKY_A = capture("07_sunset_05-16-2025.jpg", "2025-05-17T00:17:00Z", 40.0, ai=True)
SKY_B = capture("08_5m_post_05-16-2025.jpg", "2025-05-17T00:22:00Z", 60.0, ai=True)
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

    def test_ignore_ai_picks_by_hsv_score_alone(self):
        msg = rerank.rerank_day(FakeClient(), "cam", [WALL, SKY_A, SKY_B, *RANKED_WALL], FakePipeline(), use_ai=False)
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

    def test_gate_only_acts_on_fully_judged_days_with_a_non_sky_best_shot(self):
        made = []
        factory = lambda: made.append(FakePipeline()) or made[-1]
        unjudged = dict(SKY_B)
        unjudged.pop("ai_model"), unjudged.pop("ai_is_sunset")
        rerank.gate_recent_days(FakeClient([WALL, SKY_A, unjudged, *RANKED_WALL]), "cam", factory)
        self.assertEqual(made, [])  # still waiting for SKY_B to be judged
        rerank.gate_recent_days(FakeClient([WALL, SKY_A, SKY_B, *RANKED_WALL]), "cam", factory)
        self.assertEqual(len(made), 1)  # now judged, and the pipeline's pick was the wall

    def test_date_range_filters_by_local_day(self):
        next_day = capture("07_sunset_05-17-2025.jpg", "2025-05-18T00:18:00Z", 30.0)
        client = FakeClient([WALL, next_day])
        found = store.points(client, "cam", since=date(2025, 5, 16), before=date(2025, 5, 17))
        self.assertEqual([p["label"] for p in found], [WALL["label"]])


if __name__ == "__main__":
    unittest.main()
