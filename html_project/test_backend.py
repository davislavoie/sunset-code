"""Checks for picking each day's best shot (no database needed). Run: python -m unittest html_project.test_backend"""

import unittest
from unittest import mock

from html_project import backend


def shot(time, score, label="07_sunset", **fields):
    return {"time": time, "score": score, "label": label, "url": f"http://x/{time}.jpg", **fields}


class BestShot(unittest.TestCase):
    def test_highest_score_wins_and_excluded_shots_cant(self):
        self.assertEqual(backend.best_shot([shot("a", 40.0), shot("b", 60.0)])["time"], "b")
        self.assertEqual(backend.best_shot([shot("a", 40.0), shot("b", 90.0, thumb=-1)])["time"], "a")
        self.assertEqual(backend.best_shot([shot("a", 40.0), shot("b", 90.0, ai_view="dark")])["time"], "a")
        self.assertIsNone(backend.best_shot([shot("b", 90.0, thumb=-1)]))

    def test_glass_bonus_steps_and_wins_within_the_bump_but_not_beyond(self):
        self.assertEqual([backend.glass_bonus({"score": 50, "mirror_score": m}) for m in (None, -1.0, 0.34, 0.35, 0.44, 0.45, 0.9)],
                         [0, 0, 0, 5, 5, 8, 8])

    def test_no_glass_bonus_on_grey_or_rainy_shots(self):
        self.assertEqual(backend.glass_bonus({"score": 0.0, "mirror_score": 0.5}), 0)  # 2025-05-31: grey, 0 HSV
        self.assertEqual(backend.glass_bonus({"score": 50, "mirror_score": 0.5, "precipitation": 7.6}), 0)
        self.assertEqual(backend.glass_bonus({"score": 10, "mirror_score": 0.5, "precipitation": 0.0}), 8)
        self.assertEqual(backend.best_shot([shot("a", 0.0), shot("g", 0.0, mirror_score=0.4)])["time"], "a")
        glass = shot("g", 58.0, mirror_score=0.4)
        self.assertIs(backend.best_shot([shot("a", 62.0), glass]), glass)
        self.assertEqual(backend.best_shot([shot("a", 64.0), glass])["time"], "a")

    def test_thumbs_up_beats_everything(self):
        liked = shot("a", 40.0, thumb=1, view_blocked=True)
        self.assertIs(backend.best_shot([liked, shot("g", 58.0, mirror_score=0.6)]), liked)


class CameraData(unittest.TestCase):
    def test_ranked_day_comes_from_the_captures_and_old_ranked_points_are_ignored(self):
        points = [shot("2025-05-17T00:12:00Z", 30.0, "06_5m_pre"),
                  shot("2025-05-17T00:17:00Z", 55.0, "07_sunset", contrast=1.2, red_points=3.0),
                  shot("2025-05-17T00:12:00Z", 30.0, "11_ranked_5m_pre"), shot("2025-05-17T00:12:00Z", 30.0, "12_histogram_5m_pre")]
        fake = mock.Mock()
        fake.query.return_value.get_points.return_value = iter(points)
        with mock.patch.object(backend, "client", fake):
            data = backend.fetch_camera_data("cam")
        self.assertEqual([d["Label"] for d in data["all_data"]], ["06_5m_pre", "07_sunset"])
        [ranked] = data["ranked_images"]
        self.assertEqual((ranked["Date"], ranked["Label"], ranked["Score"]), ("2025-05-16", "07_sunset", 55.0))
        self.assertEqual(ranked["Breakdown"], {"red_points": 3.0, "contrast": 1.2})
        self.assertIsNone(data["all_data"][0]["Breakdown"])  # scored before breakdowns were stored


