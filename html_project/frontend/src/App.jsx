import { lazy, Suspense, useEffect, useState } from "react";
import { NavLink, Navigate, Route, Routes, useLocation, useNavigate, useParams, useSearchParams } from "react-router";
import { Moon, PanelLeftClose, PanelLeftOpen, Sun, Sunset } from "lucide-react";
import Tip from "./Tip.jsx";
import { fetchCameraData, getJson } from "./api.js";
import Dropdown from "./Dropdown.jsx";
import Calendar from "./pages/Calendar.jsx";
import Archive from "./pages/Archive.jsx";
import Config from "./pages/Config.jsx";
import HsvTuner, { INITIAL_TUNER, loadGalleryCanvas } from "./pages/HsvTuner.jsx";
import MyRanking from "./pages/MyRanking.jsx";
import Ranking from "./pages/Ranking.jsx";
import RankingExplained from "./pages/RankingExplained.jsx";
import { PageSkeleton } from "./Skeleton.jsx";

// Chart pages (bklit/visx, Leaflet) only download when opened.
const ScoreTracker = lazy(() => import("./pages/ScoreTracker.jsx"));

const DEFAULT_CAMERA = "btv_echo_cam";
const MOBILE_BREAKPOINT = 768;
const isMobile = () => window.innerWidth <= MOBILE_BREAKPOINT;

const PUBLIC_PAGES = [
  ["/calendar", "Sunset calendar"],
  ["/ranking", "Ranked images"],
  ["/score-tracker", "Score tracker"],
  ["/ranking-explained", "Ranking explained"],
  ["/cameras", "Cameras"],
];
// Everything that writes lives under /admin so a reverse proxy can gate it.
const ADMIN_PAGES = [
  ["/admin/my-ranking", "My ranking"],
  ["/admin/hsv-tuner", "HSV tuner"],
  ["/admin/config", "Config"],
  ["/admin/archive", "Archive"],
];

