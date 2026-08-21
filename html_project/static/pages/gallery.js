// Mirrors streamlit_project/sunset_gallery.py, rendered as an actual month calendar.

import { mountDayDetail } from "../dayDetail.js";
import { loadImageIntoTuner } from "./hsvtuner.js";

const WEEKDAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const MONTH_NAMES = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];

export function renderGallery(container, state) {
  if (!state.gallery) {
    state.gallery = { year: null, month: null, selectedDate: null, cellHeight: 110 };
  }
  const gallery = state.gallery;

  document.documentElement.style.setProperty("--cal-row-height", `${gallery.cellHeight}px`);

  container.innerHTML = "";

  const heading = document.createElement("h3");
  heading.textContent = "Sunset Calendar";
  container.appendChild(heading);

  if (!state.sunsetData.length) {
    const empty = document.createElement("div");
    empty.className = "empty";
    empty.textContent = "No data available.";
    container.appendChild(empty);
    return;
  }

  // One entry per captured day, keyed by "YYYY-MM-DD"
  const byDate = new Map();
  for (const item of state.sunsetData) {
    byDate.set(item.Date, item);
  }

  if (gallery.year === null) {
    const latest = [...byDate.keys()].sort().at(-1);
    const [y, m] = latest.split("-").map(Number);
    gallery.year = y;
    gallery.month = m - 1; // 0-indexed
  }

  container.appendChild(renderMonthHeader(container, state));
  container.appendChild(renderSizeControl(state));
  container.appendChild(renderMonthGrid(container, state, byDate));

  if (gallery.selectedDate) {
    const mount = document.createElement("div");
    container.appendChild(mount);
    mountDayDetail(mount, gallery.selectedDate, state.allData, {
      onClose: () => {
        gallery.selectedDate = null;
        renderGallery(container, state);
      },
      onLoadToHsv: async (url) => {
        await loadImageIntoTuner(state, url);
        state.goToPage("hsvtuner");
      },
    });
    const scrollToBottom = () => mount.scrollIntoView({ behavior: "smooth", block: "end" });
    const mainImg = mount.querySelector(".detail-main-img img");
    if (mainImg && !mainImg.complete) {
      mainImg.addEventListener("load", scrollToBottom, { once: true });
    } else {
      scrollToBottom();
    }
  }
}

function renderMonthHeader(container, state) {
  const gallery = state.gallery;
  const header = document.createElement("div");
  header.className = "calendar-header";

  const prevBtn = document.createElement("button");
  prevBtn.className = "btn cal-arrow";
  prevBtn.textContent = "‹";
  prevBtn.title = "Previous month";
  prevBtn.addEventListener("click", () => {
    gallery.month -= 1;
    if (gallery.month < 0) {
      gallery.month = 11;
      gallery.year -= 1;
    }
    gallery.selectedDate = null;
    renderGallery(container, state);
  });

  const title = document.createElement("div");
  title.className = "calendar-title";
  title.textContent = `${MONTH_NAMES[gallery.month]} ${gallery.year}`;

  const now = new Date();
  const isCurrentMonth = gallery.year === now.getFullYear() && gallery.month === now.getMonth();

  const nextBtn = document.createElement("button");
  nextBtn.className = "btn cal-arrow";
  nextBtn.textContent = "›";
  nextBtn.title = "Next month";
  nextBtn.disabled = isCurrentMonth;
  nextBtn.addEventListener("click", () => {
    gallery.month += 1;
    if (gallery.month > 11) {
      gallery.month = 0;
      gallery.year += 1;
    }
    gallery.selectedDate = null;
    renderGallery(container, state);
  });

  header.append(prevBtn, title, nextBtn);
  return header;
}

function renderSizeControl(state) {
  const gallery = state.gallery;
  const wrap = document.createElement("div");
  wrap.className = "cal-size-control";

  const label = document.createElement("label");
  label.textContent = `Size: ${gallery.cellHeight}px`;

  const slider = document.createElement("input");
  slider.type = "range";
  slider.min = 50;
  slider.max = 220;
  slider.value = gallery.cellHeight;
  slider.addEventListener("input", () => {
    gallery.cellHeight = Number(slider.value);
    label.textContent = `Size: ${gallery.cellHeight}px`;
    document.documentElement.style.setProperty("--cal-row-height", `${gallery.cellHeight}px`);
  });

  wrap.append(label, slider);
  return wrap;
}

function renderMonthGrid(container, state, byDate) {
  const gallery = state.gallery;
  const wrap = document.createElement("div");

  const weekdayRow = document.createElement("div");
  weekdayRow.className = "calendar-grid weekday-row";
  for (const wd of WEEKDAYS) {
    const cell = document.createElement("div");
    cell.className = "weekday-label";
    cell.textContent = wd;
    weekdayRow.appendChild(cell);
  }
  wrap.appendChild(weekdayRow);

  const firstOfMonth = new Date(gallery.year, gallery.month, 1);
  const startWeekday = firstOfMonth.getDay();
  const daysInMonth = new Date(gallery.year, gallery.month + 1, 0).getDate();
  const totalCells = startWeekday + daysInMonth;
  const trailingBlanks = (7 - (totalCells % 7)) % 7;

  const grid = document.createElement("div");
  grid.className = "calendar-grid day-grid";

  for (let i = 0; i < startWeekday; i++) {
    grid.appendChild(blankCell());
  }

  for (let day = 1; day <= daysInMonth; day++) {
    const dateStr = `${gallery.year}-${String(gallery.month + 1).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
    const entry = byDate.get(dateStr);

    const cell = document.createElement("div");
    cell.className = "calendar-cell" + (entry ? " has-image" : "");

    const dayLabel = document.createElement("div");
    dayLabel.className = "day-number";
    dayLabel.textContent = day;
    cell.appendChild(dayLabel);

    if (entry) {
      const img = document.createElement("img");
      img.src = entry.Image;
      img.loading = "lazy";
      cell.appendChild(img);

      const time = document.createElement("div");
      time.className = "day-time";
      time.textContent = entry.Time;
      cell.appendChild(time);

      const score = document.createElement("div");
      score.className = "day-score";
      score.textContent = `${entry.Score.toFixed(0)}%`;
      cell.appendChild(score);

      cell.addEventListener("click", () => {
        gallery.selectedDate = dateStr;
        renderGallery(container, state);
      });
    }

    grid.appendChild(cell);
  }

  for (let i = 0; i < trailingBlanks; i++) {
    grid.appendChild(blankCell());
  }

  wrap.appendChild(grid);
  return wrap;
}

function blankCell() {
  const cell = document.createElement("div");
  cell.className = "calendar-cell empty-cell";
  return cell;
}

