// Mirrors streamlit_project/sunset_gallery.py, rendered as an actual month calendar.

const WEEKDAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const MONTH_NAMES = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];

export function renderGallery(container, state) {
  if (!state.gallery) {
    state.gallery = { year: null, month: null, selectedDate: null, selectedIndex: 0 };
  }
  const gallery = state.gallery;

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
  container.appendChild(renderMonthGrid(container, state, byDate));

  if (gallery.selectedDate) {
    container.appendChild(renderDetail(container, state));
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
    renderGallery(container, state);
  });

  header.append(prevBtn, title, nextBtn);
  return header;
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
  grid.className = "calendar-grid";

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
        gallery.selectedIndex = 0;
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

function renderDetail(container, state) {
  const gallery = state.gallery;

  const dateImages = state.allData.filter((img) => img.Date === gallery.selectedDate);
  const regular = dateImages
    .filter((img) => !img.Label.toLowerCase().includes("ranked") && !img.Label.toLowerCase().includes("histogram"))
    .sort((a, b) => (a.Time > b.Time ? 1 : -1));
  const special = dateImages.filter(
    (img) => img.Label.toLowerCase().includes("ranked") || img.Label.toLowerCase().includes("histogram")
  );
  const images = [...regular, ...special];

  const wrap = document.createElement("div");
  wrap.className = "detail";

  if (!images.length) return wrap;

  if (gallery.selectedIndex >= images.length) gallery.selectedIndex = 0;
  const current = images[gallery.selectedIndex];

  const header = document.createElement("div");
  header.className = "detail-header";
  const title = document.createElement("h4");
  title.textContent = `${current.Label.slice(3)} - ${gallery.selectedDate}`;
  header.appendChild(title);
  const closeBtn = document.createElement("button");
  closeBtn.className = "btn";
  closeBtn.textContent = "✕ Close";
  closeBtn.addEventListener("click", () => {
    gallery.selectedDate = null;
    renderGallery(container, state);
  });
  header.appendChild(closeBtn);
  wrap.appendChild(header);

  const nav = document.createElement("div");
  nav.className = "detail-nav";
  const prevBtn = document.createElement("button");
  prevBtn.className = "btn";
  prevBtn.textContent = "← Previous";
  prevBtn.disabled = gallery.selectedIndex === 0;
  prevBtn.addEventListener("click", () => {
    gallery.selectedIndex -= 1;
    renderGallery(container, state);
  });
  const info = document.createElement("div");
  info.className = "info";
  info.textContent = `Image ${gallery.selectedIndex + 1} of ${images.length} | Time: ${current.Time} | Score: ${current.Score.toFixed(1)}%`;
  const nextBtn = document.createElement("button");
  nextBtn.className = "btn";
  nextBtn.textContent = "Next →";
  nextBtn.disabled = gallery.selectedIndex >= images.length - 1;
  nextBtn.addEventListener("click", () => {
    gallery.selectedIndex += 1;
    renderGallery(container, state);
  });
  nav.append(prevBtn, info, nextBtn);
  wrap.appendChild(nav);

  const mainImgWrap = document.createElement("div");
  mainImgWrap.className = "detail-main-img";
  const mainImg = document.createElement("img");
  mainImg.src = current.Image;
  mainImgWrap.appendChild(mainImg);
  wrap.appendChild(mainImgWrap);

  const stripHeading = document.createElement("h5");
  stripHeading.textContent = "All images from this date:";
  wrap.appendChild(stripHeading);

  const strip = document.createElement("div");
  strip.className = "thumb-strip";
  images.forEach((img, idx) => {
    const thumb = document.createElement("div");
    thumb.className = "thumb" + (idx === gallery.selectedIndex ? " selected" : "");
    const thumbImg = document.createElement("img");
    thumbImg.src = img.Image;
    thumbImg.loading = "lazy";
    const label = document.createElement("div");
    label.className = "label";
    label.textContent = img.Label.slice(3);
    thumb.append(thumbImg, label);
    thumb.addEventListener("click", () => {
      gallery.selectedIndex = idx;
      renderGallery(container, state);
    });
    strip.appendChild(thumb);
  });
  wrap.appendChild(strip);

  return wrap;
}
