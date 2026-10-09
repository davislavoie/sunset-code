import { lazy, Suspense, useEffect, useState } from "react";
import { NavLink, Navigate, Route, Routes, useLocation, useNavigate, useParams, useSearchParams } from "react-router";
import { fetchCameraData, getJson } from "./api.js";
import Dropdown from "./Dropdown.jsx";
import Calendar from "./pages/Calendar.jsx";
import Compare from "./pages/Compare.jsx";
import Config from "./pages/Config.jsx";
import HsvTuner, { INITIAL_TUNER, loadGalleryCanvas } from "./pages/HsvTuner.jsx";
import Ranking from "./pages/Ranking.jsx";
import RankingExplained from "./pages/RankingExplained.jsx";
import { PageSkeleton } from "./Skeleton.jsx";

// Chart pages (bklit/visx, Leaflet) only download when opened.
const CameraMap = lazy(() => import("./pages/CameraMap.jsx"));
const ScoreTracker = lazy(() => import("./pages/ScoreTracker.jsx"));

const DEFAULT_CAMERA = "btv_echo_cam";
const MOBILE_BREAKPOINT = 768;
const isMobile = () => window.innerWidth <= MOBILE_BREAKPOINT;

const PUBLIC_PAGES = [
  ["/calendar", "Sunset Calendar"],
  ["/ranking", "Ranked Images"],
  ["/score-tracker", "Score Tracker"],
  ["/hsv-tuner", "HSV Tuner"],
  ["/ranking-explained", "Ranking Explained"],
  ["/map", "Camera Map"],
  ["/compare", "Compare"],
];
// Everything that writes lives under /admin so a reverse proxy can gate it.
const ADMIN_PAGES = [
  ["/admin/config", "Config"],
  ["/admin/scoring", "Scoring"],
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
    setTuner((t) => ({ ...t, loaded: [...t.loaded, { id: crypto.randomUUID(), url, canvas }] }));
    if (go) navigate("/hsv-tuner");
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
          <button className="icon-btn collapse-btn" title="Collapse sidebar" onClick={() => setCollapsed(true)}>
            «
          </button>

          <div className="sidebar-header">
            <h2>Navigation</h2>
          </div>

          <h3>Camera Selection</h3>
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
        </div>
      </aside>

      <button
        className="icon-btn expand-btn"
        title="Expand sidebar"
        hidden={!collapsed}
        onClick={() => setCollapsed(false)}
      >
        »
      </button>

      {switching && <div className="top-progress" role="progressbar" aria-label="Loading camera" />}

      <main id="content" className={switching ? "is-stale" : undefined} aria-busy={switching || undefined}>
        {error && <div className="status-error">Couldn't load camera data: {error}</div>}
        {/* Re-keyed per section, so pages fade in on navigation but stepping
            between days or views inside the calendar swaps in place. */}
        <div key={section} className="page-enter">
          <Routes>
            <Route path="/" element={<Navigate to="/calendar" replace />} />
            {/* The latest sunset lives in the calendar's Day tab now. /sunset/<camera>/<date>
                stays as the shareable permalink (Flask adds link previews), then opens it here. */}
            <Route path="/sunset" element={<Navigate to="/calendar?view=day" replace />} />
            <Route path="/sunset/:camera/:date" element={<SunsetPermalink />} />
            <Route path="/compare" element={<Compare cameras={cameras} defaultCamera={camera} />} />
            <Route
              path="/calendar"
              element={withData((d) => <Calendar data={d} camera={dataCamera} onLoadToHsv={loadToHsv} />, "calendar")}
            />
            <Route
              path="/ranking"
              element={withData((d) => <Ranking data={d} />, "rows")}
            />
            <Route
              path="/score-tracker"
              element={withData(
                (d) => (
                  <Suspense fallback={<PageSkeleton kind="chart" />}>
                    <ScoreTracker data={d} />
                  </Suspense>
                ),
                "chart",
              )}
            />
            <Route
              path="/hsv-tuner"
              element={withData((d) => (
                <HsvTuner allData={d.all_data} tuner={tuner} setTuner={setTuner} onLoadToHsv={loadToHsv} />
              ))}
            />
            <Route path="/ranking-explained" element={<RankingExplained rankedImages={data?.ranked_images ?? []} />} />
            <Route
              path="/map"
              element={
                <Suspense fallback={<PageSkeleton />}>
                  <CameraMap />
                </Suspense>
              }
            />
            <Route path="/admin/config" element={<Config />} />
            <Route
              path="/admin/scoring"
              element={<RankingExplained rankedImages={data?.ranked_images ?? []} admin />}
            />
            <Route path="*" element={<div className="empty">Page not found.</div>} />
          </Routes>
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
