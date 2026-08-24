# sunset-code

An automated pipeline that captures sunset photos from YouTube livestream cams, scores how "good" each sunset looks using HSV color analysis, correlates scores with weather data, and displays everything in a Streamlit dashboard.

## How it works

1. **Capture** — `sunset_code/helpers/get_photo.py` grabs a frame from a YouTube livestream (via `yt_dlp` + OpenCV) at fixed intervals around sunset (2h/1h/45m/30m/15m/5m before, at sunset, and 5m/15m/30m after), computed by `sunset_code/helpers/helpers.py` (`sunset_time`) using `astral` for the local sunset time at each camera's lat/lon.
2. **Score** — `sunset_code/helpers/sunset_process.py` (`rank_sunset`) converts the sky half of each image to HSV and scores it (0–100) based on saturation-weighted red/orange/yellow/pink hue coverage. It also produces an annotated overlay image showing the color masks and ratios.
3. **Rank & visualize** — `sunset_code/helpers/generate_ranked_image.py` renders the best-scoring capture of the day as an annotated PNG plus an HSV histogram plot.
4. **Store** — `sunset_code/helpers/helpers.py` (`influxdb_push`) writes each photo's URL, score, and label as a point in InfluxDB (measurement `sunset_images`), tagged by `camera`.
5. **Weather enrichment** — `sunset_code/helpers/open_metro_weater_api.py` (`weather_fetch`) fetches hourly weather (temperature, humidity, cloud cover, precipitation, visibility, etc.) from the Open-Meteo API. Currently disabled: the call and fields are commented out in `helpers.py`'s `influxdb_push`, so weather fields in InfluxDB/the dashboard are not populated.
6. **Entry point** — `sunset_code/__main__.py` reads camera config from environment variables (see `config/*.env`), sleeps until each capture interval, captures + scores + pushes each frame, then generates and pushes the day's best-ranked image.
7. **Re-rank (batch)** — `tests/re_rank_sunsets.py` is an interactive offline job that re-scores all previously captured images for a chosen camera, picks the best-scoring interval per day, regenerates the ranked/histogram images, and re-pushes everything to InfluxDB.
8. **Dashboard** — `streamlit_project/app.py` is a multi-page Streamlit app reading from InfluxDB, with a camera-selector dropdown in the sidebar:
   - **Sunset Calendar** (`sunset_gallery.py`) — grid gallery of all captured images with an inline expand/detail view per day.
   - **Ranked Images** (`ranking_tab.py`) — sortable list of the best-scored image per day, side-by-side with its raw and HSV-mask versions.
   - **Score Tracker** (`score_tracker.py`) — Plotly line chart of scores over time, clickable to inspect individual captures.
   - **HSV Tuner** (`hsv_tuner.py`) — interactive tool for tuning the HSV thresholds used by the scoring algorithm, against reference images, gallery images, or an uploaded photo.
9. **HTML mirror (experimental)** — `html_project/` is a hand-rolled, no-build static HTML/CSS/JS rebuild of the exact same four pages, backed by a small Flask API instead of Streamlit reruns. Built for fun / to compare with Streamlit on slow connections (see below).

## Project layout

