// Score Tracker: best score per day over time (bklit line chart). Hover for
// details; click a day to see its ranked and original images.

import { useEffect, useMemo, useRef, useState } from "react";
import { curveLinear } from "@visx/curve";
import { useChartHover, useChartStable } from "@/components/charts/chart-context";
import { Grid } from "@/components/charts/grid";
import { Line, LineChart } from "@/components/charts/line-chart";
import { ChartTooltip } from "@/components/charts/tooltip";
import { XAxis } from "@/components/charts/x-axis";
import { YAxis } from "@/components/charts/y-axis";
import { GRID_STYLE, INSTANT_TOOLTIP, monthTicks } from "../chartTheme.js";
import { thumb } from "../api.js";
import { toCsv } from "../csv.js";
import { captureName } from "../DayDetail.jsx";
import { horizonOf } from "../forecast.js";
import Img, { SIZES } from "../Img.jsx";
import ScoreOverlay from "../ScoreOverlay.jsx";
import ScoreHistogram from "./ScoreHistogram.jsx";
import ScoreScatter from "./ScoreScatter.jsx";

const SCORE_TICKS = [0, 20, 40, 60, 80, 100];

export default function ScoreTracker({ data, camera }) {
  const rows = data.ranked_images;
  const [tab, setTab] = useState("chart");
  const [selected, setSelected] = useState(null);
  const points = useMemo(
    () =>
      rows
        .map((row) => ({ date: new Date(row.dt_local), score: row.Score, value: row.Score, row }))
        .sort((a, b) => a.date - b.date),
    [rows],
  );

  const xTicks = useMemo(() => (points.length ? monthTicks(points[0].date, points.at(-1).date) : {}), [points]);

  const header = (
    <>
      <h1>Score tracker</h1>
      <p>Sunset scores over time, and against everything logged with them</p>
    </>
  );

  if (!rows.length) {
    return (
      <>
        {header}
        <div className="empty">No data available.</div>
      </>
    );
  }

  const scores = rows.map((r) => r.Score);

  return (
    <>
      {header}

      <div className="tabs">
        {[["chart", "Over time"], ["dist", "Distribution"], ["compare", "Compare"], ["data", "Data"]].map(([key, name]) => (
          <button key={key} className={`tab-btn${tab === key ? " active" : ""}`} onClick={() => setTab(key)}>
            {name}
          </button>
        ))}
      </div>

      <div>
        {tab === "dist" ? (
          <ScoreHistogram rows={rows} />
        ) : tab === "compare" ? (
          <>
            <ScoreScatter rows={rows} onSelect={setSelected} />
            {selected && <PointDetail row={selected} camera={camera} />}
          </>
        ) : tab === "chart" ? (
          <>
            <p className="chart-hint">Click a point to see that day's images.</p>
            <div className="score-chart">
              <LineChart data={points} aspectRatio="" className="h-full" margin={{ left: 40, right: 16 }} yDomain={[0, 100]}>
                <Grid {...GRID_STYLE} horizontal rowTickValues={SCORE_TICKS} vertical numTicksColumns={12} />
                {/* Straight segments between days (no smoothing) with every day drawn as a point */}
                <Line
                  dataKey="value"
                  stroke="var(--chart-2)"
                  strokeWidth={1.5}
                  curve={curveLinear}
                  showMarkers
                  markers={{ radius: 2.5, strokeWidth: 0, ringGap: 0, fadeOnHover: false }}
                />
                <YAxis tickValues={SCORE_TICKS} formatValue={(v) => `${v}`} />
                <XAxis {...xTicks} />
                <ChartTooltip
                  {...INSTANT_TOOLTIP}
                  rows={(point) => [
                    { color: "var(--chart-2)", label: "Color score", value: `${point.score.toFixed(1)}%` },
                    { color: "var(--chart-3)", label: "Best shot", value: point.row.Time },
                  ]}
                />
                <SelectOnClick onSelect={(point) => setSelected(point.row)} />
              </LineChart>
            </div>
            {selected && <PointDetail row={selected} camera={camera} />}
          </>
        ) : (
          <DataTable rows={rows} allData={data.all_data} camera={camera} />
        )}
      </div>

      <h4>Summary Statistics</h4>
      <div className="stats-row">
        <Stat label="Average Score" value={(scores.reduce((a, b) => a + b, 0) / scores.length).toFixed(1)} />
        <Stat label="Highest Score" value={Math.max(...scores).toFixed(1)} />
        <Stat label="Lowest Score" value={Math.min(...scores).toFixed(1)} />
        <Stat label="Total Images" value={rows.length} />
      </div>
    </>
  );
}

