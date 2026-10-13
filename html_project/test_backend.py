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


if __name__ == "__main__":
    unittest.main()
