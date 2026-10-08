// Camera configuration (admin only): list/edit/delete config/*.env, add cameras, rebuild.

import { useEffect, useState } from "react";
import Dropdown from "../Dropdown.jsx";
import { Skeleton } from "../Skeleton.jsx";

const COMPOSE_CMD = "docker compose -f docker-compose.existing-infra.yml up -d --build";

async function sendJson(url, method, body) {
  const res = await fetch(url, {
    method,
    headers: { "Content-Type": "application/json" },
    body: body && JSON.stringify(body),
  });
  return { ok: res.ok, result: await res.json() };
}

const formToObject = (form) => Object.fromEntries(new FormData(form).entries());

export default function Config() {
  const [configs, setConfigs] = useState(null);
  const [loadError, setLoadError] = useState(null);
  const [editing, setEditing] = useState(null);

  function loadConfigs() {
    fetch("/api/admin/camera-configs")
      .then((res) => res.json())
      .then(setConfigs)
      .catch((err) => setLoadError(err.message));
  }
  useEffect(loadConfigs, []);

  async function deleteConfig(tag) {
    if (!confirm(`Delete camera "${tag}"? This cannot be undone.`)) return;
    try {
      const { ok, result } = await sendJson(`/api/admin/camera-configs/${tag}`, "DELETE");
      ok ? loadConfigs() : alert(result.error || "Failed to delete");
    } catch (err) {
      alert("Error: " + err.message);
    }
  }

  return (
    <>
      <h2>Camera Configuration</h2>
      <p>View and manage camera configurations.</p>
      <hr />

      <section>
        <h3>Current Cameras</h3>
        <div className="configs-grid">
          {loadError ? (
            <div className="empty">Failed to load configs: {loadError}</div>
          ) : !configs ? (
            [0, 1].map((i) => <Skeleton key={i} className="skeleton-card" />)
          ) : !configs.length ? (
            <div className="empty">No camera configurations found in config/ directory.</div>
          ) : (
            configs.map((config) => (
              <ConfigCard
                key={config._filename}
                config={config}
                onEdit={() => setEditing(config)}
                onDelete={() => deleteConfig(config.CAMERA_TAG)}
              />
            ))
          )}
        </div>
      </section>

      <AddCameraForm onAdded={loadConfigs} />
      <RebuildSection />

      {editing && (
        <EditModal
          config={editing}
          onClose={() => setEditing(null)}
          onSaved={() => {
            setEditing(null);
            loadConfigs();
          }}
        />
      )}
    </>
  );
}

function ConfigCard({ config, onEdit, onDelete }) {
  if (config._error) {
    return (
      <div className="config-card">
        <div className="config-header">
          <span className="config-name">{config._filename}</span>
          <span className="config-error">Error loading</span>
        </div>
        <div className="config-detail">{config._error}</div>
      </div>
    );
  }

  const mode = config.MODE || "sunset";
  const details = [
    ["Location", `${config.LAT || "N/A"}, ${config.LON || "N/A"}`],
    ["Altitude", `${config.ALTITUDE || "N/A"}m`],
    ["Timezone", config.TIMEZONE || "N/A"],
    ["Mode", mode.charAt(0).toUpperCase() + mode.slice(1)],
  ];

  return (
    <div className="config-card">
      <div className="config-header">
        <span className="config-name">{config.CAMERA_TAG || "Unknown"}</span>
        <span className="config-file">{config._filename}</span>
      </div>
      <div className="config-details">
        <div className="config-detail">
          <span className="config-label">Stream URL</span>
          <a href={config.YOUTUBE_URL || ""} target="_blank" rel="noreferrer" className="config-value config-url">
            {config.YOUTUBE_URL || "N/A"}
          </a>
        </div>
        {details.map(([label, value]) => (
          <div key={label} className="config-detail">
            <span className="config-label">{label}</span>
            <span className="config-value">{value}</span>
          </div>
        ))}
      </div>
      <div className="config-actions">
        <button className="btn btn-small btn-edit" onClick={onEdit}>
          Edit
        </button>
        <button className="btn btn-small btn-delete" onClick={onDelete}>
          Delete
        </button>
      </div>
    </div>
  );
}

/** Shared fields for the add and edit forms. `config` pre-fills them when editing. */
function CameraFields({ config = {}, includeTag = false }) {
  return (
    <>
      <div className="form-row">
        {includeTag && (
          <label>
            <span>Camera Tag</span>
            <input type="text" name="CAMERA_TAG" placeholder="my_new_cam" required pattern="^[a-zA-Z0-9_-]+$" />
          </label>
        )}
        <label>
          <span>Stream URL</span>
          <input
            type="url"
            name="YOUTUBE_URL"
            defaultValue={config.YOUTUBE_URL}
            placeholder="https://www.youtube.com/watch?v=... or direct stream URL"
            required
          />
        </label>
      </div>
      <div className="form-row">
        <label>
          <span>Latitude</span>
          <input type="number" name="LAT" step="any" defaultValue={config.LAT} placeholder="44.4766" required />
        </label>
        <label>
          <span>Longitude</span>
          <input type="number" name="LON" step="any" defaultValue={config.LON} placeholder="-73.2212" required />
        </label>
      </div>
      <div className="form-row">
        <label>
          <span>Altitude (meters)</span>
          <input type="number" name="ALTITUDE" defaultValue={config.ALTITUDE} placeholder="200" required />
        </label>
        <label>
          <span>Timezone</span>
          <input type="text" name="TIMEZONE" defaultValue={config.TIMEZONE || "America/New_York"} required />
        </label>
      </div>
      <div className="form-row">
        <label>
          <span>Mode</span>
          <ModeDropdown initial={config.MODE || "sunset"} />
        </label>
      </div>
    </>
  );
}

