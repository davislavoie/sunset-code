// Camera configuration page

let mapInstance = null;
let mapMarkers = [];
let sunLines = [];
let cachedConfigs = [];
let currentChartDate = new Date();

export function renderConfig(container) {
  container.innerHTML = "";

  const title = document.createElement("h2");
  title.textContent = "Camera Configuration";
  container.appendChild(title);

  const intro = document.createElement("p");
  intro.textContent = "View and manage camera configurations.";
  container.appendChild(intro);

  container.appendChild(document.createElement("hr"));

  // Map section
  const today = new Date();
  const dayOfYear = Math.floor((today - new Date(today.getFullYear(), 0, 0)) / (1000 * 60 * 60 * 24));
  const mapSection = document.createElement("section");
  mapSection.innerHTML = `
    <h3>Camera Locations</h3>
    <div class="map-container">
      <div class="map-controls">
        <div class="map-slider-control">
          <input type="range" id="map-date-slider" min="1" max="365" value="${dayOfYear}">
          <span id="map-date-display" class="date-display">${today.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}</span>
        </div>
        <div class="map-date-shortcuts">
          <button class="btn btn-small" data-offset="0">Today</button>
          <button class="btn btn-small" data-season="summer">Summer</button>
          <button class="btn btn-small" data-season="winter">Winter</button>
          <button class="btn btn-small" data-season="spring">Spring</button>
          <button class="btn btn-small" data-season="fall">Fall</button>
        </div>
      </div>
      <div id="camera-map"></div>
      <div class="map-legend">
        <div class="legend-item"><span class="legend-dot sunset"></span> Sunset</div>
        <div class="legend-item"><span class="legend-dot sunrise"></span> Sunrise</div>
        <div class="legend-item"><span class="legend-line"></span> Sun direction</div>
      </div>
    </div>
  `;
  container.appendChild(mapSection);

  container.appendChild(document.createElement("hr"));

  // Combined sun data section - map and chart together
  const sunDataSection = document.createElement("section");
  sunDataSection.innerHTML = `
    <h3>Sunrise & Sunset Analysis</h3>
    <div class="sun-data-layout">
      <div class="sun-chart-container">
        <div class="sun-chart-controls">
          <select id="sun-chart-camera">
            <option value="">Select a camera...</option>
          </select>
        </div>
        <div id="sun-times-chart"></div>
      </div>
    </div>
  `;
  container.appendChild(sunDataSection);

  container.appendChild(document.createElement("hr"));

  // Current configs section
  const configsSection = document.createElement("section");
  configsSection.innerHTML = "<h3>Current Cameras</h3>";
  const configsContainer = document.createElement("div");
  configsContainer.className = "configs-grid";
  configsContainer.innerHTML = '<div class="loading">Loading configurations...</div>';
  configsSection.appendChild(configsContainer);
  container.appendChild(configsSection);

  // Add new camera section
  const addSection = document.createElement("section");
  addSection.innerHTML = `
    <h3>Add New Camera</h3>
    <form id="add-camera-form" class="add-camera-form">
      <div class="form-row">
        <label>
          <span>Camera Tag</span>
          <input type="text" name="CAMERA_TAG" placeholder="my_new_cam" required pattern="^[a-zA-Z0-9_-]+$">
        </label>
        <label>
          <span>Stream URL</span>
          <input type="url" name="YOUTUBE_URL" placeholder="https://www.youtube.com/watch?v=... or direct stream URL" required>
        </label>
      </div>
      <div class="form-row">
        <label>
          <span>Latitude</span>
          <input type="number" name="LAT" step="any" placeholder="44.4766" required>
        </label>
        <label>
          <span>Longitude</span>
          <input type="number" name="LON" step="any" placeholder="-73.2212" required>
        </label>
      </div>
      <div class="form-row">
        <label>
          <span>Altitude (meters)</span>
          <input type="number" name="ALTITUDE" placeholder="200" required>
        </label>
        <label>
          <span>Timezone</span>
          <input type="text" name="TIMEZONE" value="America/New_York" required>
        </label>
      </div>
      <div class="form-row">
        <label>
          <span>Mode</span>
          <select name="MODE" required>
            <option value="sunset" selected>Sunset</option>
            <option value="sunrise">Sunrise</option>
          </select>
        </label>
      </div>
      <div class="form-actions">
        <button type="submit" class="btn btn-primary">Add Camera</button>
        <span id="form-status"></span>
      </div>
    </form>
    <div class="add-camera-note">
      <strong>Note:</strong> Adding a camera will create the config file and automatically update docker-compose.yml.
      After adding, click Rebuild below or run: <code>docker compose -f docker-compose.existing-infra.yml up -d --build</code>
    </div>
  `;
  container.appendChild(addSection);

  // Rebuild section
  const rebuildSection = document.createElement("section");
  rebuildSection.innerHTML = `
    <h3>Rebuild Containers</h3>
    <p>Apply config changes by rebuilding the Docker containers.</p>
    <div class="rebuild-actions">
      <button id="rebuild-btn" class="btn btn-primary">Rebuild All Containers</button>
      <span id="rebuild-status"></span>
    </div>
  `;
  container.appendChild(rebuildSection);

  // Load configs and initialize map
  loadConfigs(configsContainer).then(configs => {
    cachedConfigs = configs;
    initMap(configs, new Date());
    setupMapDateControls();
    initSunChart(configs);
  });

  // Handle rebuild button
  const rebuildBtn = document.getElementById("rebuild-btn");
  const rebuildStatus = document.getElementById("rebuild-status");
  rebuildBtn.addEventListener("click", async () => {
    if (!confirm("Rebuild all containers? This will briefly interrupt the dashboard.")) return;
    rebuildBtn.disabled = true;
    rebuildStatus.textContent = "Starting rebuild...";
    rebuildStatus.className = "";
    try {
      const res = await fetch("/api/rebuild", { method: "POST" });
      const result = await res.json();
      if (res.ok) {
        rebuildStatus.textContent = "Rebuild started! Page may disconnect briefly.";
        rebuildStatus.className = "status-success";
      } else {
        rebuildStatus.textContent = result.error || "Rebuild failed";
        rebuildStatus.className = "status-error";
      }
    } catch (err) {
      rebuildStatus.textContent = "Error: " + err.message;
      rebuildStatus.className = "status-error";
    }
    rebuildBtn.disabled = false;
  });

  // Handle form submission
  const form = document.getElementById("add-camera-form");
  const status = document.getElementById("form-status");
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    status.textContent = "Adding...";
    status.className = "";

    const formData = new FormData(form);
    const data = Object.fromEntries(formData.entries());

    try {
      const res = await fetch("/api/camera-configs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      });
      const result = await res.json();

      if (res.ok) {
        status.textContent = "Config created. Adding to docker-compose...";
        status.className = "";

        // Add service to docker-compose
        const composeRes = await fetch("/api/add-compose-service", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ camera_tag: data.CAMERA_TAG }),
        });
        const composeResult = await composeRes.json();

        if (composeRes.ok) {
          status.innerHTML = 'Camera added! Run: <code>docker compose -f docker-compose.existing-infra.yml up -d --build</code>';
          status.className = "status-success";
        } else {
          status.textContent = `Config saved but compose update failed: ${composeResult.error}`;
          status.className = "status-warning";
        }

        form.reset();
        form.querySelector('[name="TIMEZONE"]').value = "America/New_York";
        loadConfigs(configsContainer);
      } else {
        status.textContent = result.error || "Failed to add camera";
        status.className = "status-error";
      }
    } catch (err) {
      status.textContent = "Error: " + err.message;
      status.className = "status-error";
    }
  });
}

