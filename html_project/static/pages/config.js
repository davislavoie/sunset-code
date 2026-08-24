// Camera configuration page

export function renderConfig(container) {
  container.innerHTML = "";

  const title = document.createElement("h2");
  title.textContent = "Camera Configuration";
  container.appendChild(title);

  const intro = document.createElement("p");
  intro.textContent = "View and manage camera configurations.";
  container.appendChild(intro);

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
      After adding, run: <code>docker compose -f docker-compose.existing-infra.yml up -d --build</code>
    </div>
  `;
  container.appendChild(addSection);

  // Load configs
  loadConfigs(configsContainer);

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
      return;
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
  } catch (err) {
    container.innerHTML = `<div class="empty">Failed to load configs: ${err.message}</div>`;
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
