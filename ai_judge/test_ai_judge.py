"""Checks for the AI judge against a fake Ollama server (no model needed).
Run: python -m unittest ai_judge.test_ai_judge
"""

import base64
import io
import json
import os
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

from PIL import Image

from ai_judge import store
from ai_judge.judge import judge_image


def jpeg(width=1920, height=1080, color=(240, 120, 60)):
    buf = io.BytesIO()
    Image.new("RGB", (width, height), color).save(buf, format="JPEG")
    return buf.getvalue()


class FakeServer:
    """Tiny HTTP server: records requests and replies with whatever `respond` returns."""

    def __init__(self, respond):
        self.requests = []
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                outer.requests.append(body)
                status, payload = respond(body)
                self._send(status, payload)

            def do_GET(self):
                outer.requests.append(self.path)
                status, payload = respond(self.path)
                self._send(status, payload)

            def _send(self, status, payload):
                data = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
                self.send_response(status)
                self.end_headers()
                self.wfile.write(data)

            def log_message(self, *args):
                pass

        self.httpd = HTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.httpd.server_port}"
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def close(self):
        self.httpd.shutdown()


def ollama_reply(content):
    return 200, {"message": {"role": "assistant", "content": json.dumps(content)}, "done": True}


class JudgeTests(unittest.TestCase):
    def test_sends_small_image_with_schema_and_parses_answer(self):
        server = FakeServer(lambda body: ollama_reply({"view": "sky", "score": 83, "reason": "vivid pink clouds"}))
        try:
            result = judge_image(jpeg(), "qwen3-vl:4b", server.url)
        finally:
            server.close()
        self.assertEqual(result, {"view": "sky", "is_sunset": True, "score": 83, "reason": "vivid pink clouds"})
        sent = server.requests[0]
        self.assertEqual(sent["model"], "qwen3-vl:4b")
        self.assertEqual(sent["options"]["temperature"], 0)
        self.assertIs(sent["think"], False)
        self.assertIn("view", sent["format"]["properties"])
        img = Image.open(io.BytesIO(base64.b64decode(sent["messages"][0]["images"][0])))
        self.assertEqual(img.size, (768, 432))  # downscaled, aspect kept

    def test_not_a_sky_view_never_counts(self):
        server = FakeServer(lambda body: ollama_reply({"view": "obstructed", "score": 70, "reason": "brick wall"}))
        try:
            result = judge_image(jpeg(), "m", server.url)
        finally:
            server.close()
        self.assertEqual((result["is_sunset"], result["score"]), (False, 0))

    def test_retries_without_think_flag_when_model_rejects_it(self):
        def respond(body):
            if "think" in body:
                return 400, {"error": "model does not support think"}
            return ollama_reply({"view": "sky", "score": 40, "reason": "some orange"})

        server = FakeServer(respond)
        try:
            result = judge_image(jpeg(), "m", server.url)
        finally:
            server.close()
        self.assertEqual(result["score"], 40)
        self.assertEqual(len(server.requests), 2)

    def test_unreachable_server_returns_none(self):
        self.assertIsNone(judge_image(jpeg(), "m", "http://127.0.0.1:9", timeout=2))

    def test_unusable_answer_returns_none(self):
        server = FakeServer(lambda body: ollama_reply({"view": "beach", "score": 50, "reason": "?"}))
        try:
            self.assertIsNone(judge_image(jpeg(), "m", server.url))
        finally:
            server.close()


class StoreTests(unittest.TestCase):
    def test_save_merges_ai_fields_into_the_same_point(self):
        written = []

        class FakeClient:
            def write_points(self, points):
                written.extend(points)

        point = {"time": "2025-05-16T20:12:26Z", "label": "06_5m_pre_05-16-2025.jpg", "camera": "btv_echo_cam",
                 "url": "http://x/a.jpg", "score": 42.6}
        store.save_judgment(FakeClient(), point, {"view": "sky", "is_sunset": True, "score": 77, "reason": "r"}, "m")
        [p] = written
        # Same measurement + tags + time as the original, so InfluxDB merges instead of duplicating;
        # and only ai_* fields, so url/score are untouched.
        self.assertEqual((p["measurement"], p["tags"], p["time"]),
                         ("sunset_images", {"label": point["label"], "camera": "btv_echo_cam"}, point["time"]))
        self.assertEqual(set(p["fields"]), set(store.AI_FIELDS))

    def test_ranked_and_histogram_images_are_not_judged(self):
        self.assertTrue(store.is_raw_capture({"label": "07_sunset_05-16-2025.jpg"}))
        self.assertFalse(store.is_raw_capture({"label": "11_ranked_5m_pre_05-16-2025.jpg.png"}))
        self.assertFalse(store.is_raw_capture({"label": "12_histogram_5m_pre_05-16-2025.jpg.png"}))

    def test_image_fetch_rewrites_public_url_to_internal_server(self):
        server = FakeServer(lambda path: (200, b"jpeg-bytes"))
        os.environ.update(IMAGE_BASE_URL="http://100.107.153.41:8080", IMAGE_FETCH_URL=server.url)
        try:
            data = store.image_bytes({"url": "http://100.107.153.41:8080/sunset_images/cam/a.jpg"})
        finally:
            server.close()
            del os.environ["IMAGE_BASE_URL"], os.environ["IMAGE_FETCH_URL"]
        self.assertEqual(data, b"jpeg-bytes")
        self.assertEqual(server.requests, ["/sunset_images/cam/a.jpg"])


if __name__ == "__main__":
    unittest.main()