/**
 * Renders nothing; reports the hovered point when the chart is clicked (bklit has no click prop).
 * bklit's own mousedown starts a drag-select and clears the hovered point, so a plain "click"
 * listener always sees nothing. Read it on pointerdown instead, which fires first. For touch
 * there's no hover, the tap itself sets the point, so read it on pointerup.
 */
function SelectOnClick({ onSelect }) {
  const { tooltipData } = useChartHover();
  const { containerRef } = useChartStable();
  const latest = useRef({ tooltipData, onSelect });
  latest.current = { tooltipData, onSelect };

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const select = (e, phase) => {
      const isMouse = e.pointerType === "mouse";
      if ((phase === "down") !== isMouse) return;
      const { tooltipData: hovered, onSelect: report } = latest.current;
      if (hovered) report(hovered.point);
    };
    const onDown = (e) => select(e, "down");
    const onUp = (e) => select(e, "up");
    el.addEventListener("pointerdown", onDown, true);
    el.addEventListener("pointerup", onUp, true);
    return () => {
      el.removeEventListener("pointerdown", onDown, true);
      el.removeEventListener("pointerup", onUp, true);
    };
  }, [containerRef]);

  return null;
}

function PointDetail({ row, camera }) {
  return (
    <div className="point-detail">
      <div>
        <div className="metric-label">Selected Score</div>
        <div className="metric-value">{row.Score.toFixed(2)}</div>
        <div><strong>Label:</strong> {row.Label}</div>
        <div><strong>Date:</strong> {new Date(row.dt_local).toLocaleString()}</div>
      </div>
      <div className="images">
        <ScoreOverlay imageUrl={row["Raw Image"]} camera={camera} />
        <figure>
          {row["Raw Image"] ? (
            <>
              <Img src={row["Raw Image"]} placeholder={thumb(row["Raw Image"])} alt="" loading="lazy" {...SIZES.photo} />
              <figcaption>Original Image</figcaption>
            </>
          ) : (
            <div className="empty">No original image available</div>
          )}
        </figure>
      </div>
    </div>
  );
}

const num = (v, digits = 0) => (v == null ? null : +v.toFixed(digits));

