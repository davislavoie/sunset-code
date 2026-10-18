# sunset-code

Captures sunset (and sunrise) frames from YouTube livestream cams around Burlington, VT, scores how good each one looks with HSV color analysis, stores everything in InfluxDB with the weather at capture time, and shows it in a React web dashboard.

Cameras (one `config/<tag>.env` each): `bolton_summit_cam`, `btv_echo_cam`, `wcax_tower_sunrise`, `wcax_tower_sunset`.

## How it works

1. **Capture** (`sunset_code/`). `__main__.py` reads one camera's config from env vars, computes that day's sunset or sunrise (`MODE`) with `astral`, and sleeps until each interval (2h, 1h, 45m, 30m, 15m, 5m before, at the event, then 5m, 15m, 30m after). At each one `helpers/get_photo.py` grabs a frame with `yt_dlp` + OpenCV.
2. **Score**. `helpers/sunset_process.py` (`rank_sunset`) converts the sky (top half) to HSV and scores it 0 to 100 from saturation-weighted red, orange, yellow and pink coverage times a cloud-contrast factor, soft-capped. Every number is in `helpers/hsv_score.json` (the dashboard reads it too). It returns the score's breakdown and the sky's HSV histograms with it.
3. **Store**. `helpers/helpers.py` (`influxdb_push`) writes each capture's URL, score, score breakdown and label to InfluxDB (histograms go in `sunset_hist`) (database and measurement `sunset_images`, tagged by `camera`), along with Open-Meteo weather (`helpers/open_metro_weater_api.py`): overhead cloud, temperature, visibility, and low/mid/high cloud at 8, 25 and 50 miles toward the sun. If the weather call fails the capture is still saved and `ai_analysis` fills it in later.
4. **Rank**. Nothing to do: the dashboard takes each day's highest-scoring capture as its best shot (thumbs and exclusions applied). The old ranked-image PNGs (`helpers/generate_ranked_image.py`) are turned off.
5. **AI analysis** (`ai_analysis/`, optional sidecar). Backfills weather and view fingerprints, applies the dashboard's thumbs up/down (a 👎 can rule out every shot with the same camera view), optionally asks a local Ollama vision model to rule out dark or "no signal" frames, and rescores stored captures after a score change (`python -m ai_analysis rescore`). See [`ai_analysis/README.md`](ai_analysis/README.md).
6. **Dashboard** (`html_project/`). Flask API (`backend.py`) plus a Vite + React app (`frontend/`).

## Dashboard pages

