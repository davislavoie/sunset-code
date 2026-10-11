// Score tracker's "Compare" tab: any logged value against any other, one point per ranked
// day, with a least-squares trend line and Pearson r, to look for what goes with a good sunset.

import { useMemo, useState } from "react";
import { scaleLinear } from "@visx/scale";
import { ParentSize } from "@visx/responsive";
import Dropdown from "../Dropdown.jsx";

const fmtDate = (ms) => new Date(ms).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "2-digit" });
const fmtHour = (h) => new Date(2000, 0, 1, Math.floor(h), Math.round((h % 1) * 60)).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
const weather = (key) => (r) => r.Weather?.[key];

/** Minutes from sunset (or sunrise) of the best shot, from labels like "05_15m_pre" / "07_sunset". */
function shotOffset(row) {
  const m = /_(\d+)(h|m)_(pre|post)/.exec(row.Label || "");
  if (m) return Number(m[1]) * (m[2] === "h" ? 60 : 1) * (m[3] === "pre" ? -1 : 1);
  return /_(sunset|sunrise)/.test(row.Label || "") ? 0 : null;
}

const CLOUD_FIELDS = [["", "overhead"], ["path13_", "8 mi toward sun"], ["path40_", "25 mi toward sun"], ["path80_", "50 mi toward sun"]]
  .flatMap(([prefix, where]) => ["low", "mid", "high"].map((layer) => ({
    key: `${prefix}cloud_cover_${layer}`,
    label: `${layer[0].toUpperCase()}${layer.slice(1)} cloud ${where} (%)`,
    get: weather(`${prefix}cloud_cover_${layer}`),
  })));

export const FIELDS = [
  { key: "score", label: "Color score (%)", get: (r) => r.Score },
  { key: "ai", label: "AI score", get: (r) => r.AI?.score },
  { key: "date", label: "Date", get: (r) => new Date(r.dt_local).getTime(), fmt: fmtDate },
  {
    key: "doy", label: "Day of year",
    get: (r) => { const d = new Date(r.dt_local); return Math.floor((d - new Date(d.getFullYear(), 0, 0)) / 864e5); },
  },
  { key: "time", label: "Time of best shot", get: (r) => { const d = new Date(r.dt_local); return d.getHours() + d.getMinutes() / 60; }, fmt: fmtHour },
  { key: "offset", label: "Best shot vs sunset (min)", get: shotOffset },
  { key: "cloud_cover_total", label: "Total cloud overhead (%)", get: weather("cloud_cover_total") },
  ...CLOUD_FIELDS,
  { key: "temperature_2m", label: "Temperature (°F)", get: weather("temperature_2m") },
  { key: "relative_humidity_2m", label: "Humidity (%)", get: weather("relative_humidity_2m") },
  { key: "dew_point_2m", label: "Dew point (°F)", get: weather("dew_point_2m") },
  { key: "precipitation_probability", label: "Chance of rain (%)", get: weather("precipitation_probability") },
  { key: "precipitation", label: "Precipitation (mm)", get: weather("precipitation") },
  { key: "visibility", label: "Visibility (km)", get: (r) => (r.Weather?.visibility == null ? null : r.Weather.visibility / 1000) },
];
const byKey = Object.fromEntries(FIELDS.map((f) => [f.key, f]));
const fmtValue = (f, v) => (f.fmt ? f.fmt(v) : Number.isInteger(v) ? `${v}` : v.toFixed(1));

/** Pearson r and the least-squares line y = a + b·x. */
export function fit(points) {
  const n = points.length;
  if (n < 3) return null;
  const mx = points.reduce((s, p) => s + p.x, 0) / n;
  const my = points.reduce((s, p) => s + p.y, 0) / n;
  let sxy = 0, sxx = 0, syy = 0;
  for (const p of points) {
    sxy += (p.x - mx) * (p.y - my);
    sxx += (p.x - mx) ** 2;
    syy += (p.y - my) ** 2;
  }
  if (!sxx || !syy) return null;
  const b = sxy / sxx;
  return { r: sxy / Math.sqrt(sxx * syy), a: my - b * mx, b };
}

const strength = (r) => {
  const a = Math.abs(r);
  const word = a < 0.1 ? "No" : a < 0.3 ? "Weak" : a < 0.5 ? "Moderate" : "Strong";
  return a < 0.1 ? "No real relationship" : `${word} ${r > 0 ? "positive" : "negative"} relationship`;
};

const options = FIELDS.map((f) => ({ value: f.key, label: f.label }));

