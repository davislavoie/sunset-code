# ai_judge: sidecar that fills in captures and re-picks best shots

An optional sidecar to the capture pipeline. The **HSV color score decides** which
capture is a day's best shot; ai_judge adds what the score can't know:

- **Thumbs up / down** (Calendar → Day tab, under each capture). 👎 = this shot never
  counts; tick **all shots like this** and every near-identical shot from that camera is
  ruled out too (e.g. Bolton's lift-tower close-up preset). 👍 = this is the day's pick.
  Within ~10 minutes the judge re-picks affected days and regenerates their ranked image
  and histogram with the pipeline's own functions. A day with nothing left isn't ranked.
- **Weather** for every capture (Open-Meteo, the hour nearest the capture, at the
  camera's LAT/LON): `temperature_2m`, `cloud_cover_low/mid/high/total`, `visibility`,
  ... plus low/mid/high cloud **toward the sunset** (sunrise, for a sunrise camera) at 50,
  150 and 300 km (`path50_cloud_cover_low`, ...). A bank of low cloud out there blocks the
  light: on ~480 ranked days, days with >=70% low cloud along that line had a median best
  score of 7, vs 31 with it clear. Groundwork for predicting sunsets from the early shots + weather. New captures get
  it at capture time (`helpers.influxdb_push` → `weather_fetch`); ai_judge backfills
  history (`judge weather --camera all`) and fills any capture that missed it. Shown on
  the Calendar Day tab.
- **View fingerprints** (`view_fp`), used by "all shots like this".
- **Optional local AI** (Ollama, off unless `AI_MODEL` is set). It only rules out frames
  it calls dark or "no signal"; its 0-100 score is shown for information.

Everything is merged onto the capture's own InfluxDB point; the pipeline's code and its
`url`/`score` fields are untouched. The rule for what can't win lives in
`store.exclusion` (and the same function in `html_project/backend.py`).

## Run it on the NUC

```bash
# Start the judge alongside the existing stack. The first pass fills in weather and
# fingerprints for all of history (a few minutes), then it checks every 10 minutes.
docker compose -f docker-compose.existing-infra.yml -f docker-compose.ai.yml up -d --build

# Follow along
docker compose -f docker-compose.existing-infra.yml -f docker-compose.ai.yml logs -f ai-judge
```

To also run the local AI, add `AI_MODEL=qwen3-vl:4b` to `.env` (first run downloads
~3.3 GB) and `up -d` again.

It uses the same photos folder as the capture containers (`${HOME}/Pictures`); re-ranking
writes new ranked images next to the photos.

For the commands below, an alias saves typing:

```bash
alias judge='docker compose -f docker-compose.existing-infra.yml -f docker-compose.ai.yml run --rm ai-judge python -m ai_judge'
```

Every command takes `--camera <tag>` or `--camera all`, and `backfill`/`rerank` take
`--since YYYY-MM-DD` (inclusive) and `--before YYYY-MM-DD` (exclusive), in the cameras'
local dates. Cameras: `bolton_summit_cam`, `btv_echo_cam`, `wcax_tower_sunrise`,
`wcax_tower_sunset`.

### Weather and fingerprints by hand

`watch` does both automatically; these are for a specific range or a redo.

```bash
judge weather --camera all                                   # all of history: one request per camera
judge weather --camera all --since 2026-09-01 --refill       # fetch again
judge views --camera all                                     # fingerprint + apply "all shots like this" now
```

### 1. Pick an AI model (only if you turn the AI on)

Compare two models on a sample. Nothing is written to InfluxDB; it saves an HTML
contact sheet. Without `--dates` it samples the highest-, lowest- and random-scoring
captures (where the color score is most often fooled):

```bash
docker compose -f docker-compose.existing-infra.yml -f docker-compose.ai.yml run --rm \
  -v "$PWD/bakeoff:/app/bakeoff" ai-judge \
  python -m ai_judge bakeoff --camera btv_echo_cam --models qwen3-vl:4b,gemma3:4b --sample 12
```

Better still, add real days you know the camera was pointed at a wall or tree (spot
them in the dashboard's Calendar → Month view) with `--dates YYYY-MM-DD,YYYY-MM-DD`.
It warns about any date with no captures for that camera.

Open `bakeoff/bakeoff.html`, check which model's verdicts look right, and note its
seconds-per-photo in the log. To use the other model, set `AI_MODEL=gemma3:4b` in
`.env` (next to `IMAGE_BASE_URL`) and run `up -d` again.

### 2. Backfill history

Resumable: stop it any time, and re-running skips what's already judged.

```bash
judge backfill --camera all --best-only                                        # each day's best shot: a few hours
judge backfill --camera all --since 2026-09-01 --before 2026-09-08            # one week, every capture (all 4 cameras)
judge backfill --camera all                                                    # everything (~6,000 captures): days
```

`--best-only` is enough to catch dark / no-signal best shots; `watch` then re-picks
those days.

### 3. Re-rank (non-interactive)

`rerank` re-picks each day's best shot from InfluxDB and regenerates its ranked image +
histogram with the pipeline's functions, applying the thumbs / bad-view / dark rules, and
removes the ranking of days where nothing can win. Always try `--dry-run` first.

```bash
judge rerank --camera all --dry-run                                        # what would change
judge rerank --camera all --since 2026-09-01 --before 2026-09-08
judge rerank --camera all --rescore        # recompute every HSV score with the current sunset_process.py first
judge rerank --camera all --hsv-only       # HSV score only, ignoring thumbs (the old behavior)
judge rerank --camera all --fill-missing   # also rank days the pipeline never ranked
```

Before any AI judgments, a dry run over all history reports all 563 ranked days as
"unchanged" (it agrees with every pick the pipeline made) and 37 days that were never
ranked, which are skipped unless you pass `--fill-missing`.

Unlike `tests/re_rank_sunsets.py`, it never deletes captures, so thumbs, weather and AI
fields are kept. That script deletes every point for the camera before re-pushing them,
which would wipe them all.

## In the dashboard

- **Calendar → Day tab:** 👍 / 👎 (and "all shots like this") under each capture; shots
  that don't count are dimmed, labeled with why, and score 0.
- **Admin → Archive:** every shot that doesn't count, by day and reason, with 👍/👎 to undo.
- **Ranked Images:** a day whose best shot doesn't count (before the judge re-picks it) is
  hidden behind a "Show N ruled-out days" toggle.
- **Score Tracker:** a Color score / AI score toggle when the AI is on.

The thumbs buttons call `/api/admin/thumb`; if the dashboard goes public, keep
`/api/admin/*` behind auth like the other admin routes.

## Resource use

Ollama is capped at 6 GB RAM (`mem_limit` in `docker-compose.ai.yml`), judges one photo
at a time, and unloads the model 10 minutes after the last photo. Turn it all off with
`docker compose -f docker-compose.existing-infra.yml -f docker-compose.ai.yml stop ollama ai-judge`.

## Tests

`python -m unittest ai_judge.test_ai_judge ai_judge.test_rerank` (a fake Ollama server, a
fake InfluxDB and a fake pipeline; no model or database needed).
