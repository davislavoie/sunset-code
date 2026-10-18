"""Ollama model downloads for the local vision model (the sky read in sky.py)."""

import json
import logging

import requests

log = logging.getLogger(__name__)


def ensure_model(model, ollama_url):
    """Download the model into Ollama if it isn't there yet (first run only; can take minutes)."""
    base = ollama_url.rstrip("/")
    tags = requests.get(f"{base}/api/tags", timeout=30).json().get("models", [])
    if any(m.get("name") == model or m.get("model") == model for m in tags):
        return
    log.info("Downloading %s into Ollama (one-time, a few GB)...", model)
    # Stream the pull so progress shows up instead of a long silence.
    with requests.post(f"{base}/api/pull", json={"model": model, "stream": True}, stream=True, timeout=None) as resp:
        resp.raise_for_status()
        last_logged = -10
        for line in resp.iter_lines():
            if not line:
                continue
            update = json.loads(line)
            if update.get("error"):
                raise RuntimeError(f"Ollama couldn't pull {model}: {update['error']}")
            total, done = update.get("total"), update.get("completed")
            if total and done is not None:
                pct = int(done * 100 / total)
                if pct >= last_logged + 10 or pct == 100:
                    log.info("  %s: %s %d%% of %.1f GB", model, update.get("status", ""), pct, total / 1e9)
                    last_logged = pct
            elif update.get("status") and update["status"] != "success":
                log.info("  %s: %s", model, update["status"])
                last_logged = -10  # a new layer starts its own progress
    log.info("%s ready", model)