class Thumbs(unittest.TestCase):
    def setUp(self):
        import tempfile
        from pathlib import Path
        from PIL import Image
        self.tmp = Path(tempfile.mkdtemp())
        photo = self.tmp / "pictures" / "sunset_images" / "cam" / "07_sunset.jpg"
        photo.parent.mkdir(parents=True)
        Image.new("RGB", (1920, 1080), (200, 120, 40)).save(photo)
        (self.tmp / "pictures" / "secret.txt").write_text("no")
        patches = [mock.patch.object(backend, "IMAGE_BASE_URL", "http://nuc:8080"),
                   mock.patch.object(backend, "PICTURES_DIR", self.tmp / "pictures"),
                   mock.patch.object(backend, "THUMB_DIR", self.tmp / "thumbs")]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        self.client = backend.app.test_client()

    def get(self, url, w=480):
        return self.client.get("/api/thumb", query_string={"url": url, "w": w})

    def test_makes_and_caches_a_small_copy(self):
        from io import BytesIO
        from PIL import Image
        r = self.get("http://nuc:8080/sunset_images/cam/07_sunset.jpg")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(Image.open(BytesIO(r.data)).size, (480, 270))
        self.assertIn("immutable", r.headers["Cache-Control"])
        self.assertTrue((self.tmp / "thumbs" / "480" / "sunset_images" / "cam" / "07_sunset.jpg").is_file())
        r.close()

    def test_only_our_photos(self):
        self.assertEqual(self.get("http://evil:8080/sunset_images/cam/07_sunset.jpg").status_code, 400)
        self.assertEqual(self.get("http://nuc:8080/../../etc/passwd.jpg").status_code, 400)
        self.assertEqual(self.get("http://nuc:8080/%2e%2e/%2e%2e/x.jpg").status_code, 400)
        self.assertEqual(self.get("http://nuc:8080/secret.txt").status_code, 400)
        self.assertEqual(self.get("http://nuc:8080/sunset_images/cam/07_sunset.jpg", w=4000).status_code, 400)
        self.assertEqual(self.get("http://nuc:8080/sunset_images/cam/missing.jpg").status_code, 404)


class CameraRequests(unittest.TestCase):
    def setUp(self):
        self.client = backend.app.test_client()
        self.db = mock.patch.object(backend, "client").start()
        self.addCleanup(mock.patch.stopall)
        self.db.query.return_value.get_points.return_value = []

    def test_request_is_saved_with_only_known_fields(self):
        r = self.client.post("/api/camera-requests", json={"stream_url": "https://youtu.be/x", "name": "Pier cam",
                                                            "mode": "weird", "is_admin": True})
        self.assertEqual(r.status_code, 200)
        fields = self.db.write_points.call_args[0][0][0]["fields"]
        self.assertEqual((fields["name"], fields["mode"], fields["dismissed"]), ("Pier cam", "sunset", False))
        self.assertNotIn("is_admin", fields)

    def test_needs_a_link_and_caps_pending(self):
        self.assertEqual(self.client.post("/api/camera-requests", json={"stream_url": "javascript:x"}).status_code, 400)
        self.db.query.return_value.get_points.return_value = [{"time": str(i)} for i in range(backend.MAX_PENDING_REQUESTS)]
        self.assertEqual(self.client.post("/api/camera-requests", json={"stream_url": "https://x"}).status_code, 429)

    def test_dismissed_requests_drop_out(self):
        self.db.query.return_value.get_points.return_value = [
            {"time": "a", "stream_url": "https://x", "dismissed": False}, {"time": "b", "stream_url": "https://y", "dismissed": True}]
        with mock.patch.object(backend, "ADMIN_PASSWORD", "pw"):
            r = self.client.get("/api/admin/camera-requests", headers={"Authorization": "Basic eDpwdw=="})  # x:pw
        self.assertEqual([r["id"] for r in r.json], ["a"])


class AdminPassword(unittest.TestCase):
    def setUp(self):
        self.client = backend.app.test_client()
        mock.patch.object(backend, "client").start()
        self.addCleanup(mock.patch.stopall)

    def test_admin_needs_the_password(self):
        import base64
        basic = lambda pw: {"Authorization": "Basic " + base64.b64encode(f"x:{pw}".encode()).decode()}
        with mock.patch.object(backend, "ADMIN_PASSWORD", "secret"):
            self.assertEqual(self.client.get("/api/admin/camera-requests").status_code, 401)
            self.assertEqual(self.client.get("/api/admin/camera-requests", headers=basic("nope")).status_code, 401)
            self.assertEqual(self.client.get("/api/admin/camera-requests", headers=basic("secret")).status_code, 200)
            self.assertEqual(self.client.get("/admin/config").status_code, 401)
            self.assertEqual(self.client.get("/api/camera-locations").status_code, 200)  # public stays open
        with mock.patch.object(backend, "ADMIN_PASSWORD", ""):
            self.assertEqual(self.client.get("/api/admin/camera-requests", headers=basic("")).status_code, 503)


if __name__ == "__main__":
    unittest.main()
