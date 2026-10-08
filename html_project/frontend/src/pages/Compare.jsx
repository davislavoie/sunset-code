// Two sunsets side by side, any camera and any day: /compare?a=camera:date&b=camera:date

import { Link, useSearchParams } from "react-router";
import { sunsetPath, useCameraData, useDocumentTitle } from "../api.js";
import Dropdown from "../Dropdown.jsx";
import { SIZES } from "../Img.jsx";
import { Zoomable } from "../lightbox.jsx";
import { PageSkeleton, Skeleton } from "../Skeleton.jsx";
import ScoreBreakdown from "../ScoreBreakdown.jsx";

const parseSide = (value) => {
  const [camera, date] = (value || "").split(":");
  return { camera: camera || null, date: date || null };
};

export default function Compare({ cameras, defaultCamera }) {
  const [params, setParams] = useSearchParams();
  useDocumentTitle("Compare sunsets");

  const a = parseSide(params.get("a"));
  const b = parseSide(params.get("b"));
  a.camera ??= defaultCamera;
  b.camera ??= a.camera;

  const left = useCameraData(a.camera);
  const right = useCameraData(b.camera);

  // Defaults: left = latest sunset, right = that camera's best-ever sunset (other than the left one).
  const leftEntry = pick(left.data, a.date, (rows) => rows.at(-1));
  const rightEntry = pick(right.data, b.date, (rows) => {
    const pool = b.camera === a.camera ? rows.filter((r) => r.Date !== leftEntry?.Date) : rows;
    return pool.length ? pool.reduce((best, r) => (r.Score > best.Score ? r : best)) : null;
  });

  const setSide = (key, camera, date) =>
    setParams(
      (p) => {
        p.set(key, date ? `${camera}:${date}` : camera);
        return p;
      },
      { replace: true },
    );

  const winner =
    leftEntry && rightEntry && leftEntry.Score !== rightEntry.Score
      ? leftEntry.Score > rightEntry.Score
        ? "a"
        : "b"
      : null;

  if (!a.camera) return <PageSkeleton />;

  return (
    <>
      <h2>Compare Sunsets</h2>
      <p>Pick any two days, from any camera.</p>
      <div className="compare-grid">
        <ComparePane
          cameras={cameras}
          camera={a.camera}
          state={left}
          entry={leftEntry}
          isWinner={winner === "a"}
          onChange={(camera, date) => setSide("a", camera, date)}
        />
        <ComparePane
          cameras={cameras}
          camera={b.camera}
          state={right}
          entry={rightEntry}
          isWinner={winner === "b"}
          onChange={(camera, date) => setSide("b", camera, date)}
        />
      </div>
      {leftEntry && rightEntry && (
        <p className="compare-summary">
          {winner
            ? `Difference: ${Math.abs(leftEntry.Score - rightEntry.Score).toFixed(1)} points`
            : "It's a tie."}
        </p>
      )}
    </>
  );
}

/** The ranked entry for `date`, or `fallback(rows sorted by date)` when no date is chosen. */
function pick(data, date, fallback) {
  if (!data?.ranked_images.length) return null;
  const rows = [...data.ranked_images].sort((x, y) => (x.Date < y.Date ? -1 : 1));
  return date ? rows.find((r) => r.Date === date) ?? null : fallback(rows);
}

function ComparePane({ cameras, camera, state, entry, isWinner, onChange }) {
  const dates = state.data ? state.data.ranked_images.map((r) => r.Date).sort().reverse() : [];

  return (
    <div className={`compare-pane${isWinner ? " winner" : ""}`}>
      <div className="compare-pickers">
        <Dropdown label="Camera" options={cameras} value={camera} onChange={(cam) => onChange(cam, null)} />
        <Dropdown
          label="Day"
          placeholder="Pick a day…"
          options={dates}
          value={entry?.Date ?? null}
          onChange={(d) => onChange(camera, d)}
        />
      </div>

      {state.error && <div className="status-error">{state.error}</div>}
      {!state.data && !state.error && <Skeleton className="skeleton-photo" />}
      {state.data && !entry && <div className="empty">No sunset captured for that day.</div>}
      {entry && (
        <>
          {isWinner && <div className="compare-badge">Winner</div>}
          <Zoomable
            className="compare-img"
            src={entry["Raw Image"] || entry["Ranked Image"]}
            alt={`${camera} sunset on ${entry.Date}`}
            {...SIZES.photo}
          />
          <div className="compare-score">
            <span className="sunset-score">{entry.Score.toFixed(1)}%</span>
            <Link to={sunsetPath(camera, entry.Date)}>Sunset page →</Link>
          </div>
          {entry["Raw Image"] && <ScoreBreakdown imageUrl={entry["Raw Image"]} />}
        </>
      )}
    </div>
  );
}