```
docker-compose.yml                 # full self-contained stack (see "Docker Compose" below)
.env.example                       # copy to .env -- sets IMAGE_BASE_URL for compose

sunset_code/
  __main__.py                      # capture loop entrypoint (per-camera, via config/*.env)
  Dockerfile                       # build context = repo root (needs sunset_code importable)
  entrypoint.sh                    # loops __main__ daily so the container stays running
  requirements.txt
  helpers/
    get_photo.py                   # grab + save a frame from the livestream
    sunset_process.py              # HSV-based sunset scoring (rank_sunset)
    helpers.py                     # sunset_time() interval scheduling, influxdb_push()
    open_metro_weater_api.py       # Open-Meteo weather lookup (weather_fetch)
    generate_ranked_image.py       # renders the annotated/scored image + HSV histograms

config/
  bolton_summit_cam.env            # YOUTUBE_URL / CAMERA_TAG / LAT / LON / ALTITUDE / TIMEZONE
  btv_echo_cam.env                 # same, for a second camera

streamlit_project/
  app.py                          # dashboard entrypoint / navigation / InfluxDB query + cache
  sunset_gallery.py               # "Sunset Calendar" page
  ranking_tab.py                  # "Ranked Images" page
  score_tracker.py                # "Score Tracker" page
  hsv_tuner.py                    # "HSV Tuner" page
  stock_images/                   # reference images for the HSV tuner
  Dockerfile
  requirements.txt

tests/
  re_rank_sunsets.py               # interactive batch re-scoring / re-ranking job
  sunset_process_testing.py        # scratch/testing for the scoring algorithm
  EXAMPLE_IMAGES/                  # sample captured images

html_project/
  backend.py                       # Flask API: /api/cameras, /api/data, /api/image-proxy
  Dockerfile
  requirements.txt
  static/
    index.html                    # sidebar (camera select + nav) + main content area
    style.css
    app.js                        # router: fetches data, switches between the 4 pages
    hsv.js                        # canvas-based HSV masking shared by the tuner page
    pages/
      gallery.js                  # "Sunset Calendar" page
      ranking.js                  # "Ranked Images" page
      scoretracker.js             # "Score Tracker" page (uses Plotly.js via CDN)
      hsvtuner.js                 # "HSV Tuner" page
    stock_images/                 # copied from streamlit_project/stock_images
```

## Running it

### Docker Compose (full stack, recommended for a new machine)

Spins up everything the `html_project/` dashboard needs from scratch: InfluxDB, an image HTTP server, one capture container per camera in `config/`, and the dashboard itself.

```bash
cp .env.example .env
# edit .env: set IMAGE_BASE_URL to an address other devices can actually reach
# (your Tailscale IP, LAN IP, or hostname -- not "localhost" unless you're
# only ever viewing the dashboard from this same machine)

docker compose up -d --build
```

Then open `http://<host>:8502/`. To add a third camera, drop a new `config/<name>.env` file and add a matching `capture-<name>` service in `docker-compose.yml` (copy one of the existing `capture-*` blocks).

#### Using an existing InfluxDB and photos folder

If you already have InfluxDB running on the host and photos stored locally (not in Docker volumes), copy the example override file and customize it:

```bash
cp docker-compose.override.yml.example docker-compose.override.yml
# edit docker-compose.override.yml:
#   - change /home/YOUR_USER/Pictures/sunset_images to your actual photos path
```

Docker Compose automatically merges `docker-compose.override.yml` with the base config. The override disables the containerized InfluxDB and points services to your existing setup via `host.docker.internal`. The override file is gitignored so your local paths won't be committed.

Notes on how this fits together:
- `INFLUXDB_HOST`/`INFLUXDB_PORT` are set to Docker's internal service name (`influxdb`) for server-to-server traffic (capture containers and the dashboard backend talking to InfluxDB) — this never needs to be reachable from a browser.
- `IMAGE_BASE_URL` is different: it gets baked into every image URL written to InfluxDB, and those URLs are loaded directly by browsers (`<img src="...">`), so it must be an address reachable from wherever you're viewing the dashboard, not a Docker-internal name.
- Captured images live in the `pictures_data` named volume, shared between the capture containers (write) and `imageserver` (serve). InfluxDB's data lives in the `influxdb_data` volume. Both persist across `docker compose down`/`up`; use `docker compose down -v` to wipe them.
- `sunset_code`'s capture loop (`__main__.py`) normally runs once per day via a systemd timer and exits; `entrypoint.sh` wraps it in a loop (run → sleep 1h → repeat) so the container stays up and naturally picks up the next day's cycle instead of needing cron/systemd inside the container.

### Capture + scoring pipeline (`sunset_code/`, without Docker)

Runs once a day per camera, sleeping until each capture interval before grabbing a frame, scoring it, and pushing to InfluxDB:

```bash
set -a; source config/bolton_summit_cam.env; set +a
python -m sunset_code
```

Set up one systemd service (or scheduled task) per camera `.env` file to run multiple cams. Configurable via environment variables (all optional, default to the original bare-metal deployment's values): `INFLUXDB_HOST` (default `localhost`), `INFLUXDB_PORT` (default `8086`), `PICTURES_DIR` (default `~/Pictures`, images land under `<PICTURES_DIR>/sunset_images/<camera_tag>/<year>/<month>/<day>/`), and `IMAGE_BASE_URL` (default `http://100.107.153.41:8080`, the base URL baked into each image's InfluxDB record).