export default function ScoreScatter({ rows, onSelect }) {
  const [xKey, setXKey] = useState("path13_cloud_cover_low");
  const [yKey, setYKey] = useState("score");
  const xf = byKey[xKey], yf = byKey[yKey];

  const points = useMemo(
    () => rows.map((row) => ({ x: xf.get(row), y: yf.get(row), row })).filter((p) => p.x != null && p.y != null),
    [rows, xf, yf],
  );
  const line = useMemo(() => fit(points), [points]);

  return (
    <>
      <div className="scatter-controls">
        <label>
          <span className="metric-label">Y axis</span>
          <Dropdown label="Y axis" value={yKey} onChange={setYKey} options={options} />
        </label>
        <span className="scatter-vs">vs</span>
        <label>
          <span className="metric-label">X axis</span>
          <Dropdown label="X axis" value={xKey} onChange={setXKey} options={options} />
        </label>
        <div className="scatter-stat">
          {line ? (
            <>
              <strong>r = {line.r.toFixed(2)}</strong> · {strength(line.r)} · {points.length} days
            </>
          ) : (
            `${points.length} days with both values`
          )}
        </div>
      </div>
      <p className="chart-hint">
        One point per day (the day's best shot). r runs from −1 to 1; near 0 means the two don't move together.
        Click a point to see that day.
      </p>
      <div className="scatter-chart">
        <ParentSize>
          {({ width, height }) => width > 0 && (
            <Scatter {...{ width, height, points, line, xf, yf, onSelect }} />
          )}
        </ParentSize>
      </div>
    </>
  );
}

const M = { top: 12, right: 16, bottom: 36, left: 52 };

function Scatter({ width, height, points, line, xf, yf, onSelect }) {
  const [hover, setHover] = useState(null);
  const extent = (vals) => {
    if (!vals.length) return [0, 1];
    const lo = Math.min(...vals), hi = Math.max(...vals);
    return lo === hi ? [lo - 1, hi + 1] : [lo, hi];
  };
  const x = scaleLinear({ domain: extent(points.map((p) => p.x)), range: [M.left, width - M.right], nice: true });
  const y = scaleLinear({ domain: extent(points.map((p) => p.y)), range: [height - M.bottom, M.top], nice: true });
  const [x0, x1] = x.domain();

  const nearest = (e) => {
    const box = e.currentTarget.getBoundingClientRect();
    const mx = e.clientX - box.left, my = e.clientY - box.top;
    let best = null, bestD = 14 ** 2;
    for (const p of points) {
      const d = (x(p.x) - mx) ** 2 + (y(p.y) - my) ** 2;
      if (d < bestD) [best, bestD] = [p, d];
    }
    return best;
  };

  return (
    <div className="scatter-wrap">
      <svg
        width={width}
        height={height}
        onMouseMove={(e) => setHover(nearest(e))}
        onMouseLeave={() => setHover(null)}
        onClick={(e) => { const p = nearest(e); if (p) onSelect(p.row); }}
        role="img"
        aria-label={`${yf.label} against ${xf.label}`}
      >
        {y.ticks(5).map((t) => (
          <g key={`y${t}`}>
            <line className="scatter-grid" x1={M.left} x2={width - M.right} y1={y(t)} y2={y(t)} />
            <text className="scatter-tick" x={M.left - 8} y={y(t) + 4} textAnchor="end">{fmtValue(yf, t)}</text>
          </g>
        ))}
        {x.ticks(Math.max(2, Math.floor(width / 110))).map((t) => (
          <g key={`x${t}`}>
            <line className="scatter-grid" x1={x(t)} x2={x(t)} y1={M.top} y2={height - M.bottom} />
            <text className="scatter-tick" x={x(t)} y={height - M.bottom + 18} textAnchor="middle">{fmtValue(xf, t)}</text>
          </g>
        ))}
        {points.map((p, i) => (
          <circle key={i} className="scatter-dot" cx={x(p.x)} cy={y(p.y)} r={3.5} />
        ))}
        <clipPath id="scatter-plot-area">
          <rect x={M.left} y={M.top} width={width - M.left - M.right} height={height - M.top - M.bottom} />
        </clipPath>
        {line && (
          <line className="scatter-trend" clipPath="url(#scatter-plot-area)"
            x1={x(x0)} y1={y(line.a + line.b * x0)} x2={x(x1)} y2={y(line.a + line.b * x1)} />
        )}
        {hover && <circle className="scatter-dot active" cx={x(hover.x)} cy={y(hover.y)} r={6} />}
      </svg>
      {hover && (
        <div
          className="scatter-tip"
          style={{ left: Math.min(x(hover.x) + 12, width - 200), top: Math.max(0, y(hover.y) - 70) }}
        >
          <div className="scatter-tip-title">{hover.row.Date}</div>
          <div><span>{yf.label}</span> <b>{fmtValue(yf, hover.y)}</b></div>
          <div><span>{xf.label}</span> <b>{fmtValue(xf, hover.x)}</b></div>
        </div>
      )}
    </div>
  );
}
