// Camera map with sun direction lines + yearly sunrise/sunset chart. Public:
// reads /api/camera-locations, which never includes stream URLs.

import { useEffect, useRef, useState } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import SunCalc from "suncalc";
import Dropdown from "../Dropdown.jsx";
import { Skeleton } from "../Skeleton.jsx";
import SunTimesChart from "../SunTimesChart.jsx";

// The pipeline samples clouds at these distances (8 / 25 / 50 mi) along the sun's bearing,
// rounded to 0.1 degree (sunset_code/helpers/open_metro_weater_api.py: PATH_KM, BEARING_STEP).
const PATH_KM = [13, 40, 80];
const MILES = { 13: 8, 40: 25, 80: 50 };
const BEARING_STEP = 0.1;
const RAY_KM = 100;

const SEASONS = [
  ["Summer", 5, 21], // June 21
  ["Winter", 11, 21], // Dec 21
  ["Spring", 2, 20], // Mar 20
  ["Fall", 8, 22], // Sep 22
];

const shortDate = (date) => date.toLocaleDateString(undefined, { month: "short", day: "numeric" });

function dayOfYearToDate(dayOfYear) {
  const date = new Date(new Date().getFullYear(), 0, 1);
  date.setDate(dayOfYear);
  return date;
}

function dateToDayOfYear(date) {
  return Math.floor((date - new Date(date.getFullYear(), 0, 0)) / (1000 * 60 * 60 * 24));
}

const modeOf = (config) => config.MODE || "sunset";
const colorOf = (config) => (modeOf(config) === "sunrise" ? "var(--sunrise)" : "var(--sun)");

/** [lat, lon] km along a compass bearing (degrees), on a sphere. */
function destination(lat, lon, bearingDeg, km) {
  const d = km / 6371, b = (bearingDeg * Math.PI) / 180;
  const p1 = (lat * Math.PI) / 180, l1 = (lon * Math.PI) / 180;
  const p2 = Math.asin(Math.sin(p1) * Math.cos(d) + Math.cos(p1) * Math.sin(d) * Math.cos(b));
  const l2 = l1 + Math.atan2(Math.sin(b) * Math.sin(d) * Math.cos(p1), Math.cos(d) - Math.sin(p1) * Math.sin(p2));
  return [(p2 * 180) / Math.PI, (l2 * 180) / Math.PI];
}

