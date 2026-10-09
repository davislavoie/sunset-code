# ai_judge: local AI sunset judge

An optional sidecar to the capture pipeline. For every capture it asks a small
vision model running locally in [Ollama](https://ollama.com) two things:

- **Is this actually the sky?** `sky`, `obstructed` (wall, tree, wrong preset),
  `dark`, or `no_signal`. Frames that aren't the sky are hidden from rankings so
  they can't skew them.
- **How good is the sunset?** A 0–100 score plus a one-line reason, shown next to
  the color (HSV) score. It never replaces it.

It reads captures from InfluxDB and writes `ai_view`, `ai_is_sunset`, `ai_score`,
`ai_reason` and `ai_model` back onto the same points. The pipeline's own fields
(`url`, `score`) and code are untouched. Everything runs on the NUC's CPU; nothing
leaves the machine.

## Run it on the NUC

```bash
# Start Ollama + the judge alongside the existing stack (first run downloads the
# model, ~3.3 GB for qwen3-vl:4b, before judging starts)
docker compose -f docker-compose.existing-infra.yml -f docker-compose.ai.yml up -d --build

# Follow along
docker compose -f docker-compose.existing-infra.yml -f docker-compose.ai.yml logs -f ai-judge
```

The `ai-judge` service then checks for new captures every 10 minutes (the last 2 days).

### 1. Pick a model first (recommended)

Compare two models on a sample, including days you know the camera was pointed at
a wall or tree. Nothing is written to InfluxDB; it saves an HTML contact sheet:

```bash
docker compose -f docker-compose.existing-infra.yml -f docker-compose.ai.yml run --rm \
  -v "$PWD/bakeoff:/app/bakeoff" ai-judge \
  python -m ai_judge bakeoff --camera btv_echo_cam --models qwen3-vl:4b,gemma3:4b \
  --sample 12 --dates 2025-07-04,2025-08-12
```

Open `bakeoff/bakeoff.html`, check which model's verdicts look right, and note its
seconds-per-photo in the log. To use the other model, set `AI_MODEL=gemma3:4b` in
`.env` (next to `IMAGE_BASE_URL`) and run `up -d` again.

### 2. Backfill history

Resumable: stop it any time, and re-running skips what's already judged.

```bash
# Each day's best shot only (the frames that matter for rankings), a few hours per camera
docker compose -f docker-compose.existing-infra.yml -f docker-compose.ai.yml run --rm ai-judge \
  python -m ai_judge backfill --camera btv_echo_cam --best-only

# Every capture (~3,500 for btv_echo_cam): run overnight, or leave it running for a few days
docker compose -f docker-compose.existing-infra.yml -f docker-compose.ai.yml run --rm ai-judge \
  python -m ai_judge backfill --camera btv_echo_cam
```

Cameras: `bolton_summit_cam`, `btv_echo_cam`, `wcax_tower_sunrise`, `wcax_tower_sunset`.

## In the dashboard

- **Calendar → Day tab:** "AI 78 · vivid pink clouds" under the score; captures that
  aren't the sky are dimmed and labeled.
- **Ranked Images:** days whose best shot isn't the sky are hidden behind a
  "Show N not-the-sky days" toggle.
- **Score Tracker:** a Color score / AI score toggle (the tooltip shows both).

Until a day has been judged, it looks exactly as before.

## Resource use

Ollama is capped at 6 GB RAM (`mem_limit` in `docker-compose.ai.yml`), judges one photo
at a time, and unloads the model 10 minutes after the last photo. Turn it all off with
`docker compose -f docker-compose.existing-infra.yml -f docker-compose.ai.yml stop ollama ai-judge`.

## Tests

`python -m unittest ai_judge.test_ai_judge` (uses a fake Ollama server; no model needed).
