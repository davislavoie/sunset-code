"""Checks for the glass-lake detector. Run: python -m unittest ai_judge.test_reflect"""

import io
import unittest
from unittest import mock

import numpy as np
from PIL import Image

from ai_judge import reflect, store
from ai_judge.rerank import pick


def jpeg(a):
    buf = io.BytesIO()
    Image.fromarray(a.astype(np.uint8)).save(buf, format="JPEG", quality=95)
    return buf.getvalue()


def scene(mirrored, seed=0):
    """640x360 frame: a cloudy sky (blobs, sky-blue ramp) over either its own reflection or choppy water."""
    rng = np.random.default_rng(seed)
    blobs = rng.normal(size=(50, 160, 3)) * 50  # fine cloud texture, as real skies have
    sky = np.asarray(Image.fromarray(np.clip(blobs + 128, 0, 255).astype(np.uint8)).resize((640, 200), Image.BICUBIC), float)
    sky += np.linspace(0, 60, 200)[:, None, None]
    sky[:, 300:308] = 40  # a mast: vertical, so it must not count as mirroring
    water = sky[::-1][:160] * .8 if mirrored else 90 + rng.normal(size=(160, 640, 3)) * 25
    return jpeg(np.clip(np.vstack([sky, water]), 0, 255))


class MirrorScore(unittest.TestCase):
    def test_reflection_scores_above_the_badge_threshold(self):
        score, row = reflect.mirror_score(scene(mirrored=True))
        self.assertGreaterEqual(score, reflect.GLASS_LAKE)
        self.assertAlmostEqual(row, 200 / 360, delta=.05)

    def test_choppy_water_scores_below_it(self):
        self.assertLess(reflect.mirror_score(scene(mirrored=False))[0], reflect.GLASS_LAKE)

    def test_blank_frame_is_minus_one(self):
        self.assertEqual(reflect.mirror_score(jpeg(np.zeros((180, 320, 3))))[0], -1.0)


class Fill(unittest.TestCase):
    def test_writes_score_and_badge_only_for_btv_captures_lacking_one(self):
        points = [{"time": "t1", "label": "07_sunset", "camera": "btv_echo_cam", "url": "a"},
                  {"time": "t2", "label": "06_5m_pre", "camera": "btv_echo_cam", "url": "b", "mirror_score": 0.2}]
        client = mock.Mock()
        with mock.patch.object(reflect.store, "captures", return_value=points), \
                mock.patch.object(reflect.store, "image_bytes", return_value=scene(mirrored=True)):
            self.assertEqual(reflect.fill(client, "btv_echo_cam"), 1)
            self.assertEqual(reflect.fill(client, "bolton_summit_cam"), 0)
        (written,), _ = client.write_points.call_args
        self.assertEqual(len(written), 1)
        self.assertEqual(written[0]["time"], "t1")
        self.assertTrue(written[0]["fields"]["glass_lake"])
        self.assertGreaterEqual(written[0]["fields"]["mirror_score"], reflect.GLASS_LAKE)


class Bump(unittest.TestCase):
    def test_bonus_steps(self):
        self.assertEqual([store.glass_bonus({"mirror_score": m}) for m in (None, -1.0, 0.34, 0.35, 0.44, 0.45, 0.9)],
                         [0, 0, 0, 5, 5, 8, 8])

    def test_glass_shot_wins_within_the_bump_but_not_beyond(self):
        glass = {"time": "g", "score": 58.0, "mirror_score": 0.4}
        self.assertIs(pick([{"time": "a", "score": 62.0}, glass]), glass)
        self.assertEqual(pick([{"time": "a", "score": 64.0}, glass])["time"], "a")

    def test_thumbs_up_still_beats_the_bump(self):
        liked = {"time": "a", "score": 40.0, "thumb": 1}
        self.assertIs(pick([liked, {"time": "g", "score": 58.0, "mirror_score": 0.6}]), liked)


if __name__ == "__main__":
    unittest.main()
