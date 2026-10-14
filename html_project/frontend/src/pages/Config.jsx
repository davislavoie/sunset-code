// Cameras page. Public (/cameras): the cameras we watch, a form to request a new one, and the map.
// Admin (/admin/config, the same page): edit/delete the config/*.env files, add a camera (or turn a
// request into one), rebuild. Requests are stored by the backend (camera_requests in InfluxDB).

import { Suspense, lazy, useEffect, useState } from "react";
import Dropdown from "../Dropdown.jsx";
import { Skeleton } from "../Skeleton.jsx";

const CameraMap = lazy(() => import("./CameraMap.jsx")); // Leaflet: only loaded with this page
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

export default function Config({ admin = false }) {
  const [configs, setConfigs] = useState(null);
  const [loadError, setLoadError] = useState(null);
  const [editing, setEditing] = useState(null);
  const [prefill, setPrefill] = useState(null); // a request being turned into a camera

  function loadConfigs() {
    // The public list never includes stream URLs.
    fetch(admin ? "/api/admin/camera-configs" : "/api/camera-locations")
      .then((res) => res.json())
      .then(setConfigs)
      .catch((err) => setLoadError(err.message));
  }
  useEffect(loadConfigs, [admin]);

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
      <h1>{admin ? "Camera configuration" : "Cameras"}</h1>
      <p>{admin ? "Manage the cameras, review requests, and rebuild." : "The webcams we watch every day, and where they point."}</p>
      <hr />

      <section>
        <h3>Current cameras</h3>
        <div className="configs-grid">
          {loadError ? (
            <div className="empty">Failed to load cameras: {loadError}</div>
          ) : !configs ? (
            [0, 1].map((i) => <Skeleton key={i} className="skeleton-card" />)
          ) : !configs.length ? (
            <div className="empty">No cameras yet.</div>
          ) : (
            configs.map((config) => (
              <ConfigCard
                key={config._filename || config.CAMERA_TAG}
                config={config}
                onEdit={admin ? () => setEditing(config) : null}
                onDelete={admin ? () => deleteConfig(config.CAMERA_TAG) : null}
              />
            ))
          )}
        </div>
      </section>

      {admin ? (
        <>
          <CameraRequests onUse={setPrefill} />
          <AddCameraForm
            key={prefill?.id || "blank"}
            prefill={prefill}
            onAdded={() => {
              setPrefill(null);
              loadConfigs();
            }}
          />
          <RebuildSection />
        </>
      ) : (
        <RequestCameraForm />
      )}

      <hr />
      <Suspense fallback={<Skeleton style={{ height: 400 }} />}>
        <CameraMap />
      </Suspense>

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
    ["Location", config.LAT && config.LON ? `${(+config.LAT).toFixed(4)}, ${(+config.LON).toFixed(4)}` : "N/A"],
    ["Altitude", `${config.ALTITUDE || "N/A"}m`],
    ["Timezone", config.TIMEZONE || "N/A"],
    ["Mode", mode.charAt(0).toUpperCase() + mode.slice(1)],
  ];

  return (
    <div className="config-card">
      <div className="config-header">
        <span className="config-name">{config.CAMERA_TAG || "Unknown"}</span>
        {config._filename && <span className="config-file">{config._filename}</span>}
      </div>
      <div className="config-details">
        {config.YOUTUBE_URL && (
          <div className="config-detail">
            <span className="config-label">Stream URL</span>
            <a href={config.YOUTUBE_URL} target="_blank" rel="noreferrer" className="config-value config-url">
              {config.YOUTUBE_URL}
            </a>
          </div>
        )}
        {details.map(([label, value]) => (
          <div key={label} className="config-detail">
            <span className="config-label">{label}</span>
            <span className="config-value">{value}</span>
          </div>
        ))}
      </div>
      {onEdit && (
        <div className="config-actions">
          <button className="btn btn-small btn-edit" onClick={onEdit}>
            Edit
          </button>
          <button className="btn btn-small btn-delete" onClick={onDelete}>
            Delete
          </button>
        </div>
      )}
    </div>
  );
}

