# ai_analysis: sidecar that fills in captures and rescores them

An optional sidecar to the capture pipeline. The **HSV color score decides** which
capture is a day's best shot; ai_analysis adds what the score can't know:

- **Thumbs up / down** (Calendar → Day tab, under each capture). 👎 = this shot never
  counts; tick **all shots like this** and every near-identical shot from that camera is
  ruled out too (e.g. Bolton's lift-tower close-up preset). 👍 = this is the day's pick.
  The dashboard picks each day's best shot from the scores as it reads them, so a vote
  shows straight away. A day with nothing left isn't ranked.
- **Weather** for every capture (Open-Meteo, the hour nearest the capture, at the
  camera's LAT/LON): `temperature_2m`, `cloud_cover_low/mid/high/total`, `visibility`,
  ... plus low/mid/high cloud **toward the sunset** (sunrise, for a sunrise camera) at 8,
  25 and 50 miles (13 / 40 / 80 km: `path13_cloud_cover_low`, ...). A bank of low cloud out
  there blocks the light: on ~480 ranked days, days with >=70% low cloud 50-300 km along that
  line (the earlier `path50_`/`path150_`/`path300_` readings) had a median best score of 7,
  vs 31 with it clear. Groundwork for predicting sunsets from the early shots + weather. New captures get
  it at capture time (`helpers.influxdb_push` → `weather_fetch`); ai_analysis backfills
  history (`ai weather --camera all`) and fills any capture that missed it. Shown on
  the Calendar Day tab.
- **Sunset forecast** on every pre shot (`predicted_pct/score/call`, and `predicted_with`: which
  input set was used). Inputs: the stored weather, the **ICON** model's path cloud
  (`path{13,40,80}_icon_cloud_cover_*`, fetched next to best_match), **GOES-East** observed cloud
  toward the sun (`goes_over/near/far/fan`, from NOAA's public satellite bucket, ~0.7 MB and ~1 s per
  shot), and the HSV scores so far. A shot missing ICON or GOES falls back to the plain weather line.
  `watch` fills recent shots; `ai goes --camera all --since YYYY-MM-DD` backfills history.
- **View fingerprints** (`view_fp`), used by "all shots like this".
- **Glass lake** (btv_echo_cam only): `mirror_score` (how well the frame's lower part mirrors
  the sky above some horizon row) and `glass_lake` (score >= 0.35, about 4 % of days). Such
  shots show a green "Glass lake +5" bubble and get +5 (+8 at >= 0.45) when picking the day's
  best and in the displayed score; the HSV `score` itself is unchanged. `watch` fills it;
  `ai reflect --camera all` does history by hand.
- **Sky read** (Ollama, `SKY_MODEL`, default qwen3-vl:4b): the vision model reads the band of light
  and cloud on the 1h, 45m, 30m and 15m shots, for the forecast. `ai sky --camera all` does history.

Everything is merged onto the capture's own InfluxDB point; the pipeline's code and its
`url`/`score` fields are untouched. The rule for what can't win lives in
`store.exclusion` (and the same function in `html_project/backend.py`).

## Run it on the NUC

```bash
# ai-analysis starts with the rest of the stack (one compose file, one shared image). The first
# pass fills in weather and fingerprints for all of history (a few minutes), then it checks every 10 minutes.
docker compose -f docker-compose.existing-infra.yml up -d --build --remove-orphans

# Follow along
docker compose -f docker-compose.existing-infra.yml logs -f ai-analysis
```

It uses the same photos folder as the capture containers (`${HOME}/Pictures`): `rescore`
reads the photos, `drop-ranked --delete` removes the old ranked PNGs.

For the commands below, an alias saves typing:

```bash
alias ai='docker compose -f docker-compose.existing-infra.yml run --rm ai-analysis python -m ai_analysis'
```

Every command takes `--camera <tag>` or `--camera all`, and `rescore` takes
`--since YYYY-MM-DD` (inclusive) and `--before YYYY-MM-DD` (exclusive), in the cameras'
local dates. Cameras: `bolton_summit_cam`, `btv_echo_cam`, `wcax_tower_sunrise`,
`wcax_tower_sunset`.

### Weather and fingerprints by hand

`watch` does both automatically; these are for a specific range or a redo.

```bash
ai weather --camera all                                   # all of history: one request per camera
ai weather --camera all --since 2026-09-01 --refill       # fetch again
ai views --camera all                                     # fingerprint + apply "all shots like this" now
```

### Rescore after changing the score

After a change to `sunset_code/helpers/sunset_process.py` or `hsv_score.json`, `rescore` recomputes
every capture's HSV score, its breakdown and its histograms, and writes them onto the same points
(InfluxDB merges fields), so thumbs, weather and forecast fields are kept and nothing is deleted. No
images are made: the dashboard picks each day's best shot from the scores. About 40 ms a photo.

```bash
ai rescore --camera all --dry-run                                  # how much scores would move
ai rescore --camera all --since 2026-09-01 --before 2026-09-08
ai rescore --camera all
```

The pipeline used to save a ranked image and histogram PNG for each day's best shot (11_ranked /
12_histogram points). The dashboard no longer uses them; list or remove them with:

```bash
ai drop-ranked --camera all             # how many
ai drop-ranked --camera all --delete    # remove the points and their PNGs
```

## In the dashboard

- **Calendar → Day tab:** 👍 / 👎 (and "all shots like this") under each capture; shots
  that don't count are dimmed, labeled with why, and score 0.
- **Admin → Archive:** every shot that doesn't count, by day and reason, with 👍/👎 to undo.

The thumbs buttons call `/api/admin/thumb`; if the dashboard goes public, keep
`/api/admin/*` behind auth like the other admin routes.

## Resource use

Ollama is capped at 6 GB RAM (`mem_limit` in `docker-compose.existing-infra.yml`), reads one photo
at a time, and unloads the model 10 minutes after the last photo. Turn it all off with
`docker compose -f docker-compose.existing-infra.yml stop ollama ai-analysis`.

## Tests

`python -m unittest ai_analysis.test_ai_analysis ai_analysis.test_rescore` (a fake Ollama server, a
fake InfluxDB and a fake scorer; no model or database needed).