export default function App() {
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const section = pathname.split("/")[1];
  const [searchParams, setSearchParams] = useSearchParams();
  const [cameras, setCameras] = useState([]);
  const [camera, setCamera] = useState(null);
  const [data, setData] = useState(null);
  const [dataCamera, setDataCamera] = useState(null);
  const [error, setError] = useState(null);
  const [tuner, setTuner] = useState(INITIAL_TUNER);
  // Logged in as admin (the browser has the admin password): shows admin-only buttons like Load to HSV Tuner.
  const [isAdmin, setIsAdmin] = useState(false);
  useEffect(() => {
    getJson("/api/admin/status").then((s) => setIsAdmin(!!s.admin)).catch(() => {});
  }, []);
  // Only the explicit buttons collapse it; starts collapsed on mobile.
  const [collapsed, setCollapsed] = useState(isMobile);
  const collapseOnMobile = () => isMobile() && setCollapsed(true);

  useEffect(() => {
    getJson("/api/cameras")
      .then((list) => {
        setCameras(list);
        setCamera(list.includes(DEFAULT_CAMERA) ? DEFAULT_CAMERA : list[0] || DEFAULT_CAMERA);
      })
      .catch((e) => setError(e.message));
  }, []);

  // Keep showing the previous camera's page (dimmed) until the new data arrives.
  useEffect(() => {
    if (!camera) return;
    let live = true;
    setError(null);
    fetchCameraData(camera)
      .then((d) => {
        if (!live) return;
        setData(d);
        setDataCamera(camera);
      })
      .catch((e) => live && setError(e.message));
    return () => {
      live = false;
    };
  }, [camera]);
  const switching = data && camera !== dataCamera && !error;

  // A shared link can name its camera (?camera=..., from /sunset/<camera>/<date>);
  // select it in the sidebar once the camera list has loaded.
  const urlCamera = searchParams.get("camera");
  useEffect(() => {
    if (urlCamera && cameras.includes(urlCamera)) setCamera(urlCamera);
  }, [urlCamera, cameras]);

  function changeCamera(cam) {
    setCamera(cam);
    if (urlCamera || section === "calendar") {
      // Drop the linked camera (it would switch straight back) and, on the calendar, the
      // date, so the new camera opens on its own latest sunset.
      setSearchParams((p) => {
        p.delete("camera");
        if (section === "calendar") {
          p.delete("date");
          p.delete("open");
        }
        return p;
      });
    }
  }

  /** Adds a gallery image to the HSV tuner, then (by default) opens the tuner. */
  async function loadToHsv(url, { navigate: go = true } = {}) {
    const canvas = await loadGalleryCanvas(url);
    // Not crypto.randomUUID(): browsers only have it on https or localhost, and the dashboard is opened over
    // plain http (Tailscale IP), where it threw inside the state update and blanked the whole app.
    const id = `${Date.now()}-${Math.random()}`;
    setTuner((t) => ({ ...t, loaded: [...t.loaded, { id, url, canvas }] }));
    if (go) navigate("/admin/hsv-tuner");
  }

  // Pages that need the selected camera's data show a page-shaped skeleton until it arrives.
  const withData = (render, kind) => (data ? render(data) : !error && <PageSkeleton kind={kind} />);

  const navLink = ([to, label]) => (
    <NavLink key={to} className="nav-btn" to={to} onClick={collapseOnMobile}>
      {label}
    </NavLink>
  );

  return (
    <div className={`layout${collapsed ? " sidebar-collapsed" : ""}`}>
      <aside className="sidebar">
        <div className="sidebar-inner">
          <Tip label="Collapse sidebar">
            <button className="icon-btn collapse-btn" aria-label="Collapse sidebar" onClick={() => setCollapsed(true)}>
              <PanelLeftClose size={18} />
            </button>
          </Tip>

          <div className="sidebar-header">
            <span className="brand-tile">
              <Sunset size={18} />
            </span>
            <h2>Sunsets</h2>
          </div>

          <h3>Camera</h3>
          <Dropdown
            className="dd-block"
            label="Camera"
            placeholder="Loading cameras…"
            options={cameras}
            value={camera}
            onChange={(cam) => {
              changeCamera(cam);
              collapseOnMobile();
            }}
          />

          <hr />
          {PUBLIC_PAGES.map(navLink)}

          <h3>Admin</h3>
          {ADMIN_PAGES.map(navLink)}

          <ThemeToggle />
        </div>
      </aside>

      <Tip label="Expand sidebar" side="right">
        <button
          className="icon-btn expand-btn"
          aria-label="Expand sidebar"
          hidden={!collapsed}
          onClick={() => setCollapsed(false)}
        >
          <PanelLeftOpen size={18} />
        </button>
      </Tip>

      {switching && <div className="top-progress" role="progressbar" aria-label="Loading camera" />}

      <main id="content" className={switching ? "is-stale" : undefined} aria-busy={switching || undefined}>
        {error && <div className="status-error">Couldn't load camera data: {error}</div>}
        {/* Re-keyed per section, so pages fade in on navigation but stepping
            between days or views inside the calendar swaps in place. */}
        <div key={section} className="page-enter">
          {section === "admin" && !isAdmin ? (
            <AdminGate onOk={() => setIsAdmin(true)} />
          ) : (
          <Routes>
            <Route path="/" element={<Navigate to="/calendar" replace />} />
            {/* The latest sunset lives in the calendar's Day tab now. /sunset/<camera>/<date>
                stays as the shareable permalink (Flask adds link previews), then opens it here. */}
            <Route path="/sunset" element={<Navigate to="/calendar?view=day" replace />} />
            <Route path="/sunset/:camera/:date" element={<SunsetPermalink />} />
            <Route path="/compare" element={<Navigate to="/calendar" replace />} />
            <Route path="/hsv-tuner" element={<Navigate to="/admin/hsv-tuner" replace />} />
            <Route
              path="/calendar"
              element={withData((d) => <Calendar data={d} camera={dataCamera} onLoadToHsv={isAdmin ? loadToHsv : undefined} />, "calendar")}
            />
            <Route
              path="/admin/archive"
              element={withData((d) => <Archive data={d} camera={dataCamera} />, "rows")}
            />
            <Route
              path="/ranking"
              element={withData((d) => <Ranking data={d} camera={dataCamera} onLoadToHsv={isAdmin ? loadToHsv : undefined} />, "rows")}
            />
            <Route
              path="/score-tracker"
              element={withData(
                (d) => (
                  <Suspense fallback={<PageSkeleton kind="chart" />}>
                    <ScoreTracker data={d} camera={dataCamera} />
                  </Suspense>
                ),
                "chart",
              )}
            />
            <Route
              path="/admin/hsv-tuner"
              element={withData((d) => (
                <HsvTuner allData={d.all_data} tuner={tuner} setTuner={setTuner} onLoadToHsv={loadToHsv} />
              ))}
            />
            <Route path="/ranking-explained" element={<RankingExplained />} />
            {/* Cameras: the config list (read-only, with a request form) over the map; /admin/config is the same page with editing. */}
            <Route path="/cameras" element={<Config />} />
            <Route path="/map" element={<Navigate to="/cameras" replace />} />
            <Route
              path="/admin/my-ranking"
              element={withData((d) => <MyRanking data={d} camera={dataCamera} />, "rows")}
            />
            <Route path="/admin/config" element={<Config admin />} />
            {/* Multipliers live in sunset_code/helpers/hsv_score.json now; the old admin editor is gone. */}
            <Route path="/admin/scoring" element={<Navigate to="/ranking-explained" replace />} />
            <Route path="*" element={<div className="empty">Page not found.</div>} />
          </Routes>
          )}
        </div>
      </main>
    </div>
  );
}

function SunsetPermalink() {
  const { camera, date } = useParams();
  const params = new URLSearchParams({ view: "day", date, camera });
  return <Navigate to={`/calendar?${params}`} replace />;
}

/** Light / dark switch. Starts from the OS setting; a choice sticks in localStorage. */
function ThemeToggle() {
  const systemDark = () => window.matchMedia("(prefers-color-scheme: dark)").matches;
  const [dark, setDark] = useState(() => {
    const chosen = document.documentElement.dataset.theme;
    return chosen ? chosen === "dark" : systemDark();
  });

  function toggle() {
    const next = dark ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    try {
      localStorage.setItem("theme", next);
    } catch {
      // storage blocked: the choice lasts for this visit
    }
    setDark(!dark);
  }

  return (
    <button className="nav-btn theme-toggle" onClick={toggle}>
      {dark ? <Sun size={16} /> : <Moon size={16} />}
      {dark ? "Light mode" : "Dark mode"}
    </button>
  );
}

// Admin pages: moving to one inside the app never reaches the server, so ask for the password here
// (the 401 from /api/admin/ping makes the browser show its login box).
function AdminGate({ onOk }) {
  const [state, setState] = useState("asking");
  const ask = () => {
    setState("asking");
    fetch("/api/admin/ping").then((r) => (r.ok ? onOk() : setState("denied"))).catch(() => setState("denied"));
  };
  useEffect(ask, []);
  if (state === "asking") return <PageSkeleton />;
  return (
    <div className="empty">
      <p>This page is for the admin.</p>
      <button className="btn" onClick={ask}>Log in</button>
    </div>
  );
}