async function loadConfigs(container) {
  try {
    const res = await fetch("/api/camera-configs");
    const configs = await res.json();

    if (!configs.length) {
      container.innerHTML = '<div class="empty">No camera configurations found in config/ directory.</div>';
      return [];
    }

    container.innerHTML = "";
    for (const config of configs) {
      const card = document.createElement("div");
      card.className = "config-card";

      if (config._error) {
        card.innerHTML = `
          <div class="config-header">
            <span class="config-name">${config._filename}</span>
            <span class="config-error">Error loading</span>
          </div>
          <div class="config-detail">${config._error}</div>
        `;
      } else {
        const tag = config.CAMERA_TAG || "Unknown";
        card.innerHTML = `
          <div class="config-header">
            <span class="config-name">${tag}</span>
            <span class="config-file">${config._filename}</span>
          </div>
          <div class="config-details">
            <div class="config-detail">
              <span class="config-label">Stream URL</span>
              <a href="${config.YOUTUBE_URL || ''}" target="_blank" class="config-value config-url">${config.YOUTUBE_URL || 'N/A'}</a>
            </div>
            <div class="config-detail">
              <span class="config-label">Location</span>
              <span class="config-value">${config.LAT || 'N/A'}, ${config.LON || 'N/A'}</span>
            </div>
            <div class="config-detail">
              <span class="config-label">Altitude</span>
              <span class="config-value">${config.ALTITUDE || 'N/A'}m</span>
            </div>
            <div class="config-detail">
              <span class="config-label">Timezone</span>
              <span class="config-value">${config.TIMEZONE || 'N/A'}</span>
            </div>
            <div class="config-detail">
              <span class="config-label">Mode</span>
              <span class="config-value">${(config.MODE || 'sunset').charAt(0).toUpperCase() + (config.MODE || 'sunset').slice(1)}</span>
            </div>
          </div>
          <div class="config-actions">
            <button class="btn btn-small btn-edit" data-tag="${tag}">Edit</button>
            <button class="btn btn-small btn-delete" data-tag="${tag}">Delete</button>
          </div>
        `;

        // Edit button handler
        card.querySelector('.btn-edit').addEventListener('click', () => {
          showEditModal(config, container);
        });

        // Delete button handler
        card.querySelector('.btn-delete').addEventListener('click', async () => {
          if (!confirm(`Delete camera "${tag}"? This cannot be undone.`)) return;
          try {
            const res = await fetch(`/api/camera-configs/${tag}`, { method: 'DELETE' });
            const result = await res.json();
            if (res.ok) {
              loadConfigs(container);
            } else {
              alert(result.error || 'Failed to delete');
            }
          } catch (err) {
            alert('Error: ' + err.message);
          }
        });
      }

      container.appendChild(card);
    }
    return configs;
  } catch (err) {
    container.innerHTML = `<div class="empty">Failed to load configs: ${err.message}</div>`;
    return [];
  }
}