Dependencies: `sunset_code/requirements.txt`.

### Batch re-ranking (`tests/re_rank_sunsets.py`)

Interactive CLI (uses `simple_term_menu`) that lets you pick a camera and re-score its whole image history, or just one month:

```bash
python tests/re_rank_sunsets.py
```

This deletes and re-writes all InfluxDB points for the selected camera.

### Dashboard (`streamlit_project/`)

```bash
cd streamlit_project
pip install -r requirements.txt
streamlit run app.py
```

Or via Docker:

```bash
cd streamlit_project
docker build -t sunset-dashboard .
docker run -p 8501:8501 sunset-dashboard
```

The dashboard connects to InfluxDB at `100.107.153.41:8086` (hardcoded in `app.py`) and expects images to be served over HTTP from that same host (e.g. `python3 -m http.server 8080` from the `Pictures` directory, matching the URL built in `helpers.py`'s `influxdb_push`).

### HTML mirror (`html_project/`)

Same InfluxDB host, same image server — just a different frontend, served on its own port so it can run side by side with the Streamlit app:

```bash
cd html_project
pip install -r requirements.txt
python backend.py
```

Then open `http://<host>:8502/`. There's no build step — `static/` is plain HTML/CSS/ES modules served directly by Flask. The four pages (`pages/gallery.js`, `pages/ranking.js`, `pages/scoretracker.js`, `pages/hsvtuner.js`) are 1:1 ports of the Streamlit pages of the same purpose, reading from the same `/api/data` JSON the Flask backend builds with the same query/grouping logic as `app.py`'s `fetch_camera_data`. The HSV tuner does real per-pixel HSV masking on `<canvas>` (see `hsv.js`) instead of OpenCV; gallery-sourced images are fetched through `/api/image-proxy` (a same-origin proxy) so the canvas can read their pixels without hitting cross-origin restrictions. Its InfluxDB connection is configurable via `INFLUXDB_HOST`/`INFLUXDB_PORT` (default `100.107.153.41`/`8086`, matching the original deployment).

## Notes / known rough edges

- `streamlit_project/app.py` and `tests/re_rank_sunsets.py` still hardcode the InfluxDB host (`100.107.153.41`) and, for the latter, the local photo directory (`/home/dlavoie/Pictures/...`) — only `sunset_code/`'s capture pipeline and `html_project/`'s backend were made configurable (via `INFLUXDB_HOST`, `INFLUXDB_PORT`, `PICTURES_DIR`, `IMAGE_BASE_URL`) as part of getting the Docker Compose setup working on other machines.
- Weather enrichment (`open_metro_weater_api.py`) is wired up but currently disabled — its call and all weather fields are commented out in `helpers.py`, so `ranking_tab.py`'s weather lookups always resolve to `N/A`.
- The Sunset Calendar gallery renders every historical capture at full resolution with no pagination or thumbnail generation, which is the main cause of it feeling sluggish as the image history grows — see the note below.
- `.cache.sqlite` is the `requests_cache` cache used by the weather API client.

## Streamlit gallery performance

The Sunset Calendar page (`sunset_gallery.py`) calls `st.image()` directly on the full-resolution capture URL for every thumbnail in the grid, for every day ever captured, all in one page render — no thumbnail images, no pagination, no lazy-loading. A single direct image request is fast because it's one HTTP fetch; the gallery is slow because it's doing that same full-resolution fetch hundreds of times on every load/rerun. A custom C++ or hand-rolled HTML site isn't needed to fix this — the fix is:

1. Generate small thumbnail JPEGs at capture/re-rank time (or on-demand via a tiny resizing endpoint) and point the grid at those instead of the originals.
2. Paginate the gallery by month/day instead of loading the entire history at once.
3. Let the browser lazy-load offscreen images (native `loading="lazy"` on the `<img>` tags, e.g. in the thumbnail-strip HTML that's already hand-written).

`html_project/` (above) already applies fix #3 — its gallery grid uses native `loading="lazy"` on every `<img>`, so offscreen thumbnails aren't fetched at all until scrolled into view, which helps a lot on a phone connecting over a relayed Tailscale link. It still doesn't paginate or generate real thumbnails, so images that *are* visible are still full-resolution — worth doing #1/#2 there too if it needs to hold up over a full season of captures.
