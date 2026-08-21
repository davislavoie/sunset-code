// Mirrors streamlit_project/ranking_tab.py

import { openLightbox, closeLightbox } from "../lightbox.js";
import { mountDayDetail } from "../dayDetail.js";
import { loadImageIntoTuner } from "./hsvtuner.js";

export function renderRanking(container, state) {
  if (!state.ranking) {
    state.ranking = { sortBy: "Score", order: "Highest to Lowest" };
  }
  const ranking = state.ranking;

  container.innerHTML = "";

  const title = document.createElement("h2");
  title.textContent = "Ranked Images";
  container.appendChild(title);

  const controls = document.createElement("div");
  controls.className = "ranking-controls";

  const sortSelect = makeSelect("Sort by:", ["Score", "Date", "Time"], ranking.sortBy, (v) => {
    ranking.sortBy = v;
    renderRanking(container, state);
  });
  const orderSelect = makeSelect(
    "Order:",
    ["Highest to Lowest", "Lowest to Highest"],
    ranking.order,
    (v) => {
      ranking.order = v;
      renderRanking(container, state);
    }
  );
  controls.append(sortSelect, orderSelect);
  container.appendChild(controls);

  const divider = document.createElement("hr");
  container.appendChild(divider);

  let rows = [...state.rankedImages];
  if (!rows.length) {
    const empty = document.createElement("div");
    empty.className = "empty";
    empty.textContent = "No data available.";
    container.appendChild(empty);
    return;
  }

  const ascending = ranking.order === "Lowest to Highest";
  const key = { Score: "Score", Date: "Date", Time: "Time" }[ranking.sortBy];
  rows.sort((a, b) => {
    const av = a[key], bv = b[key];
    const cmp = av < bv ? -1 : av > bv ? 1 : 0;
    return ascending ? cmp : -cmp;
  });

  for (const row of rows) {
    const rowEl = document.createElement("div");
    rowEl.className = "ranking-row";

    rowEl.appendChild(imgCell(row["Ranked Image"]));
    rowEl.appendChild(imgCell(row["Raw Image"]));
    rowEl.appendChild(imgCell(row["HSV Image"]));

    const metric = document.createElement("div");
    metric.className = "score-cell";
    metric.innerHTML = `<div class="metric-label">Score</div><div class="metric-value">${row.Score.toFixed(2)}%</div>`;
    rowEl.appendChild(metric);

    const info = document.createElement("div");
    info.className = "info-cell";
    const rawUrl = row["Raw Image"];
    const rawLabel = rawUrl ? rawUrl.split("/").pop().split(".")[0] : "No raw image";
    info.innerHTML = `
      <div><strong>Date:</strong> ${row.Date || "N/A"}</div>
      <div><strong>Time:</strong> ${row.Time || "N/A"}</div>
      <div><strong>Label:</strong> ${rawUrl ? rawLabel : "No raw image"}</div>
    `;
    const calendarBtn = document.createElement("button");
    calendarBtn.className = "btn show-in-calendar-btn";
    calendarBtn.textContent = "Show in Calendar";
    info.appendChild(calendarBtn);
    rowEl.appendChild(info);

    container.appendChild(rowEl);

    const detailMount = document.createElement("div");
    container.appendChild(detailMount);
    let daySession = null;

    calendarBtn.addEventListener("click", () => {
      if (daySession) {
        daySession.close();
        daySession = null;
        calendarBtn.textContent = "Show in Calendar";
      } else {
        daySession = mountDayDetail(detailMount, row.Date, state.allData, {
          onClose: () => {
            daySession = null;
            calendarBtn.textContent = "Show in Calendar";
          },
          onLoadToHsv: async (url) => {
            await loadImageIntoTuner(state, url);
            state.goToPage("hsvtuner");
          },
        });
        calendarBtn.textContent = "Hide";
      }
    });

    const hr = document.createElement("hr");
    container.appendChild(hr);
  }
}

function imgCell(url) {
  const cell = document.createElement("div");
  if (url) {
    cell.className = "ranked-img-cell";

    const img = document.createElement("img");
    img.src = url;
    img.loading = "lazy";
    cell.appendChild(img);

    const fsBtn = document.createElement("button");
    fsBtn.className = "fullscreen-toggle-btn";
    fsBtn.textContent = "⛶";
    fsBtn.title = "View fullscreen";
    fsBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      if (fsBtn.textContent === "✕") {
        closeLightbox();
        return;
      }
      openLightbox(url, {
        onClose: () => {
          fsBtn.textContent = "⛶";
          fsBtn.title = "View fullscreen";
        },
      });
      fsBtn.textContent = "✕";
      fsBtn.title = "Close fullscreen";
    });
    cell.appendChild(fsBtn);
  }
  return cell;
}

function makeSelect(labelText, options, value, onChange) {
  const wrap = document.createElement("div");
  const label = document.createElement("label");
  label.textContent = labelText;
  label.style.display = "block";
  label.style.marginBottom = "4px";
  label.style.color = "var(--muted)";
  label.style.fontSize = "0.85em";

  const select = document.createElement("select");
  for (const opt of options) {
    const o = document.createElement("option");
    o.value = opt;
    o.textContent = opt;
    if (opt === value) o.selected = true;
    select.appendChild(o);
  }
  select.addEventListener("change", () => onChange(select.value));

  wrap.append(label, select);
  return wrap;
}
