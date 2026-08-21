import { renderGallery } from "./pages/gallery.js";
import { renderRanking } from "./pages/ranking.js";
import { renderScoreTracker } from "./pages/scoretracker.js";
import { renderHsvTuner } from "./pages/hsvtuner.js";

const content = document.getElementById("content");
const cameraSelect = document.getElementById("camera-select");
const navButtons = document.querySelectorAll(".nav-btn");
const layout = document.getElementById("layout");
const sidebar = document.getElementById("sidebar");
const collapseBtn = document.getElementById("collapse-btn");
const expandBtn = document.getElementById("expand-btn");

collapseBtn.addEventListener("click", (e) => {
  e.stopPropagation();
  layout.classList.add("sidebar-collapsed");
  expandBtn.hidden = false;
});
expandBtn.addEventListener("click", (e) => {
  e.stopPropagation();
  layout.classList.remove("sidebar-collapsed");
  expandBtn.hidden = true;
});

// Clicking blank space outside the sidebar collapses it while it's open.
// Clicks on actual controls (buttons, inputs, images, clickable cells/thumbs)
// are left alone so interacting with the page doesn't also close it.
const INTERACTIVE_SELECTOR = "button, a, input, select, textarea, img, .calendar-cell.has-image, .thumb";

document.addEventListener("click", (e) => {
  if (layout.classList.contains("sidebar-collapsed")) return;
  if (sidebar.contains(e.target)) return;
  if (e.target.closest(INTERACTIVE_SELECTOR)) return;
  layout.classList.add("sidebar-collapsed");
  expandBtn.hidden = false;
});

const pages = {
  gallery: renderGallery,
  ranking: renderRanking,
  scoretracker: renderScoreTracker,
  hsvtuner: renderHsvTuner,
};

// Mirrors app.py's session state: current page + fetched data for the selected camera
const state = {
  page: "gallery",
  camera: null,
  sunsetData: [],
  allData: [],
  rankedImages: [],
  goToPage(pageName) {
    goToPage(pageName);
  },
};

async function loadCameras() {
  const res = await fetch("/api/cameras");
  const cameras = await res.json();
  cameraSelect.innerHTML = "";
  for (const cam of cameras) {
    const opt = document.createElement("option");
    opt.value = cam;
    opt.textContent = cam;
    cameraSelect.appendChild(opt);
  }
  return cameras;
}

async function loadCameraData(camera) {
  content.innerHTML = '<div class="loading">Loading…</div>';
  const res = await fetch(`/api/data?camera=${encodeURIComponent(camera)}`);
  const data = await res.json();
  state.camera = camera;
  state.sunsetData = data.sunset_data;
  state.allData = data.all_data;
  state.rankedImages = data.ranked_images;
}

function renderPage() {
  content.innerHTML = "";
  pages[state.page](content, state);
}

function goToPage(pageName) {
  for (const b of navButtons) b.classList.toggle("active", b.dataset.page === pageName);
  state.page = pageName;
  renderPage();
}

cameraSelect.addEventListener("change", async () => {
  await loadCameraData(cameraSelect.value);
  renderPage();
});

for (const btn of navButtons) {
  btn.addEventListener("click", () => goToPage(btn.dataset.page));
}

(async function init() {
  const cameras = await loadCameras();
  const defaultCamera = cameras.includes("btv_echo_cam") ? "btv_echo_cam" : cameras[0] || "btv_echo_cam";
  cameraSelect.value = defaultCamera;
  await loadCameraData(defaultCamera);
  renderPage();
})();
