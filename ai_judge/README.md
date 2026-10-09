# ai_judge: local AI sunset judge + re-ranker

An optional sidecar to the capture pipeline. For every capture it asks a small
vision model running locally in [Ollama](https://ollama.com) two things:

- **Is this actually the sky?** `sky`, `obstructed` (wall, tree, wrong preset),
  `dark`, or `no_signal`.
- **How good is the sunset?** A 0–100 score plus a one-line reason, shown next to
  the color (HSV) score. It never replaces it.

It reads captures from InfluxDB and writes `ai_view`, `ai_is_sunset`, `ai_score`,
`ai_reason` and `ai_model` back onto the same points. The pipeline's code and its
`url`/`score` fields are untouched. Everything runs on the NUC's CPU; nothing
leaves the machine.

**The gate:** a capture that isn't the sky counts as 0 in the dashboard. Once all of a
day's captures are judged, if the pipeline's best shot turned out not to be the sky,
the judge re-picks the day's best shot from its real-sky captures by HSV score and
regenerates the ranked image and histogram with the pipeline's own functions. If none
of the day's captures show the sky, that day isn't ranked at all. This happens within
~10 minutes of the day's capture run finishing, without changing the capture pipeline.

## Run it on the NUC

```bash
# Start Ollama + the judge alongside the existing stack (first run downloads the
# model, ~3.3 GB for qwen3-vl:4b, before judging starts)
docker compose -f docker-compose.existing-infra.yml -f docker-compose.ai.yml up -d --build

# Follow along
docker compose -f docker-compose.existing-infra.yml -f docker-compose.ai.yml logs -f ai-judge
```

The `ai-judge` service then checks for new captures every 10 minutes (the last 2 days)
and applies the gate.

The photos folder defaults to `/home/dlavoie/Pictures`; set `PICTURES_PATH` in `.env`
if it lives elsewhere (re-ranking writes new ranked images next to the photos).

For the commands below, an alias saves typing:

```bash
alias judge='docker compose -f docker-compose.existing-infra.yml -f docker-compose.ai.yml run --rm ai-judge python -m ai_judge'
```

Every command takes `--camera <tag>` or `--camera all`, and `backfill`/`rerank` take
`--since YYYY-MM-DD` (inclusive) and `--before YYYY-MM-DD` (exclusive), in the cameras'
local dates. Cameras: `bolton_summit_cam`, `btv_echo_cam`, `wcax_tower_sunrise`,
`wcax_tower_sunset`.

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
judge backfill --camera all --best-only                                        # each day's best shot: a few hours
judge backfill --camera btv_echo_cam --since 2025-07-01 --before 2025-08-01    # one month, every capture
judge backfill --camera all                                                    # everything (~6,000 captures): days
```

`--best-only` is enough to hide not-the-sky days from the rankings. To have the gate
re-pick a better best shot for those days, it needs the rest of that day judged too,
so backfill those days (or everything) without `--best-only`, then run `rerank`.

### 3. Re-rank (non-interactive)

`rerank` re-picks each day's best shot from InfluxDB and regenerates its ranked image +
histogram with the pipeline's functions. It skips captures the AI judged not the sky,
and removes the ranking of days with no sky at all. Always try `--dry-run` first.

```bash
judge rerank --camera all --dry-run                                        # what would change
judge rerank --camera btv_echo_cam --since 2025-07-01 --before 2025-08-01
judge rerank --camera all --rescore        # recompute every HSV score with the current sunset_process.py first
judge rerank --camera all --ignore-ai      # HSV score only (the old behavior)
judge rerank --camera all --fill-missing   # also rank days the pipeline never ranked
```

Before any AI judgments, a dry run over all history reports all 563 ranked days as
"unchanged" (it agrees with every pick the pipeline made) and 37 days that were never
ranked, which are skipped unless you pass `--fill-missing`.

Unlike `tests/re_rank_sunsets.py`, it never deletes captures, so AI judgments are kept.
That script deletes every point for the camera before re-pushing them, which would wipe
the AI fields (they'd need a re-backfill).

## In the dashboard

- **Calendar → Day tab:** "AI 78 · vivid pink clouds" under the score; captures that
  aren't the sky are dimmed, labeled, and count as 0.
- **Ranked Images:** days whose best shot isn't the sky are hidden behind a
  "Show N not-the-sky days" toggle.
- **Score Tracker:** a Color score / AI score toggle (the tooltip shows both).

Until a day has been judged, it looks exactly as before.

## Resource use

Ollama is capped at 6 GB RAM (`mem_limit` in `docker-compose.ai.yml`), judges one photo
at a time, and unloads the model 10 minutes after the last photo. Turn it all off with
`docker compose -f docker-compose.existing-infra.yml -f docker-compose.ai.yml stop ollama ai-judge`.

## Tests

`python -m unittest ai_judge.test_ai_judge ai_judge.test_rerank` (a fake Ollama server, a
fake InfluxDB and a fake pipeline; no model or database needed).
