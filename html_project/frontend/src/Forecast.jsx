// The sunset forecast next to what actually happened: a table per day (Day view) and a
// compact metric (Ranked images). See forecast.js for how "actual" and accuracy are worked out.

import { useMemo } from "react";
import { captureName } from "./DayDetail.jsx";
import { CALL_TONE, VERDICT_TONE, accuracy, actualPct, callFor, dailyBests, horizonOf, summary } from "./forecast.js";
import Tip from "./Tip.jsx";

const Bubble = ({ tone, children }) => (
  <span className={`bubble ${tone}`} style={{ textTransform: "capitalize" }}>
    {children}
  </span>
);

const pctText = (pct) => `top ${Math.max(1, Math.round(100 - pct))}%`;

export function ForecastCard({ date, dayImages, allData, event = "sunset" }) {
  const bests = useMemo(() => dailyBests(allData), [allData]);
  const totals = useMemo(() => summary(allData), [allData]);
  const shots = dayImages.filter((img) => horizonOf(img.Label) && img.Forecast);
  if (!shots.length) return null;
  const actual = actualPct(bests, date);

  return (
    <div className="detail forecast-card">
      <div className="detail-title">
        <h3>Forecast</h3>
        <span>
          {bests[date] == null
            ? "No sunset-window shots yet"
            : `Day's best ${bests[date].toFixed(1)}%${actual == null ? "" : ` · ${pctText(actual)} of days · ${callFor(actual)}`}`}
        </span>
      </div>
      <table className="info-table forecast-table">
        <thead>
          <tr>
            <th>Shot</th>
            <th>Shot score</th>
            <th>Predicted best</th>
            <th>Call</th>
            <th>Accuracy</th>
          </tr>
        </thead>
        <tbody>
          {shots.map((img) => {
            const f = img.Forecast;
            const acc = accuracy(f.pct, actual);
            return (
              <tr key={img.Image}>
                <td>{captureName(img.Label, event)}</td>
                <td>{`${img.Score.toFixed(1)}%`}</td>
                <td>
                  {f.score != null && `${f.score.toFixed(1)}% · `}
                  <span className="muted">{pctText(f.pct)}</span>
                </td>
                <td>
                  <Bubble tone={CALL_TONE[f.call] ?? ""}>{f.call}</Bubble>
                </td>
                <td>
                  {acc ? (
                    <Tip label={`Predicted ${pctText(f.pct)}, actual ${pctText(actual)}`}>
                      <span className="forecast-acc">
                        <Bubble tone={VERDICT_TONE[acc.verdict]}>{acc.verdict}</Bubble>
                        <span className="muted">{`${acc.points} pts off`}</span>
                      </span>
                    </Tip>
                  ) : (
                    <span className="muted">Waiting for sunset</span>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      <ForecastSummary totals={totals} event={event} />
    </div>
  );
}

function ForecastSummary({ totals, event }) {
  const rows = Object.entries(totals).sort(([a], [b]) => (a < b ? -1 : 1));
  if (!rows.length) return null;
  return (
    <div className="forecast-summary">
      <span className="metric-label">All days</span>
      {rows.map(([h, s]) => (
        <span key={h}>
          {`${captureName(h, event)}: ${Math.round((100 * s.Hit) / s.days)}% hit, ${Math.round(
            (100 * (s.Hit + s.Close)) / s.days,
          )}% hit or close`}
          <span className="muted">{` (${s.days} days)`}</span>
        </span>
      ))}
    </div>
  );
}

/** Compact "1 hr before" forecast + accuracy for a ranked day. */
export function ForecastMetric({ date, allData }) {
  const bests = useMemo(() => dailyBests(allData), [allData]);
  const shot = allData.find((r) => r.Date === date && horizonOf(r.Label) === "02_1h_pre" && r.Forecast);
  if (!shot) return null;
  const acc = accuracy(shot.Forecast.pct, actualPct(bests, date));
  return (
    <div className="ranking-score">
      <div className="metric-label">1 hr forecast</div>
      <div className="forecast-metric">
        {shot.Forecast.score != null && <span className="ranking-score-value">{`${shot.Forecast.score.toFixed(1)}%`}</span>}
        <Bubble tone={CALL_TONE[shot.Forecast.call] ?? ""}>{shot.Forecast.call}</Bubble>
        {acc && <Bubble tone={VERDICT_TONE[acc.verdict]}>{acc.verdict}</Bubble>}
      </div>
    </div>
  );
}
