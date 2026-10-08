// Camera map with sun direction lines + yearly sunrise/sunset chart. Public:
// reads /api/camera-locations, which never includes stream URLs.

import { useEffect, useRef, useState } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import SunCalc from "suncalc";
import Dropdown from "../Dropdown.jsx";
import { Skeleton } from "../Skeleton.jsx";
import SunTimesChart from "../SunTimesChart.jsx";

const SUNRISE_COLOR = "#ff9500";
const SUNSET_COLOR = "#f39c12";

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
const colorOf = (config) => (modeOf(config) === "sunrise" ? SUNRISE_COLOR : SUNSET_COLOR);

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
      <h2>Camera Map</h2>

      <section>
        <h3>Camera Locations</h3>
        <div className="map-container">
          <div className="map-controls">
            <div className="map-slider-control">
              <input
                type="range"
                min={1}
                max={365}
                value={dateToDayOfYear(date)}
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
          </div>
        </div>
      </section>

      <hr />

      <section>
        <h3>Sunrise &amp; Sunset Analysis</h3>
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

function LeafletMap({ configs, date }) {
  const elRef = useRef(null);
  const mapRef = useRef(null);
  const markersRef = useRef([]);
  const linesRef = useRef([]);

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

    if (markersRef.current.length > 1) {
      map.fitBounds(L.featureGroup(markersRef.current).getBounds().pad(0.2));
    }

    return () => {
      map.remove();
      mapRef.current = null;
      markersRef.current = [];
      linesRef.current = [];
    };
  }, [configs]);

  // Redraw sun direction lines and popups for the selected date.
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    linesRef.current.forEach((line) => map.removeLayer(line));
    linesRef.current = [];

    const dateStr = date.toLocaleDateString(undefined, { weekday: "short", month: "short", day: "numeric" });
    const formatTime = (d) => (d ? d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : "N/A");

    for (const marker of markersRef.current) {
      const config = marker._config;
      const lat = parseFloat(config.LAT);
      const lon = parseFloat(config.LON);
      const mode = modeOf(config);

      const sunTimes = SunCalc.getTimes(date, lat, lon);
      const sunPos = SunCalc.getPosition(mode === "sunrise" ? sunTimes.sunrise : sunTimes.sunset, lat, lon);

      // SunCalc azimuth is from South, clockwise. Convert to bearing from North.
      const bearing = sunPos.azimuth + Math.PI;
      const lineLength = 2.5; // degrees (~250km)
      const endLat = lat + lineLength * Math.cos(bearing);
      const endLon = lon + (lineLength * Math.sin(bearing)) / Math.cos((lat * Math.PI) / 180);

      linesRef.current.push(
        L.polyline(
          [
            [lat, lon],
            [endLat, endLon],
          ],
          { color: colorOf(config), weight: 2, opacity: 0.7, dashArray: "8, 8" },
        ).addTo(map),
      );

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
  }, [configs, date]);

  return (
    <div id="camera-map" ref={elRef}>
      {!configs.length && <div className="map-empty">No cameras with valid coordinates</div>}
    </div>
  );
}
