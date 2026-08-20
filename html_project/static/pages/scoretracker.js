// Mirrors streamlit_project/score_tracker.py

const AXIS_KEYS = {
  "Date Only": "Date",
  "Time Only": "Time",
  Score: "Score",
};

export function renderScoreTracker(container, state) {
  if (!state.scoretracker) {
    state.scoretracker = { xAxis: "Date Only", yAxis: "Score", tab: "chart", selectedIndex: null };
  }
  const st = state.scoretracker;

  container.innerHTML = "";

  const title = document.createElement("h2");
  title.textContent = "Score Tracker";
  container.appendChild(title);
  const subtitle = document.createElement("p");
  subtitle.textContent = "Track and visualize sunset scores over time";
  container.appendChild(subtitle);

  const rows = state.rankedImages;
  if (!rows.length) {
    const empty = document.createElement("div");
    empty.className = "empty";
    empty.textContent = "No data available.";
    container.appendChild(empty);
    return;
  }

  const controls = document.createElement("div");
  controls.className = "axis-controls";
  controls.append(
    makeSelect("X-Axis:", Object.keys(AXIS_KEYS), st.xAxis, (v) => {
      st.xAxis = v;
      renderScoreTracker(container, state);
    }),
    makeSelect("Y-Axis:", Object.keys(AXIS_KEYS), st.yAxis, (v) => {
      st.yAxis = v;
      renderScoreTracker(container, state);
    })
  );
  container.appendChild(controls);
  container.appendChild(document.createElement("hr"));

  const tabs = document.createElement("div");
  tabs.className = "tabs";
  for (const tabName of ["Line Chart", "Data"]) {
    const key = tabName === "Line Chart" ? "chart" : "data";
    const btn = document.createElement("button");
    btn.className = "tab-btn" + (st.tab === key ? " active" : "");
    btn.textContent = tabName;
    btn.addEventListener("click", () => {
      st.tab = key;
      renderScoreTracker(container, state);
    });
    tabs.appendChild(btn);
  }
  container.appendChild(tabs);

  const xCol = AXIS_KEYS[st.xAxis];
  const yCol = AXIS_KEYS[st.yAxis];

  const indexed = rows.map((r, i) => ({ ...r, _idx: i }));
  const sorted = [...indexed].sort((a, b) => (a[xCol] < b[xCol] ? -1 : a[xCol] > b[xCol] ? 1 : 0));

  const tabPane = document.createElement("div");
  container.appendChild(tabPane);

  if (st.tab === "chart") {
    renderChartTab(tabPane, state, sorted, xCol, yCol, st);
  } else {
    renderDataTab(tabPane, rows);
  }

  renderSummary(container, rows);
}

function renderChartTab(pane, state, sorted, xCol, yCol, st) {
  const chartDiv = document.createElement("div");
  chartDiv.id = "score-chart";
  pane.appendChild(chartDiv);

  const trace = {
    x: sorted.map((r) => r[xCol]),
    y: sorted.map((r) => r[yCol]),
    text: sorted.map((r) => r.Label),
    customdata: sorted.map((r) => r._idx),
    mode: "lines+markers",
    type: "scatter",
    name: "Sunset Data",
    hovertemplate: `<b>%{text}</b><br>${st.xAxis}: %{x}<br>${st.yAxis}: %{y:.2f}<br>Click to see image<extra></extra>`,
    line: { width: 2 },
    marker: { size: 8 },
  };

  const layout = {
    title: `${st.yAxis} vs ${st.xAxis} (Click points to see images)`,
    xaxis: { title: st.xAxis, showgrid: true, gridcolor: "rgba(128,128,128,0.3)" },
    yaxis: { title: st.yAxis, showgrid: true, gridcolor: "rgba(128,128,128,0.3)" },
    height: 600,
    hovermode: "closest",
    paper_bgcolor: "rgba(0,0,0,0)",
    plot_bgcolor: "rgba(0,0,0,0)",
    font: { color: "#f0f2f6" },
  };

  Plotly.newPlot(chartDiv, [trace], layout, { responsive: true });

  chartDiv.on("plotly_click", (evt) => {
    const point = evt.points[0];
    st.selectedIndex = point.customdata;
    renderPointDetail(pane, state, st.selectedIndex);
  });

  if (st.selectedIndex !== null) {
    renderPointDetail(pane, state, st.selectedIndex);
  }
}

function renderPointDetail(pane, state, index) {
  const existing = pane.querySelector(".point-detail");
  if (existing) existing.remove();

  const row = state.rankedImages[index];
  const wrap = document.createElement("div");
  wrap.className = "point-detail";

  const info = document.createElement("div");
  info.innerHTML = `
    <div class="metric-label">Selected Score</div>
    <div class="metric-value">${row.Score.toFixed(2)}</div>
    <div><strong>Label:</strong> ${row.Label}</div>
    <div><strong>Date:</strong> ${new Date(row.dt_local).toLocaleString()}</div>
  `;

  const images = document.createElement("div");
  images.className = "images";

  const rankedFig = document.createElement("figure");
  rankedFig.innerHTML = `<img src="${row["Ranked Image"]}" loading="lazy" /><figcaption>Ranked Image (with analysis)</figcaption>`;
  images.appendChild(rankedFig);

  const rawFig = document.createElement("figure");
  if (row["Raw Image"]) {
    rawFig.innerHTML = `<img src="${row["Raw Image"]}" loading="lazy" /><figcaption>Original Image</figcaption>`;
  } else {
    rawFig.innerHTML = `<div class="empty">No original image available</div>`;
  }
  images.appendChild(rawFig);

  wrap.append(info, images);
  pane.appendChild(wrap);
}

function renderDataTab(pane, rows) {
  const sorted = [...rows].sort((a, b) => new Date(b.dt_local) - new Date(a.dt_local));

  const table = document.createElement("table");
  table.innerHTML = `
    <thead>
      <tr><th>dt_local</th><th>Date</th><th>Time</th><th>Score</th><th>Label</th></tr>
    </thead>
    <tbody>
      ${sorted
        .map(
          (r) => `<tr>
            <td>${new Date(r.dt_local).toLocaleString()}</td>
            <td>${r.Date}</td>
            <td>${r.Time}</td>
            <td>${r.Score.toFixed(2)}</td>
            <td>${r.Label}</td>
          </tr>`
        )
        .join("")}
    </tbody>
  `;
  pane.appendChild(table);
}

function renderSummary(container, rows) {
  const scores = rows.map((r) => r.Score);
  const avg = scores.reduce((a, b) => a + b, 0) / scores.length;
  const max = Math.max(...scores);
  const min = Math.min(...scores);

  const heading = document.createElement("h4");
  heading.textContent = "Summary Statistics";
  container.appendChild(heading);

  const statsRow = document.createElement("div");
  statsRow.className = "stats-row";
  statsRow.append(
    stat("Average Score", avg.toFixed(1)),
    stat("Highest Score", max.toFixed(1)),
    stat("Lowest Score", min.toFixed(1)),
    stat("Total Images", rows.length)
  );
  container.appendChild(statsRow);
}

function stat(label, value) {
  const el = document.createElement("div");
  el.className = "stat";
  el.innerHTML = `<span class="metric-label">${label}</span><span class="metric-value">${value}</span>`;
  return el;
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