/** Public: ask for a camera to be added. Nothing changes until an admin adds it. */
function RequestCameraForm() {
  const [status, setStatus] = useState(null);

  async function onSubmit(e) {
    e.preventDefault();
    const form = e.currentTarget;
    setStatus({ text: "Sending..." });
    try {
      const { ok, result } = await sendJson("/api/camera-requests", "POST", formToObject(form));
      if (!ok) return setStatus({ text: result.error || "Couldn't send the request", className: "status-error" });
      setStatus({ text: "Thanks! We'll take a look.", className: "status-success" });
      form.reset();
    } catch (err) {
      setStatus({ text: "Error: " + err.message, className: "status-error" });
    }
  }

  return (
    <section>
      <h3>Request a new camera</h3>
      <form className="add-camera-form" onSubmit={onSubmit}>
        <div className="form-row">
          <label>
            <span>Camera name</span>
            <input type="text" name="name" maxLength={80} placeholder="Burlington waterfront" />
          </label>
          <label>
            <span>Stream or webcam link</span>
            <input type="url" name="stream_url" maxLength={500} placeholder="https://www.youtube.com/watch?v=..." required />
          </label>
        </div>
        <div className="form-row">
          <label>
            <span>Latitude (if you know it)</span>
            <input type="number" name="lat" step="any" placeholder="44.4766" />
          </label>
          <label>
            <span>Longitude (if you know it)</span>
            <input type="number" name="lon" step="any" placeholder="-73.2212" />
          </label>
        </div>
        <div className="form-row">
          <label>
            <span>Points at the</span>
            <ModeDropdown name="mode" initial="sunset" />
          </label>
          <label>
            <span>Your email (optional)</span>
            <input type="email" name="contact" maxLength={200} />
          </label>
        </div>
        <div className="form-row">
          <label>
            <span>Anything else</span>
            <textarea name="notes" rows={3} maxLength={1000} />
          </label>
        </div>
        <div className="form-actions">
          <button type="submit" className="btn btn-primary">
            Send request
          </button>
          <span className={status?.className}>{status?.text}</span>
        </div>
      </form>
    </section>
  );
}

/** Admin: requests waiting for review. Use fills in the Add form below; Dismiss hides the request. */
function CameraRequests({ onUse }) {
  const [requests, setRequests] = useState(null);
  const load = () =>
    fetch("/api/admin/camera-requests")
      .then((r) => r.json())
      .then(setRequests)
      .catch(() => setRequests([]));
  useEffect(() => {
    load();
  }, []);

  async function dismiss(id) {
    const { ok, result } = await sendJson("/api/admin/camera-requests/dismiss", "POST", { id });
    ok ? load() : alert(result.error || "Couldn't dismiss");
  }

  if (!requests?.length) return null;
  return (
    <section>
      <h3>Camera requests ({requests.length})</h3>
      <div className="configs-grid">
        {requests.map((r) => (
          <div key={r.id} className="config-card">
            <div className="config-header">
              <span className="config-name">{r.name || "Unnamed"}</span>
              <span className="config-file">{new Date(r.id).toLocaleDateString()}</span>
            </div>
            <div className="config-details">
              <div className="config-detail">
                <span className="config-label">Link</span>
                <a href={r.stream_url} target="_blank" rel="noreferrer noopener" className="config-value config-url">
                  {r.stream_url}
                </a>
              </div>
              {[
                ["Location", r.lat && r.lon ? `${r.lat}, ${r.lon}` : "—"],
                ["Mode", r.mode],
                ["From", r.contact || "—"],
                ["Notes", r.notes || "—"],
              ].map(([label, value]) => (
                <div key={label} className="config-detail">
                  <span className="config-label">{label}</span>
                  <span className="config-value">{value}</span>
                </div>
              ))}
            </div>
            <div className="config-actions">
              <button className="btn btn-small btn-edit" onClick={() => onUse(r)}>
                Use
              </button>
              <button className="btn btn-small btn-delete" onClick={() => dismiss(r.id)}>
                Dismiss
              </button>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

/** Shared fields for the add and edit forms. `config` pre-fills them when editing (or from a request). */
function CameraFields({ config = {}, includeTag = false }) {
  return (
    <>
      <div className="form-row">
        {includeTag && (
          <label>
            <span>Camera Tag</span>
            <input
              type="text"
              name="CAMERA_TAG"
              defaultValue={config.CAMERA_TAG}
              placeholder="my_new_cam"
              required
              pattern="^[a-zA-Z0-9_-]+$"
            />
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

/** A request's answers as Add form defaults (the camera tag made from its name). */
const fromRequest = (r) =>
  r && {
    CAMERA_TAG: (r.name || "").toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_|_$/g, ""),
    YOUTUBE_URL: r.stream_url,
    LAT: r.lat,
    LON: r.lon,
    MODE: r.mode,
  };

function AddCameraForm({ onAdded, prefill }) {
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
      <h3>Add a camera{prefill ? ` (from ${prefill.name || "a request"})` : ""}</h3>
      <form className="add-camera-form" onSubmit={onSubmit}>
        <CameraFields includeTag config={fromRequest(prefill) || undefined} />
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
      <h3>Rebuild containers</h3>
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

// Controlled so the form's hidden input (from Base UI) always has a value.
function ModeDropdown({ initial, name = "MODE" }) {
  const [mode, setMode] = useState(initial);
  return (
    <Dropdown
      name={name}
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