// The Data tab and its CSV: one row per day (the best shot) with what was logged at that shot.
// Each column is [heading, (row, { forecast, event }) => value]; forecast is the day's 1 hr-before one.
const COLUMNS = [
  ["Date", (r) => r.Date],
  ["Time", (r) => r.Time],
  ["Best shot", (r, c) => captureName(r.Label, c.event)],
  ["Score", (r) => num(r.Score, 1)],
  ["Color score", (r) => num(r["HSV Score"], 1)],
  ["Glass bonus", (r) => r.Glass?.bonus],
  ["Zoom offset", (r) => r.Zoom || null],
  ["Flagged", (r) => r.Excluded],
  ["1 hr forecast", (r, c) => num(c.forecast?.score, 1)],
  ["Forecast call", (r, c) => c.forecast?.call],
  ["Temp (°F)", (r) => num(r.Weather?.temperature_2m)],
  ["Humidity (%)", (r) => num(r.Weather?.relative_humidity_2m)],
  ["Dew point (°F)", (r) => num(r.Weather?.dew_point_2m)],
  ["Chance of rain (%)", (r) => num(r.Weather?.precipitation_probability)],
  ["Precipitation (mm)", (r) => num(r.Weather?.precipitation, 1)],
  ["Wind (mph)", (r) => num(r.Weather?.obs_wind_mph ?? r.Weather?.wind_speed_10m)],
  ["Gust (mph)", (r) => num(r.Weather?.obs_station ? r.Weather.obs_gust_mph : r.Weather?.wind_gusts_10m)],
  ["Cloud low (%)", (r) => num(r.Weather?.cloud_cover_low)],
  ["Cloud mid (%)", (r) => num(r.Weather?.cloud_cover_mid)],
  ["Cloud high (%)", (r) => num(r.Weather?.cloud_cover_high)],
  ["Cloud total (%)", (r) => num(r.Weather?.cloud_cover_total)],
  ["Satellite cloud overhead (%)", (r) => num(r.Weather?.goes_over != null ? 100 * r.Weather.goes_over : null)],
  ["Satellite cloud 3-25 mi (%)", (r) => num(r.Weather?.goes_near != null ? 100 * r.Weather.goes_near : null)],
  ["Satellite cloud 50-190 mi (%)", (r) => num(r.Weather?.goes_far != null ? 100 * r.Weather.goes_far : null)],
  ["Airport sky", (r) => r.Weather?.obs_sky],
  ["Airport weather", (r) => r.Weather?.obs_wx],
];

function download(name, text) {
  const url = URL.createObjectURL(new Blob([text], { type: "text/csv" }));
  Object.assign(document.createElement("a"), { href: url, download: name }).click();
  URL.revokeObjectURL(url);
}

function DataTable({ rows, allData, camera }) {
  const dates = useMemo(() => rows.map((r) => r.Date).sort(), [rows]);
  const [start, setStart] = useState(dates[0]);
  const [end, setEnd] = useState(dates.at(-1));
  const context = useMemo(() => {
    const forecasts = new Map(allData.filter((r) => horizonOf(r.Label) === "02_1h_pre" && r.Forecast).map((r) => [r.Date, r.Forecast]));
    const event = allData.some((r) => /^\d+_sunrise/.test(r.Label)) ? "sunrise" : "sunset";
    return (r) => ({ forecast: forecasts.get(r.Date), event });
  }, [allData]);

  // An emptied date box means no limit on that side.
  const lines = rows
    .filter((r) => (!start || r.Date >= start) && (!end || r.Date <= end))
    .sort((a, b) => (a.Date < b.Date ? 1 : -1))
    .map((r) => COLUMNS.map(([, value]) => value(r, context(r)) ?? null));
  const headings = COLUMNS.map(([heading]) => heading);

  return (
    <>
      <div className="data-controls">
        <label>
          Start date
          <input type="date" value={start} min={dates[0]} max={end || dates.at(-1)} onChange={(e) => setStart(e.target.value)} />
        </label>
        <label>
          End date
          <input type="date" value={end} min={start || dates[0]} max={dates.at(-1)} onChange={(e) => setEnd(e.target.value)} />
        </label>
        <button
          className="btn btn-primary"
          disabled={!lines.length}
          onClick={() => download(`${camera}_${start || dates[0]}_to_${end || dates.at(-1)}.csv`, toCsv([headings, ...lines]))}
        >
          Download CSV
        </button>
        <span className="muted">{`${lines.length} ${lines.length === 1 ? "day" : "days"}`}</span>
      </div>
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              {headings.map((h) => (
                <th key={h}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {lines.map((line) => (
              <tr key={line[0]}>
                {line.map((v, i) => (
                  <td key={headings[i]}>{v}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}

function Stat({ label, value }) {
  return (
    <div className="stat">
      <span className="metric-label">{label}</span>
      <span className="metric-value">{value}</span>
    </div>
  );
}