function initMap(configs, selectedDate) {
  const mapEl = document.getElementById('camera-map');
  if (!mapEl || !configs.length) return;

  // Clean up existing map
  if (mapInstance) {
    mapInstance.remove();
    mapInstance = null;
  }
  mapMarkers = [];
  sunLines = [];

  // Filter valid configs with coordinates
  const validConfigs = configs.filter(c => c.LAT && c.LON && !c._error);
  if (!validConfigs.length) {
    mapEl.innerHTML = '<div class="map-empty">No cameras with valid coordinates</div>';
    return;
  }

  // Calculate center from all cameras
  const avgLat = validConfigs.reduce((sum, c) => sum + parseFloat(c.LAT), 0) / validConfigs.length;
  const avgLon = validConfigs.reduce((sum, c) => sum + parseFloat(c.LON), 0) / validConfigs.length;

  // Initialize map with dark tiles
  mapInstance = L.map(mapEl, {
    center: [avgLat, avgLon],
    zoom: 4,
    zoomControl: true,
  });

  // OpenStreetMap tiles (free, no API key) - darkened via CSS
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    maxZoom: 19,
    className: 'dark-tiles',
  }).addTo(mapInstance);

  // Add markers for each camera (lines and popups added by updateSunData)
  validConfigs.forEach(config => {
    const lat = parseFloat(config.LAT);
    const lon = parseFloat(config.LON);
    const mode = config.MODE || 'sunset';
    const isSunrise = mode === 'sunrise';
    const markerColor = isSunrise ? '#ff9500' : '#f39c12';

    const markerIcon = L.divIcon({
      className: 'camera-marker',
      html: `<div class="marker-pin" style="--marker-color: ${markerColor}">
        <div class="marker-pulse"></div>
        <div class="marker-dot"></div>
      </div>`,
      iconSize: [24, 24],
      iconAnchor: [12, 12],
    });

    const marker = L.marker([lat, lon], { icon: markerIcon }).addTo(mapInstance);
    marker._config = config; // Store config reference
    marker.on('mouseover', function() { this.openPopup(); });
    marker.on('mouseout', function() { this.closePopup(); });
    mapMarkers.push(marker);
  });

  // Fit bounds to show all markers with padding
  if (mapMarkers.length > 1) {
    const group = L.featureGroup(mapMarkers);
    mapInstance.fitBounds(group.getBounds().pad(0.2));
  }

  // Initial sun data update
  updateSunData(selectedDate);
}