function AddCameraForm({ onAdded }) {
  const [status, setStatus] = useState(null);

  async function onSubmit(e) {
    e.preventDefault();
    const form = e.currentTarget;
    const data = formToObject(form);
    setStatus({ text: "Adding..." });

    try {
      const { ok, result } = await sendJson("/api/admin/camera-configs", "POST", data);
      if (!ok) {
        setStatus({ text: result.error || "Failed to add camera", className: "status-error" });
        return;
      }

      setStatus({ text: "Config created. Adding to docker-compose..." });
      const compose = await sendJson("/api/admin/add-compose-service", "POST", { camera_tag: data.CAMERA_TAG });
      setStatus(
        compose.ok
          ? { text: <>Camera added! Run: <code>{COMPOSE_CMD}</code></>, className: "status-success" }
          : { text: `Config saved but compose update failed: ${compose.result.error}`, className: "status-warning" },
      );
      form.reset();
      onAdded();
    } catch (err) {
      setStatus({ text: "Error: " + err.message, className: "status-error" });
    }
  }

  return (
    <section>
      <h3>Add New Camera</h3>
      <form className="add-camera-form" onSubmit={onSubmit}>
        <CameraFields includeTag />
        <div className="form-actions">
          <button type="submit" className="btn btn-primary">
            Add Camera
          </button>
          <span className={status?.className}>{status?.text}</span>
        </div>
      </form>
      <div className="add-camera-note">
        <strong>Note:</strong> Adding a camera will create the config file and automatically update docker-compose.yml.
        After adding, click Rebuild below or run: <code>{COMPOSE_CMD}</code>
      </div>
    </section>
  );
}

function RebuildSection() {
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState(null);

  async function rebuild() {
    if (!confirm("Rebuild all containers? This will briefly interrupt the dashboard.")) return;
    setBusy(true);
    setStatus({ text: "Starting rebuild..." });
    try {
      const { ok, result } = await sendJson("/api/admin/rebuild", "POST");
      setStatus(
        ok
          ? { text: "Rebuild started! Page may disconnect briefly.", className: "status-success" }
          : { text: result.error || "Rebuild failed", className: "status-error" },
      );
    } catch (err) {
      setStatus({ text: "Error: " + err.message, className: "status-error" });
    }
    setBusy(false);
  }

  return (
    <section>
      <h3>Rebuild Containers</h3>
      <p>Apply config changes by rebuilding the Docker containers.</p>
      <div className="rebuild-actions">
        <button className="btn btn-primary" disabled={busy} onClick={rebuild}>
          Rebuild All Containers
        </button>
        <span className={status?.className}>{status?.text}</span>
      </div>
    </section>
  );
}

function EditModal({ config, onClose, onSaved }) {
  const [status, setStatus] = useState(null);

  async function onSubmit(e) {
    e.preventDefault();
    setStatus({ text: "Saving..." });
    try {
      const { ok, result } = await sendJson(
        `/api/admin/camera-configs/${config.CAMERA_TAG}`,
        "PUT",
        formToObject(e.currentTarget),
      );
      ok ? onSaved() : setStatus({ text: result.error || "Failed to save", className: "status-error" });
    } catch (err) {
      setStatus({ text: "Error: " + err.message, className: "status-error" });
    }
  }

  return (
    <div className="edit-modal" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="edit-modal-content">
        <h3>Edit {config.CAMERA_TAG}</h3>
        <form className="add-camera-form" onSubmit={onSubmit}>
          <CameraFields config={config} />
          <div className="form-actions">
            <button type="submit" className="btn btn-primary">
              Save Changes
            </button>
            <button type="button" className="btn btn-cancel" onClick={onClose}>
              Cancel
            </button>
            <span className={status?.className}>{status?.text}</span>
          </div>
        </form>
      </div>
    </div>
  );
}

// Controlled so the form's hidden MODE input (from Base UI) always has a value.
function ModeDropdown({ initial }) {
  const [mode, setMode] = useState(initial);
  return (
    <Dropdown
      name="MODE"
      label="Mode"
      value={mode}
      onChange={setMode}
      options={[
        { value: "sunset", label: "Sunset" },
        { value: "sunrise", label: "Sunrise" },
      ]}
    />
  );
}