const formatTime = (d) => (d && !isNaN(d) ? d.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" }) : "—");

export default function CameraMap() {
  const [configs, setConfigs] = useState(null);
  const [date, setDate] = useState(() => new Date());
  const [chartCamera, setChartCamera] = useState("");

  useEffect(() => {
    fetch("/api/camera-locations")
      .then((res) => res.json())
      .then((list) => {
        const valid = list.filter((c) => c.LAT && c.LON);
        setConfigs(valid);
        if (valid.length) setChartCamera(valid[0].CAMERA_TAG); // auto-select first camera
      })
      .catch((err) => {
        console.error("Failed to load camera locations:", err);
        setConfigs([]);
      });
  }, []);

  return (
    <>
      <h1>Camera map</h1>

      <section>
        <h3>Camera locations</h3>
        <div className="map-container">
          <div className="map-controls">
            <div className="map-slider-control">
              <input
                type="range"
                min={1}
                max={365}
                aria-label="Date"
                value={dateToDayOfYear(date)}
                style={{ "--pct": `${((dateToDayOfYear(date) - 1) / 364) * 100}%` }}
                onChange={(e) => setDate(dayOfYearToDate(parseInt(e.target.value)))}
              />
              <span className="date-display">{shortDate(date)}</span>
            </div>
            <div className="map-date-shortcuts">
              <button className="btn btn-small" onClick={() => setDate(new Date())}>
                Today
              </button>
              {SEASONS.map(([name, month, day]) => (
                <button
                  key={name}
                  className="btn btn-small"
                  onClick={() => setDate(new Date(new Date().getFullYear(), month, day))}
                >
                  {name}
                </button>
              ))}
            </div>
          </div>
          {configs ? <LeafletMap configs={configs} date={date} /> : <Skeleton style={{ height: 400 }} />}
          <div className="map-legend">
            <div className="legend-item"><span className="legend-dot sunset"></span> Sunset</div>
            <div className="legend-item"><span className="legend-dot sunrise"></span> Sunrise</div>
            <div className="legend-item"><span className="legend-line"></span> Sun direction</div>
            <div className="legend-item"><span className="legend-point"></span> Cloud readings (8 / 25 / 50 mi)</div>
          </div>
        </div>
      </section>

      <hr />

      <section>
        <h3>Sunrise &amp; sunset times</h3>
        <div className="sun-data-layout">
          <div className="sun-chart-container">
            <div className="sun-chart-controls">
              <Dropdown
                label="Chart camera"
                placeholder="Select a camera…"
                value={chartCamera || null}
                onChange={setChartCamera}
                options={(configs || []).map((c) => ({ value: c.CAMERA_TAG, label: `${c.CAMERA_TAG} (${modeOf(c)})` }))}
              />
              <SunTimesReadout config={configs?.find((c) => c.CAMERA_TAG === chartCamera)} date={date} />
            </div>
            {configs && !configs.length ? (
              <div id="sun-times-chart">
                <div className="chart-empty">No cameras with valid coordinates</div>
              </div>
            ) : (
              <SunTimesChart config={configs?.find((c) => c.CAMERA_TAG === chartCamera)} date={date} />
            )}
          </div>
        </div>
      </section>
    </>
  );
}

// The chart's values for the slider's date, so moving the slider visibly updates this section.
function SunTimesReadout({ config, date }) {
  if (!config) return null;
  const t = SunCalc.getTimes(date, parseFloat(config.LAT), parseFloat(config.LON));
  return (
    <dl className="sun-readout">
      <div><dt>{shortDate(date)}</dt><dd /></div>
      <div><dt>Sunrise</dt><dd>{formatTime(t.sunrise)}</dd></div>
      <div><dt>Golden hour</dt><dd>{formatTime(t.goldenHour)}</dd></div>
      <div><dt>Sunset</dt><dd>{formatTime(t.sunset)}</dd></div>
    </dl>
  );
}

function LeafletMap({ configs, date }) {
  const elRef = useRef(null);
  const mapRef = useRef(null);
  const markersRef = useRef([]);
  const linesRef = useRef([]);
  const fittedRef = useRef(false);

  // Build the map and markers once per set of cameras.
  useEffect(() => {
    if (!configs.length) return;

    const avgLat = configs.reduce((sum, c) => sum + parseFloat(c.LAT), 0) / configs.length;
    const avgLon = configs.reduce((sum, c) => sum + parseFloat(c.LON), 0) / configs.length;

    const map = L.map(elRef.current, {
      center: [avgLat, avgLon],
      zoom: 4,
      zoomControl: true,
      closePopupOnClick: false,
    });
    mapRef.current = map;

    // OpenStreetMap tiles (free, no API key) - darkened via CSS
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
      maxZoom: 19,
      className: "dark-tiles",
    }).addTo(map);

    markersRef.current = configs.map((config) => {
      const icon = L.divIcon({
        className: "camera-marker",
        html: `<div class="marker-pin" style="--marker-color: ${colorOf(config)}">
          <div class="marker-pulse"></div>
          <div class="marker-dot"></div>
        </div>`,
        iconSize: [24, 24],
        iconAnchor: [12, 12],
      });

      const marker = L.marker([parseFloat(config.LAT), parseFloat(config.LON)], { icon }).addTo(map);
      marker._config = config;
      marker._sticky = false;
      // Hover previews the popup; click makes it stick until clicked again.
      marker.on("mouseover", function () {
        this.openPopup();
      });
      marker.on("mouseout", function () {
        if (!this._sticky) this.closePopup();
      });
      marker.on("click", function () {
        this._sticky = !this._sticky;
        this._sticky ? this.openPopup() : this.closePopup();
      });
      return marker;
    });

    return () => {
      map.remove();
      mapRef.current = null;
      markersRef.current = [];
      linesRef.current = [];
      fittedRef.current = false;
    };
  }, [configs]);

  // Redraw sun direction lines and popups for the selected date.
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    linesRef.current.forEach((line) => map.removeLayer(line));
    linesRef.current = [];

    const dateStr = date.toLocaleDateString(undefined, { weekday: "short", month: "short", day: "numeric" });

    for (const marker of markersRef.current) {
      const config = marker._config;
      const lat = parseFloat(config.LAT);
      const lon = parseFloat(config.LON);
      const mode = modeOf(config);

      const sunTimes = SunCalc.getTimes(date, lat, lon);
      const sunPos = SunCalc.getPosition(mode === "sunrise" ? sunTimes.sunrise : sunTimes.sunset, lat, lon);

      // SunCalc azimuth is from South, clockwise; convert to a compass bearing. The points use it
      // rounded the way the pipeline does, so they sit where the clouds were actually read.
      const exact = ((sunPos.azimuth * 180) / Math.PI + 180 + 360) % 360;
      const bearing = Math.round(exact / BEARING_STEP) * BEARING_STEP;
      const cls = `sun-ray ${mode}`;

      // The ray follows the exact sun direction, drawn as a great circle (a 2-point Leaflet line is
      // straight in Mercator and drifts off the reading points over long distances).
      const ray = Array.from({ length: RAY_KM / 5 + 1 }, (_, i) => destination(lat, lon, exact, i * 5));
      linesRef.current.push(L.polyline(ray, { className: cls, weight: 3, interactive: false }).addTo(map));
      for (const km of PATH_KM) {
        linesRef.current.push(
          L.circleMarker(destination(lat, lon, bearing, km), { className: `path-point ${mode}`, radius: 6, weight: 2 })
            .bindTooltip(`${config.CAMERA_TAG} · ${MILES[km]} mi toward the ${mode}`, { className: "path-tip", direction: "top", offset: [0, -6] })
            .addTo(map),
        );
      }

      const popupContent = `
        <div class="map-popup">
          <div class="popup-header">
            <span class="popup-name">${config.CAMERA_TAG}</span>
            <span class="popup-mode ${mode}">${mode}</span>
          </div>
          <div class="popup-date">${dateStr}</div>
          <div class="popup-details">
            <div class="popup-row">
              <span class="popup-label">Location</span>
              <span class="popup-value">${lat.toFixed(4)}, ${lon.toFixed(4)}</span>
            </div>
            <div class="popup-row">
              <span class="popup-label">Altitude</span>
              <span class="popup-value">${config.ALTITUDE || "N/A"}m</span>
            </div>
            <div class="popup-divider"></div>
            <div class="popup-row">
              <span class="popup-label">Sunrise</span>
              <span class="popup-value">${formatTime(sunTimes.sunrise)}</span>
            </div>
            <div class="popup-row">
              <span class="popup-label">Sunset</span>
              <span class="popup-value">${formatTime(sunTimes.sunset)}</span>
            </div>
          </div>
        </div>
      `;

      marker.setZIndexOffset(1000);
      if (marker.getPopup()) {
        marker.setPopupContent(popupContent);
      } else {
        marker.bindPopup(popupContent, {
          className: "dark-popup",
          maxWidth: 280,
          autoPan: false,
          closeOnClick: false,
          autoClose: false,
        });
      }
    }

    // First draw: frame the cameras and their reading points; later dates keep the user's view.
    if (!fittedRef.current && linesRef.current.length) {
      map.fitBounds(L.featureGroup([...markersRef.current, ...linesRef.current]).getBounds().pad(0.1));
      fittedRef.current = true;
    }
  }, [configs, date]);

  return (
    <div id="camera-map" ref={elRef}>
      {!configs.length && <div className="map-empty">No cameras with valid coordinates</div>}
    </div>
  );
}
