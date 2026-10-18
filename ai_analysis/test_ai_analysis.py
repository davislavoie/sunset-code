"""Checks for ai_analysis's Ollama downloads and image fetching against a fake server (no model needed).
Run: python -m unittest ai_analysis.test_ai_analysis
"""

import json
import os
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

from ai_analysis import store
from ai_analysis.ollama import ensure_model


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


class EnsureModelTests(unittest.TestCase):
    def test_streams_download_progress_and_skips_installed_models(self):
        lines = [{"status": "pulling manifest"}] + [
            {"status": "pulling abc", "total": 3_000_000_000, "completed": n * 300_000_000} for n in range(11)
        ] + [{"status": "success"}]
        stream = "\n".join(json.dumps(l) for l in lines).encode()

        def respond(req):
            if req == "/api/tags":
                return 200, {"models": [{"name": "already:here"}]}
            return 200, stream

        server = FakeServer(respond)
        try:
            with self.assertLogs("ai_analysis.ollama", level="INFO") as logs:
                ensure_model("new:model", server.url)
            ensure_model("already:here", server.url)  # no pull for an installed model
        finally:
            server.close()
        text = "\n".join(logs.output)
        self.assertIn("0% of 3.0 GB", text)
        self.assertIn("100% of 3.0 GB", text)
        self.assertIn("new:model ready", text)
        pulls = [r for r in server.requests if isinstance(r, dict)]
        self.assertEqual([r["model"] for r in pulls], ["new:model"])


class StoreTests(unittest.TestCase):
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
