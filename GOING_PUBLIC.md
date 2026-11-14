# Before the site goes public

From the audit of `claude/sunset-prediction` on 2026-11-14. Tick items off as they land.

## Decisions

- [x] **Admin is Tailscale-only.** `/admin*` and `/api/admin*` are never reachable from the public URL.
- [ ] **How the site is exposed.** Recommended: Cloudflare Tunnel (HTTPS, gzip, caching, rate limiting and a hidden home IP with almost no code). Alternatives: Tailscale Funnel, or port-forward + Caddy.
- [ ] **Display names** for the four cameras (`btv_echo_cam`, `bolton_summit_cam`, `wcax_tower_sunset`, `wcax_tower_sunrise`).

## Must fix

- [ ] **HTTPS in front of the dashboard.** Admin is HTTP Basic auth, so without TLS the password travels in clear text. The admin password is effectively root on the NUC (admin can rewrite the compose file and trigger a rebuild through a container holding `docker.sock`), and nothing limits password guessing.
- [ ] **Block `/admin*` and `/api/admin*` at the public edge**, so they only answer over Tailscale. (`/api/admin/status` is called by every page; it must fail quietly, which the frontend already handles.)
- [ ] **Replace Flask's development server** (`app.run` at the bottom of `html_project/backend.py`) with waitress or gunicorn: one line in `html_project/requirements.txt`, one `command:` in the compose file. Keep it to one process, since the data cache is in memory.
- [ ] **Don't publish InfluxDB (8086, no auth) or the image server (8080) to the internet.** Fine behind a tunnel; wide open with a port-forward. Bind them to the Tailscale IP or drop the `ports:` entries if nothing outside Docker needs them.
- [ ] **Fix link previews behind a proxy.** `og:image` is built from `request.host_url`, which becomes the internal address. Add Flask's `ProxyFix` or a `PUBLIC_URL` setting.
- [ ] **Rate-limit the public write endpoints.** `/api/vote` can be stuffed by a script. `/api/camera-requests` stops at 50 pending, so one script can fill it and block real requests. Do it at the edge (Cloudflare rule) rather than in code.
- [ ] **Set real secrets in `.env` on the NUC:** `ADMIN_PASSWORD` (long, random) and `REBUILD_TOKEN` (defaults to `changeme`).
- [ ] **Merge `claude/sunset-prediction` into `main`** (76+ commits ahead) and deploy from it.

## Should fix

- [ ] **`/api/data` returns a camera's whole history in one response**: every capture with every weather field, uncompressed, growing daily. Measure it on the NUC first. Gzip (free with Cloudflare) is the cheap fix; splitting ranked days from all captures is the later one.
- [ ] **Cache stampede.** When the 5-minute cache expires, every concurrent request re-queries InfluxDB. One lock around `fetch_camera_data_cached` fixes it.
- [ ] **Long-lived cache headers for the built JS/CSS.** The filenames are hashed, so `/assets/*` can be `immutable`.
- [ ] **Validate admin config writes.** A newline in a field injects extra lines into the camera's `.env` file, and the tag in the PUT/DELETE URL isn't checked against the tag pattern. Admin-only, so low risk.
- [ ] **Backups** of the `influxdb-storage` volume and `~/Pictures`.
- [ ] **Healthcheck** on the dashboard container, and pin `ollama/ollama` to a version instead of `latest`.
- [ ] **Run the backend tests** (`python -m unittest html_project.test_backend ...`); they were not run during the audit.

## UI

- [ ] **Say what the site is.** It opens straight on the calendar with no context: one intro line or an About blurb.
- [ ] **Camera display names** in the dropdown and in shared-link titles instead of raw tags.
- [ ] **Page metadata:** a real title, favicon, meta description, `robots.txt`.
- [ ] **Remove the developer error text** shown to visitors ("is the Flask backend running on :8502?" in `frontend/src/api.js`).
- [ ] **Hide "Admin log in"** from the public sidebar; go to `/admin` directly over Tailscale.
- [ ] **Lazy-load the admin pages** (HSV tuner, Config, Archive, My ranking) so visitors don't download them; the main bundle is about 540 KB.
- [ ] **Credit the camera owners** (WCAX, the YouTube streams) with a link per camera.
- [ ] **Unknown URLs return 200** with a "Page not found" page. Minor.

## Check after launch

- [ ] The public URL loads over HTTPS and `/admin` and `/api/admin/ping` are refused there.
- [ ] Admin still works over Tailscale.
- [ ] A shared `/sunset/<camera>/<date>` link unfurls with its photo.
- [ ] Ports 8086 and 8080 don't answer from outside the tailnet.
