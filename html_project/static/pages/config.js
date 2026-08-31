// Camera configuration page

let mapInstance = null;
let mapMarkers = [];
let sunLines = [];

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
  const mapSection = document.createElement("section");
  mapSection.innerHTML = `
    <h3>Camera Locations</h3>
    <div class="map-container">
      <div id="camera-map"></div>
      <div class="map-legend">
        <div class="legend-item"><span class="legend-dot sunset"></span> Sunset cameras</div>
        <div class="legend-item"><span class="legend-dot sunrise"></span> Sunrise cameras</div>
        <div class="legend-item"><span class="legend-line"></span> Sun direction</div>
      </div>
    </div>
  `;
  container.appendChild(mapSection);

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
    initMap(configs);
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

function initMap(configs) {
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

  // Dark tile layer (CartoDB Dark Matter)
  L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> &copy; <a href="https://carto.com/">CARTO</a>',
    subdomains: 'abcd',
    maxZoom: 19,
  }).addTo(mapInstance);

  // Add markers and sun direction lines for each camera
  validConfigs.forEach(config => {
    const lat = parseFloat(config.LAT);
    const lon = parseFloat(config.LON);
    const mode = config.MODE || 'sunset';
    const isSunrise = mode === 'sunrise';

    // Calculate sun position for today
    const now = new Date();
    const sunTimes = SunCalc.getTimes(now, lat, lon);
    const targetTime = isSunrise ? sunTimes.sunrise : sunTimes.sunset;
    const sunPos = SunCalc.getPosition(targetTime, lat, lon);
    const azimuthDeg = (sunPos.azimuth * 180 / Math.PI) + 180; // Convert to degrees, adjust for north

    // Create custom marker icon
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

    // Calculate endpoint for sun direction line (extend ~50km in sun direction)
    const lineLength = 0.5; // degrees, roughly 50km
    const endLat = lat + lineLength * Math.cos(sunPos.azimuth);
    const endLon = lon + lineLength * Math.sin(sunPos.azimuth);

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

    // Create popup content
    const popupContent = `
      <div class="map-popup">
        <div class="popup-header">
          <span class="popup-name">${config.CAMERA_TAG}</span>
          <span class="popup-mode ${mode}">${mode}</span>
        </div>
        <div class="popup-details">
          <div class="popup-row">
            <span class="popup-label">Location</span>
            <span class="popup-value">${lat.toFixed(4)}, ${lon.toFixed(4)}</span>
          </div>
          <div class="popup-row">
            <span class="popup-label">Altitude</span>
            <span class="popup-value">${config.ALTITUDE || 'N/A'}m</span>
          </div>
          <div class="popup-row">
            <span class="popup-label">Timezone</span>
            <span class="popup-value">${config.TIMEZONE || 'N/A'}</span>
          </div>
          <div class="popup-divider"></div>
          <div class="popup-row">
            <span class="popup-label">Today's Sunrise</span>
            <span class="popup-value">${formatTime(sunTimes.sunrise)}</span>
          </div>
          <div class="popup-row">
            <span class="popup-label">Today's Sunset</span>
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

    marker.bindPopup(popupContent, {
      className: 'dark-popup',
      maxWidth: 280,
    });

    // Show popup on hover (desktop), keep click for mobile
    marker.on('mouseover', function() {
      this.openPopup();
    });

    mapMarkers.push(marker);
  });

  // Fit bounds to show all markers with padding
  if (mapMarkers.length > 1) {
    const group = L.featureGroup(mapMarkers);
    mapInstance.fitBounds(group.getBounds().pad(0.2));
  }
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