- **Sunset calendar**: day, week, month and year views. The Day tab opens on the latest sunset with its best shot, score, color breakdown, weather, and thumbs up/down per capture. Shots that don't count stay visible at 0% with a reason pill (Wrong view, Flagged, Too dark, No signal).
- **Ranked images**: best shot per day (highest score), sortable, with its color overlay and HSV histogram.
- **Score tracker**: scores over time, plus a Compare tab that plots any logged value (weather, time of best shot, ...) against any other with a trend line and Pearson r.
- **HSV tuner**: tune the scoring thresholds against reference images, gallery images or an upload.
- **Ranking explained**: interactive, in-browser version of the scorer (`frontend/src/scoring.js`).
- **Camera map**: Leaflet map with sun-direction lines and a yearly sunrise/sunset chart.
- **Compare**: any two sunsets side by side.
- **Admin** (`/admin/*`): Config (camera configs, add a compose service, trigger a rebuild), Scoring (color multipliers, written back into `sunset_process.py`), Archive (every capture that doesn't count, with a way to clear a thumbs down).

Every write goes through `/admin/*` in the UI and `/api/admin/*` in the API, so those paths can sit behind reverse-proxy auth if the site goes public. `/sunset/<camera>/<date>` is a shareable permalink with link-preview tags. Gallery images go through `/api/image-proxy` (locked to `IMAGE_BASE_URL`) so the canvas-based HSV tools can read their pixels.

## Project layout

```
sunset_code/            capture + scoring pipeline (one container per camera)
  helpers/              get_photo, sunset_process (+ hsv_score.json), helpers, open_metro_weater_api
  entrypoint.sh         loops __main__ daily so the container stays up
ai_analysis/               optional sidecar: weather backfill, fingerprints, thumbs, local AI, rescoring
html_project/
  backend.py            Flask: JSON API, image proxy, serves frontend/dist
  frontend/src/         React app: App.jsx (nav, routes), pages/, components/charts (bklit), scoring.js, hsv.js
config/                 one .env per camera: YOUTUBE_URL, CAMERA_TAG, LAT, LON, ALTITUDE, TIMEZONE, MODE
webhook.py              tiny token-protected endpoint the dashboard calls to run `docker compose up -d --build`
streamlit_project/      older Streamlit dashboard (superseded by html_project/, not in the compose files)
tests/                  sunset_process_testing.py (score + debug overlay for a few photos), example images
skills/                 vendored UI/animation design skills for Claude Code (not part of the app)

docker-compose.yml                  self-contained stack: InfluxDB + image server + 2 cameras + dashboard
docker-compose.existing-infra.yml   the NUC deployment: all 4 cameras, ai-analysis + Ollama, ~/Pictures, rebuild webhook
Dockerfile                          the one image every Python service runs (capture, ai-analysis, dashboard)
```

## Running it

### On the NUC (production)

The deployment uses an existing `influxdb-storage` volume and the photos in `~/Pictures`:

```bash
cp .env.example .env    # set IMAGE_BASE_URL to an address browsers can reach (Tailscale/LAN IP)
docker compose -f docker-compose.existing-infra.yml up -d --build
```

That starts everything, ai-analysis and Ollama included (add `--remove-orphans` after renaming a service). The local AI photo score stays off unless `AI_MODEL` is set in `.env` (e.g. `AI_MODEL=qwen3-vl:4b`). Set `REBUILD_TOKEN` in `.env` too; it defaults to `changeme`.

Dashboard: `http://<host>:8502/`. Images: `http://<host>:8080/`.

### Fresh machine

```bash
cp .env.example .env
docker compose up -d --build
```

This uses Docker volumes for InfluxDB and photos and only runs the two original cameras. To point it at an existing InfluxDB and photos folder instead, copy `docker-compose.override.yml.example` to `docker-compose.override.yml` and edit the paths (it's gitignored).

Two addresses to keep straight: `INFLUXDB_HOST` is server-to-server and can be a compose service name, but `IMAGE_BASE_URL` is baked into every image URL in InfluxDB and loaded by browsers, so it must be reachable from wherever you view the dashboard.

### Adding a camera

Add a `config/<tag>.env` and a matching `capture-<tag>` service in the compose file (copy an existing block), or use **Admin → Config** in the dashboard, which can write both and trigger a rebuild.

### Without Docker

Capture, one camera:

```bash
set -a; source config/bolton_summit_cam.env; set +a
python -m sunset_code
```

Optional env vars: `INFLUXDB_HOST` (default `localhost`), `INFLUXDB_PORT` (`8086`), `PICTURES_DIR` (`~/Pictures`; images land in `<PICTURES_DIR>/sunset_images/<camera>/<year>/<month>/<day>/`), `IMAGE_BASE_URL` (`http://100.107.153.41:8080`).

Dashboard, for development (Flask on :8502, Vite on :5173 proxying `/api`):

```bash
cd html_project
pip install -r requirements.txt
IMAGE_BASE_URL=http://<image-host>:8080 python backend.py
```

```bash
cd html_project/frontend
npm install
npm run dev
```

On Windows PowerShell set `$env:IMAGE_BASE_URL = "http://<image-host>:8080"` first, and use `npm.cmd` if script execution is disabled. The backend's InfluxDB defaults to `100.107.153.41:8086`.

## Tests

```bash
cd html_project/frontend && npm test          # in-browser scorer (scoring.test.js)
python -m unittest ai_analysis.test_ai_analysis ai_analysis.test_rescore html_project.test_backend   # AI analysis, rescore, best-shot pick (no model or database needed)
```

## Known rough edges

- `streamlit_project/app.py` hardcodes the InfluxDB host (`100.107.153.41`).
- The scoring multipliers are read and written by regex against `sunset_process.py`, so reformatting that `score = (...)` line breaks the Admin → Scoring page.
- Galleries lazy-load images but don't paginate or generate thumbnails, so visible images are full resolution.
- `.cache.sqlite` is the `requests_cache` cache for the weather client.
