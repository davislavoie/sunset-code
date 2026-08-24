// Mirrors streamlit_project/sunset_gallery.py, rendered as an actual calendar
// with Day / Week / Month / Year views.

import { mountDayDetail } from "../dayDetail.js";
import { loadImageIntoTuner } from "./hsvtuner.js";
import { makeZoomable } from "../lightbox.js";

const WEEKDAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const MONTH_NAMES = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];

function toISODate(d) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

function fromISODate(s) {
  const [y, m, d] = s.split("-").map(Number);
  return new Date(y, m - 1, d);
}

function shiftDate(isoStr, deltaDays) {
  const d = fromISODate(isoStr);
  d.setDate(d.getDate() + deltaDays);
  return toISODate(d);
}

// Labels are formatted like "01_2h_pre_...", "07_sunset_...", "11_ranked_...",
// "12_histogram_..." -- the leading number is the true capture order.
function labelOrder(label) {
  return parseInt(label.slice(0, 2), 10);
}

function byLabelOrder(a, b) {
  return labelOrder(a.Label) - labelOrder(b.Label);
}

export function renderGallery(container, state) {
  if (!state.gallery) {
    state.gallery = {
      viewMode: "month",
      year: null, month: null,
      focusDate: null,
      expandedDate: null,
      cellHeight: 110,
    };
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
    gallery.focusDate = latest;
  }

  container.appendChild(renderViewTabs(container, state));

  if (gallery.viewMode === "day") {
    container.appendChild(renderDayView(container, state));
  } else if (gallery.viewMode === "week") {
    container.appendChild(renderWeekView(container, state));
  } else if (gallery.viewMode === "year") {
    container.appendChild(renderYearView(container, state, byDate));
  } else {
    container.appendChild(renderMonthHeader(container, state));
    container.appendChild(renderSizeControl(state));
    container.appendChild(renderMonthGrid(container, state, byDate));

    if (gallery.expandedDate) {
      const mount = document.createElement("div");
      container.appendChild(mount);
      mountDayDetail(mount, gallery.expandedDate, state.allData, {
        onClose: () => {
          gallery.expandedDate = null;
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
}

function renderViewTabs(container, state) {
  const gallery = state.gallery;
  const row = document.createElement("div");
  row.className = "view-tabs";

  const tabGroup = document.createElement("div");
  tabGroup.className = "view-tab-group";
  for (const [key, label] of [["day", "Day"], ["week", "Week"], ["month", "Month"], ["year", "Year"]]) {
    const btn = document.createElement("button");
    btn.className = "btn view-tab-btn" + (gallery.viewMode === key ? " active" : "");
    btn.textContent = label;
    btn.addEventListener("click", () => {
      gallery.viewMode = key;
      gallery.expandedDate = null;
      renderGallery(container, state);
    });
    tabGroup.appendChild(btn);
  }
  row.appendChild(tabGroup);

  const todayBtn = document.createElement("button");
  todayBtn.className = "btn today-btn";
  todayBtn.textContent = "Today";
  todayBtn.addEventListener("click", () => {
    const now = new Date();
    gallery.year = now.getFullYear();
    gallery.month = now.getMonth();
    gallery.focusDate = toISODate(now);
    renderGallery(container, state);
  });
  row.appendChild(todayBtn);

  return row;
}

// ---------------------------------------------------------------------------
// Day view -- every capture from a single day, with its stats, all at once.
// ---------------------------------------------------------------------------
function renderDayView(container, state) {
  const gallery = state.gallery;
  const wrap = document.createElement("div");

  const header = document.createElement("div");
  header.className = "calendar-header";

  const prevBtn = document.createElement("button");
  prevBtn.className = "btn cal-arrow";
  prevBtn.textContent = "‹";
  prevBtn.addEventListener("click", () => {
    gallery.focusDate = shiftDate(gallery.focusDate, -1);
    renderGallery(container, state);
  });

  const title = document.createElement("div");
  title.className = "calendar-title";
  title.textContent = fromISODate(gallery.focusDate).toLocaleDateString(undefined, {
    weekday: "long", year: "numeric", month: "long", day: "numeric",
  });

  const isToday = gallery.focusDate === toISODate(new Date());
  const nextBtn = document.createElement("button");
  nextBtn.className = "btn cal-arrow";
  nextBtn.textContent = "›";
  nextBtn.disabled = isToday;
  nextBtn.addEventListener("click", () => {
    gallery.focusDate = shiftDate(gallery.focusDate, 1);
    renderGallery(container, state);
  });

  header.append(prevBtn, title, nextBtn);
  wrap.appendChild(header);

  const dayImages = state.allData
    .filter((img) => img.Date === gallery.focusDate)
    .sort(byLabelOrder);

  if (!dayImages.length) {
    const empty = document.createElement("div");
    empty.className = "empty";
    empty.textContent = "No captures for this day.";
    wrap.appendChild(empty);
    return wrap;
  }

  const grid = document.createElement("div");
  grid.className = "day-view-grid";
  for (const img of dayImages) {
    const card = document.createElement("div");
    card.className = "day-view-card";

    const imageEl = document.createElement("img");
    imageEl.src = img.Image;
    imageEl.loading = "lazy";
    makeZoomable(imageEl);
    card.appendChild(imageEl);

    const caption = document.createElement("div");
    caption.className = "day-view-caption";
    const displayLabel = /^(07_|11_|12_)/.test(img.Label) ? img.Label.slice(3) : img.Label;
    caption.innerHTML = `<strong>${displayLabel}</strong><br>${img.Time} &middot; Score: ${img.Score.toFixed(1)}%`;
    card.appendChild(caption);

    grid.appendChild(card);
  }
  wrap.appendChild(grid);
  return wrap;
}

// ---------------------------------------------------------------------------
// Week view -- 7 columns (one per weekday), each a vertical filmstrip of
// that day's captures in chronological order.
// ---------------------------------------------------------------------------
function renderWeekView(container, state) {
  const gallery = state.gallery;
  const wrap = document.createElement("div");

  const focus = fromISODate(gallery.focusDate);
  const weekStart = new Date(focus);
  weekStart.setDate(focus.getDate() - focus.getDay());
  const weekEnd = new Date(weekStart);
  weekEnd.setDate(weekStart.getDate() + 6);

  const now = new Date();
  const todayWeekStart = new Date(now);
  todayWeekStart.setDate(now.getDate() - now.getDay());
  const isCurrentWeek = toISODate(weekStart) === toISODate(todayWeekStart);

  // Build lookup for sunset data (one entry per day)
  const sunsetByDate = new Map();
  for (const item of state.sunsetData) {
    sunsetByDate.set(item.Date, item);
  }

  const header = document.createElement("div");
  header.className = "calendar-header";

  const prevBtn = document.createElement("button");
  prevBtn.className = "btn cal-arrow";
  prevBtn.textContent = "‹";
  prevBtn.addEventListener("click", () => {
    gallery.focusDate = shiftDate(gallery.focusDate, -7);
    renderGallery(container, state);
  });

  const title = document.createElement("div");
  title.className = "calendar-title";
  const fmt = (d) => d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
  title.textContent = `${fmt(weekStart)} – ${fmt(weekEnd)}`;

  const nextBtn = document.createElement("button");
  nextBtn.className = "btn cal-arrow";
  nextBtn.textContent = "›";
  nextBtn.disabled = isCurrentWeek;
  nextBtn.addEventListener("click", () => {
    gallery.focusDate = shiftDate(gallery.focusDate, 7);
    renderGallery(container, state);
  });

  header.append(prevBtn, title, nextBtn);
  wrap.appendChild(header);

  const grid = document.createElement("div");
  grid.className = "week-view-grid";

  for (let i = 0; i < 7; i++) {
    const dayDate = new Date(weekStart);
    dayDate.setDate(weekStart.getDate() + i);
    const dateStr = toISODate(dayDate);

    const col = document.createElement("div");
    col.className = "week-day-col";

    const colHeader = document.createElement("div");
    colHeader.className = "week-day-header";
    colHeader.textContent = `${WEEKDAYS[i]} ${dayDate.getDate()}`;
    col.appendChild(colHeader);

    const sunsetEntry = sunsetByDate.get(dateStr);
    const dayImages = state.allData
      .filter((img) => img.Date === dateStr)
      .sort(byLabelOrder);

    if (dayImages.length) {
      // Show time from sunset entry and max score from all images
      const maxScore = Math.max(...dayImages.map((img) => img.Score));
      if (sunsetEntry) {
        const stats = document.createElement("div");
        stats.className = "week-day-stats";
        stats.innerHTML = `<span class="week-day-time">${sunsetEntry.Time}</span><span class="week-day-score">${maxScore.toFixed(0)}%</span>`;
        col.appendChild(stats);
      }

      for (const img of dayImages) {
        const thumbWrap = document.createElement("div");
        thumbWrap.className = "week-day-thumb-wrap";

        const thumb = document.createElement("img");
        thumb.className = "week-day-thumb";
        thumb.src = img.Image;
        thumb.loading = "lazy";
        thumb.title = `${img.Time} — Score: ${img.Score.toFixed(1)}%`;
        makeZoomable(thumb);
        thumbWrap.appendChild(thumb);

        const scoreLabel = document.createElement("div");
        scoreLabel.className = "week-thumb-score";
        scoreLabel.textContent = `${img.Score.toFixed(0)}%`;
        thumbWrap.appendChild(scoreLabel);

        col.appendChild(thumbWrap);
      }
    } else {
      const none = document.createElement("div");
      none.className = "week-day-empty";
      none.textContent = "—";
      col.appendChild(none);
    }

    grid.appendChild(col);
  }
  wrap.appendChild(grid);
  return wrap;
}

// ---------------------------------------------------------------------------
// Year view -- one row per month, month name on the left, then only the days
// that actually have a capture, laid out left-to-right (missing days skipped).
// ---------------------------------------------------------------------------
function renderYearView(container, state, byDate) {
  const gallery = state.gallery;
  const wrap = document.createElement("div");

  const header = document.createElement("div");
  header.className = "calendar-header";

  const prevBtn = document.createElement("button");
  prevBtn.className = "btn cal-arrow";
  prevBtn.textContent = "‹";
  prevBtn.addEventListener("click", () => {
    gallery.year -= 1;
    renderGallery(container, state);
  });

  const title = document.createElement("div");
  title.className = "calendar-title";
  title.textContent = `${gallery.year}`;

  const nextBtn = document.createElement("button");
  nextBtn.className = "btn cal-arrow";
  nextBtn.textContent = "›";
  nextBtn.disabled = gallery.year >= new Date().getFullYear();
  nextBtn.addEventListener("click", () => {
    gallery.year += 1;
    renderGallery(container, state);
  });

  header.append(prevBtn, title, nextBtn);
  wrap.appendChild(header);

  const monthsGrid = document.createElement("div");
  monthsGrid.className = "year-view-list";

  for (let m = 0; m < 12; m++) {
    const row = document.createElement("div");
    row.className = "year-month-row";

    const monthLabel = document.createElement("div");
    monthLabel.className = "year-month-row-label";
    monthLabel.textContent = MONTH_NAMES[m];
    row.appendChild(monthLabel);

    const strip = document.createElement("div");
    strip.className = "year-month-row-strip";

    const detailMount = document.createElement("div");
    let daySession = null;
    let openDate = null;

    const daysInMonth = new Date(gallery.year, m + 1, 0).getDate();
    for (let day = 1; day <= daysInMonth; day++) {
      const dateStr = `${gallery.year}-${String(m + 1).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
      const entry = byDate.get(dateStr);
      if (!entry) continue; // skip days with no captures entirely

      const cell = document.createElement("div");
      cell.className = "year-mini-cell has-image" + (dateStr === openDate ? " selected" : "");

      const img = document.createElement("img");
      img.src = entry.Image;
      img.loading = "lazy";
      img.title = `${dateStr} — ${entry.Score.toFixed(0)}%`;
      cell.appendChild(img);
      cell.addEventListener("click", () => {
        if (daySession && openDate === dateStr) {
          daySession.close();
          daySession = null;
          openDate = null;
          cell.classList.remove("selected");
          return;
        }
        for (const c of strip.children) c.classList.remove("selected");
        if (daySession) daySession.close();
        openDate = dateStr;
        cell.classList.add("selected");
        daySession = mountDayDetail(detailMount, dateStr, state.allData, {
          onClose: () => {
            daySession = null;
            openDate = null;
            cell.classList.remove("selected");
          },
          onLoadToHsv: async (url) => {
            await loadImageIntoTuner(state, url);
            state.goToPage("hsvtuner");
          },
        });
      });

      strip.appendChild(cell);
    }

    if (!strip.children.length) {
      const none = document.createElement("div");
      none.className = "year-month-row-empty";
      none.textContent = "No captures";
      strip.appendChild(none);
    }

    row.appendChild(strip);
    monthsGrid.appendChild(row);
    monthsGrid.appendChild(detailMount);
  }
  wrap.appendChild(monthsGrid);
  return wrap;
}

// ---------------------------------------------------------------------------
// Month view (the original calendar grid)
// ---------------------------------------------------------------------------
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
    gallery.expandedDate = null;
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
    gallery.expandedDate = null;
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
        gallery.expandedDate = dateStr;
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