function updateSunData(selectedDate) {
  if (!mapInstance || !mapMarkers.length) return;

  // Remove existing sun lines
  sunLines.forEach(line => mapInstance.removeLayer(line));
  sunLines = [];

  const dateStr = selectedDate.toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' });

  mapMarkers.forEach(marker => {
    const config = marker._config;
    const lat = parseFloat(config.LAT);
    const lon = parseFloat(config.LON);
    const mode = config.MODE || 'sunset';
    const isSunrise = mode === 'sunrise';
    const markerColor = isSunrise ? '#ff9500' : '#f39c12';

    // Calculate sun position for selected date
    const sunTimes = SunCalc.getTimes(selectedDate, lat, lon);
    const targetTime = isSunrise ? sunTimes.sunrise : sunTimes.sunset;
    const sunPos = SunCalc.getPosition(targetTime, lat, lon);

    // SunCalc azimuth is from South, clockwise. Convert to bearing from North.
    // azimuth 0 = South, π/2 = West, -π/2 = East
    const bearingFromNorth = sunPos.azimuth + Math.PI;
    const azimuthDeg = (bearingFromNorth * 180 / Math.PI) % 360;

    // Calculate endpoint for sun direction line (pointing toward the sun)
    const lineLength = 2.5; // degrees (~250km)
    const latRad = lat * Math.PI / 180;
    const endLat = lat + lineLength * Math.cos(bearingFromNorth);
    const endLon = lon + lineLength * Math.sin(bearingFromNorth) / Math.cos(latRad);

    // Draw sun direction line
    const sunLine = L.polyline([[lat, lon], [endLat, endLon]], {
      color: markerColor,
      weight: 2,
      opacity: 0.7,
      dashArray: '8, 8',
    }).addTo(mapInstance);
    sunLines.push(sunLine);

    // Format times for popup
    const formatTime = (date) => date ? date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : 'N/A';

    // Update popup content
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
            <span class="popup-value">${config.ALTITUDE || 'N/A'}m</span>
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
          <div class="popup-row">
            <span class="popup-label">Sun Azimuth</span>
            <span class="popup-value">${azimuthDeg.toFixed(1)}°</span>
          </div>
          <div class="popup-row">
            <span class="popup-label">Golden Hour</span>
            <span class="popup-value">${formatTime(sunTimes.goldenHour)}</span>
          </div>
        </div>
      </div>
    `;

    // Bind or update popup
    if (marker.getPopup()) {
      marker.setPopupContent(popupContent);
    } else {
      marker.bindPopup(popupContent, {
        className: 'dark-popup',
        maxWidth: 280,
        autoPan: false,
      });
    }
  });
}

function setupMapDateControls() {
  const slider = document.getElementById('map-date-slider');
  const display = document.getElementById('map-date-display');
  if (!slider) return;

  function dayOfYearToDate(dayOfYear) {
    const year = new Date().getFullYear();
    const date = new Date(year, 0, 1);
    date.setDate(dayOfYear);
    return date;
  }

  function dateToDayOfYear(date) {
    const start = new Date(date.getFullYear(), 0, 0);
    const diff = date - start;
    return Math.floor(diff / (1000 * 60 * 60 * 24));
  }

  function updateFromSlider() {
    const date = dayOfYearToDate(parseInt(slider.value));
    display.textContent = date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
    currentChartDate = date;
    updateSunData(date);
    updateChartDateMarker(date);
  }

  // Slider change
  slider.addEventListener('input', updateFromSlider);

  // Shortcut buttons
  document.querySelectorAll('.map-date-shortcuts button').forEach(btn => {
    btn.addEventListener('click', () => {
      const year = new Date().getFullYear();
      let date;

      if (btn.dataset.offset !== undefined) {
        date = new Date();
        date.setDate(date.getDate() + parseInt(btn.dataset.offset));
      } else if (btn.dataset.season) {
        switch (btn.dataset.season) {
          case 'summer':
            date = new Date(year, 5, 21); // June 21
            break;
          case 'winter':
            date = new Date(year, 11, 21); // Dec 21
            break;
          case 'spring':
            date = new Date(year, 2, 20); // Mar 20
            break;
          case 'fall':
            date = new Date(year, 8, 22); // Sep 22
            break;
          default:
            date = new Date();
        }
      }

      slider.value = dateToDayOfYear(date);
      display.textContent = date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
      currentChartDate = date;
      updateSunData(date);
      updateChartDateMarker(date);
    });
  });
}

function updateChartDateMarker(date) {
  const chartEl = document.getElementById('sun-times-chart');
  if (!chartEl || !chartEl.data) return;

  // Update the vertical line and annotation for selected date
  Plotly.relayout(chartEl, {
    'shapes[0].x0': date,
    'shapes[0].x1': date,
    'annotations[0].x': date,
    'annotations[0].text': date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' }),
  });
}

function initSunChart(configs) {
  const chartEl = document.getElementById('sun-times-chart');
  const select = document.getElementById('sun-chart-camera');
  if (!chartEl || !select) return;

  // Filter valid configs
  const validConfigs = configs.filter(c => c.LAT && c.LON && !c._error);
  if (!validConfigs.length) {
    chartEl.innerHTML = '<div class="chart-empty">No cameras with valid coordinates</div>';
    return;
  }

  // Populate camera selector
  validConfigs.forEach(config => {
    const opt = document.createElement('option');
    opt.value = config.CAMERA_TAG;
    opt.textContent = `${config.CAMERA_TAG} (${config.MODE || 'sunset'})`;
    select.appendChild(opt);
  });

  // Draw chart when camera selected
  select.addEventListener('change', () => {
    const config = validConfigs.find(c => c.CAMERA_TAG === select.value);
    if (config) {
      drawSunChart(config, chartEl);
    } else {
      chartEl.innerHTML = '';
    }
  });

  // Auto-select first camera
  if (validConfigs.length) {
    select.value = validConfigs[0].CAMERA_TAG;
    drawSunChart(validConfigs[0], chartEl);
  }
}

function drawSunChart(config, chartEl) {
  const lat = parseFloat(config.LAT);
  const lon = parseFloat(config.LON);
  const year = new Date().getFullYear();

  // Calculate sun times for every day of the year
  const dates = [];
  const sunriseHours = [];
  const sunsetHours = [];
  const goldenHours = [];
  const dayLengths = [];

  for (let d = 1; d <= 365; d++) {
    const date = new Date(year, 0, d);
    const sunTimes = SunCalc.getTimes(date, lat, lon);

    dates.push(date);

    // Convert times to decimal hours for smooth chart
    const toDecimalHour = (dt) => dt ? dt.getHours() + dt.getMinutes() / 60 : null;

    sunriseHours.push(toDecimalHour(sunTimes.sunrise));
    sunsetHours.push(toDecimalHour(sunTimes.sunset));
    goldenHours.push(toDecimalHour(sunTimes.goldenHour));

    // Day length in hours
    if (sunTimes.sunrise && sunTimes.sunset) {
      dayLengths.push((sunTimes.sunset - sunTimes.sunrise) / (1000 * 60 * 60));
    } else {
      dayLengths.push(null);
    }
  }

  // Format date labels
  const dateLabels = dates.map(d => d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' }));

  // bklit-ui style colors
  const sunriseColor = '#ff9500';
  const sunsetColor = '#f39c12';
  const goldenColor = '#ffd700';

  const traces = [
    {
      x: dates,
      y: sunriseHours,
      name: 'Sunrise',
      type: 'scatter',
      mode: 'lines',
      line: { color: sunriseColor, width: 2.5 },
      fill: 'tozeroy',
      fillcolor: 'rgba(255, 149, 0, 0.1)',
      hovertemplate: '%{x|%b %d}<br>Sunrise: %{y:.2f}h<extra></extra>',
    },
    {
      x: dates,
      y: sunsetHours,
      name: 'Sunset',
      type: 'scatter',
      mode: 'lines',
      line: { color: sunsetColor, width: 2.5 },
      fill: 'tonexty',
      fillcolor: 'rgba(243, 156, 18, 0.15)',
      hovertemplate: '%{x|%b %d}<br>Sunset: %{y:.2f}h<extra></extra>',
    },
    {
      x: dates,
      y: goldenHours,
      name: 'Golden Hour',
      type: 'scatter',
      mode: 'lines',
      line: { color: goldenColor, width: 1.5, dash: 'dot' },
      hovertemplate: '%{x|%b %d}<br>Golden Hour: %{y:.2f}h<extra></extra>',
    },
  ];

  const layout = {
    paper_bgcolor: 'rgba(0,0,0,0)',
    plot_bgcolor: 'rgba(23, 27, 35, 0.5)',
    font: { color: '#f0f2f6', family: 'Source Sans Pro, sans-serif' },
    margin: { t: 40, r: 20, b: 50, l: 50 },
    showlegend: true,
    legend: {
      orientation: 'h',
      y: 1.1,
      x: 0.5,
      xanchor: 'center',
      bgcolor: 'rgba(0,0,0,0)',
    },
    xaxis: {
      gridcolor: 'rgba(255,255,255,0.08)',
      tickformat: '%b',
      dtick: 'M1',
      tickangle: 0,
    },
    yaxis: {
      title: 'Time (24h)',
      gridcolor: 'rgba(255,255,255,0.08)',
      range: [0, 24],
      dtick: 4,
      tickvals: [0, 4, 8, 12, 16, 20, 24],
      ticktext: ['12am', '4am', '8am', '12pm', '4pm', '8pm', '12am'],
    },
    hovermode: 'x unified',
    hoverlabel: {
      bgcolor: 'rgba(23, 27, 35, 0.95)',
      bordercolor: 'rgba(255,255,255,0.1)',
      font: { color: '#f0f2f6' },
    },
    // Add vertical line for today
    shapes: [{
      type: 'line',
      x0: currentChartDate,
      x1: currentChartDate,
      y0: 0,
      y1: 24,
      line: { color: 'rgba(243, 156, 18, 0.8)', width: 2 },
    }],
    annotations: [{
      x: currentChartDate,
      y: 23,
      text: currentChartDate.toLocaleDateString(undefined, { month: 'short', day: 'numeric' }),
      showarrow: false,
      font: { color: 'var(--accent)', size: 11 },
      bgcolor: 'rgba(0,0,0,0.5)',
      borderpad: 3,
    }],
  };

  const plotlyConfig = {
    displayModeBar: false,
    responsive: true,
  };

  Plotly.newPlot(chartEl, traces, layout, plotlyConfig);
}

function showEditModal(config, configsContainer) {
  // Remove existing modal if any
  const existing = document.querySelector('.edit-modal');
  if (existing) existing.remove();

  const modal = document.createElement('div');
  modal.className = 'edit-modal';
  modal.innerHTML = `
    <div class="edit-modal-content">
      <h3>Edit ${config.CAMERA_TAG}</h3>
      <form id="edit-camera-form" class="add-camera-form">
        <div class="form-row">
          <label>
            <span>Stream URL</span>
            <input type="url" name="YOUTUBE_URL" value="${config.YOUTUBE_URL || ''}" required>
          </label>
        </div>
        <div class="form-row">
          <label>
            <span>Latitude</span>
            <input type="number" name="LAT" step="any" value="${config.LAT || ''}" required>
          </label>
          <label>
            <span>Longitude</span>
            <input type="number" name="LON" step="any" value="${config.LON || ''}" required>
          </label>
        </div>
        <div class="form-row">
          <label>
            <span>Altitude (meters)</span>
            <input type="number" name="ALTITUDE" value="${config.ALTITUDE || ''}" required>
          </label>
          <label>
            <span>Timezone</span>
            <input type="text" name="TIMEZONE" value="${config.TIMEZONE || 'America/New_York'}" required>
          </label>
        </div>
        <div class="form-row">
          <label>
            <span>Mode</span>
            <select name="MODE" required>
              <option value="sunset" ${(config.MODE || 'sunset') === 'sunset' ? 'selected' : ''}>Sunset</option>
              <option value="sunrise" ${config.MODE === 'sunrise' ? 'selected' : ''}>Sunrise</option>
            </select>
          </label>
        </div>
        <div class="form-actions">
          <button type="submit" class="btn btn-primary">Save Changes</button>
          <button type="button" class="btn btn-cancel">Cancel</button>
          <span id="edit-status"></span>
        </div>
      </form>
    </div>
  `;

  document.body.appendChild(modal);

  // Close on cancel or backdrop click
  modal.querySelector('.btn-cancel').addEventListener('click', () => modal.remove());
  modal.addEventListener('click', (e) => {
    if (e.target === modal) modal.remove();
  });

  // Handle form submit
  const form = modal.querySelector('#edit-camera-form');
  const status = modal.querySelector('#edit-status');

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    status.textContent = 'Saving...';

    const formData = new FormData(form);
    const data = Object.fromEntries(formData.entries());

    try {
      const res = await fetch(`/api/camera-configs/${config.CAMERA_TAG}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
      const result = await res.json();

      if (res.ok) {
        modal.remove();
        loadConfigs(configsContainer);
      } else {
        status.textContent = result.error || 'Failed to save';
        status.className = 'status-error';
      }
    } catch (err) {
      status.textContent = 'Error: ' + err.message;
      status.className = 'status-error';
    }
  });
}
