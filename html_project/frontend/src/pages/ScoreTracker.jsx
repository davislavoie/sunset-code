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
import Img, { SIZES } from "../Img.jsx";

const SCORE_TICKS = [0, 20, 40, 60, 80, 100];

export default function ScoreTracker({ data }) {
  const rows = data.ranked_images;
  const [tab, setTab] = useState("chart");
  const [selected, setSelected] = useState(null);
  // "color" = the HSV score from sunset_process.py; "ai" = the optional local AI judge's score.
  const [metric, setMetric] = useState("color");

  const points = useMemo(
    () =>
      rows
        .map((row) => ({ date: new Date(row.dt_local), score: row.Score, ai: aiScore(row), row }))
        .sort((a, b) => a.date - b.date),
    [rows],
  );
  const hasAi = points.some((p) => p.ai != null);
  const showAi = metric === "ai" && hasAi;
  // One line at a time: AI scores only exist for judged days, and bklit would draw gaps as zeros.
  const chartData = useMemo(
    () => (showAi ? points.filter((p) => p.ai != null) : points).map((p) => ({ ...p, value: showAi ? p.ai : p.score })),
    [points, showAi],
  );

  const xTicks = useMemo(() => (points.length ? monthTicks(points[0].date, points.at(-1).date) : {}), [points]);

  const header = (
    <>
      <h2>Score Tracker</h2>
      <p>Track and visualize sunset scores over time</p>
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
        {[["chart", "Line Chart"], ["data", "Data"]].map(([key, name]) => (
          <button key={key} className={`tab-btn${tab === key ? " active" : ""}`} onClick={() => setTab(key)}>
            {name}
          </button>
        ))}
      </div>

      <div>
        {tab === "chart" ? (
          <>
            {hasAi && (
              <div className="rank-chips metric-toggle" role="group" aria-label="Score shown">
                {[["color", "Color score"], ["ai", "AI score"]].map(([key, label]) => (
                  <button key={key} className={`rank-chip${metric === key ? " active" : ""}`} aria-pressed={metric === key} onClick={() => setMetric(key)}>
                    {label}
                  </button>
                ))}
              </div>
            )}
            <p className="chart-hint">
              Click a point to see that day's images.
              {showAi && ` Showing the ${chartData.length} days the AI has judged.`}
            </p>
            <div className="score-chart">
              <LineChart key={metric} data={chartData} aspectRatio="" className="h-full" margin={{ left: 40, right: 16 }} yDomain={[0, 100]}>
                <Grid {...GRID_STYLE} horizontal rowTickValues={SCORE_TICKS} vertical numTicksColumns={12} />
                {/* Straight segments between days (no smoothing) with every day drawn as a point */}
                <Line
                  dataKey="value"
                  stroke={showAi ? "var(--chart-4)" : "var(--chart-2)"}
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
                    ...(point.row.AI
                      ? [{ color: "var(--chart-4)", label: "AI score", value: point.row.AI.is_sunset ? `${point.ai}` : `${point.ai ?? 0} (ruled out)` }]
                      : []),
                    { color: "var(--chart-3)", label: "Best shot", value: point.row.Time },
                  ]}
                />
                <SelectOnClick onSelect={(point) => setSelected(point.row)} />
              </LineChart>
            </div>
            {selected && <PointDetail row={selected} />}
          </>
        ) : (
          <DataTable rows={rows} />
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

function PointDetail({ row }) {
  return (
    <div className="point-detail">
      <div>
        <div className="metric-label">Selected Score</div>
        <div className="metric-value">{row.Score.toFixed(2)}</div>
        <div><strong>Label:</strong> {row.Label}</div>
        <div><strong>Date:</strong> {new Date(row.dt_local).toLocaleString()}</div>
      </div>
      <div className="images">
        <figure>
          <Img src={row["Ranked Image"]} alt="" loading="lazy" {...SIZES.ranked} />
          <figcaption>Ranked Image (with analysis)</figcaption>
        </figure>
        <figure>
          {row["Raw Image"] ? (
            <>
              <Img src={row["Raw Image"]} alt="" loading="lazy" {...SIZES.photo} />
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

function DataTable({ rows }) {
  const sorted = [...rows].sort((a, b) => new Date(b.dt_local) - new Date(a.dt_local));
  return (
    <table>
      <thead>
        <tr>
          <th>dt_local</th>
          <th>Date</th>
          <th>Time</th>
          <th>Score</th>
          <th>Label</th>
        </tr>
      </thead>
      <tbody>
        {sorted.map((r) => (
          <tr key={r["Ranked Image"]}>
            <td>{new Date(r.dt_local).toLocaleString()}</td>
            <td>{r.Date}</td>
            <td>{r.Time}</td>
            <td>{r.Score.toFixed(2)}</td>
            <td>{r.Label}</td>
          </tr>
        ))}
      </tbody>
    </table>
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

/** The AI judge's sky-only score for a ranked day, or null if not judged. */
function aiScore(row) {
  return row.AI ? row.AI.score : null;
}
