// Per-color contribution bars for one capture: the breakdown sunset_process.py stored with its score
// (points per color, coverage, saturation, cloud contrast). Nothing is computed in the browser.

import { COLORS } from "./scoring.js";

export const COLOR_META = {
  red: { label: "Red", swatch: "hsl(0, 70%, 50%)" },
  orange: { label: "Orange", swatch: "hsl(20, 80%, 50%)" },
  yellow: { label: "Yellow", swatch: "hsl(45, 85%, 55%)" },
  pink: { label: "Pink/Purple", swatch: "hsl(300, 60%, 55%)" },
};

/** breakdown: the capture's Breakdown from /api/data (null if it was scored before breakdowns were stored). */
export default function ScoreBreakdown({ breakdown, score }) {
  return (
    <div className="score-breakdown-bars">
      <div className="metric-label">Color breakdown</div>
      {!breakdown && <div className="breakdown-detail">Scored before breakdowns were stored; shows after a rescore.</div>}
      {breakdown && COLORS.map((color) => {
        const coverage = breakdown[`${color}_coverage`] ?? 0;
        return (
          <div key={color} className="breakdown-row">
            <div className="breakdown-head">
              <span className="breakdown-label">
                <i style={{ background: COLOR_META[color].swatch }} /> {COLOR_META[color].label}
              </span>
              <span className="breakdown-value">{`${(breakdown[`${color}_points`] ?? 0).toFixed(1)} pts`}</span>
            </div>
            <div className="breakdown-track">
              <div
                className="breakdown-fill"
                // Coverage of the sky: it's half the frame, so 50% of the image fills the bar.
                // scaleX rather than width so the grow animation stays on the compositor.
                style={{ transform: `scaleX(${Math.min(1, coverage / 0.5)})`, background: COLOR_META[color].swatch }}
              />
            </div>
            <div className="breakdown-detail">
              {`${(coverage * 100).toFixed(2)}% of image · avg saturation ${Math.round(breakdown[`${color}_saturation`] ?? 0)}`}
            </div>
          </div>
        );
      })}
      {breakdown && (
        <div className="breakdown-total">
          Score = Σ points × cloud contrast {breakdown.contrast.toFixed(2)}, soft-capped = <strong>{score.toFixed(1)}</strong>
        </div>
      )}
    </div>
  );
}
