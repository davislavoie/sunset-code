// Per-color contribution bars for one image, computed in the browser with the
// same scorer as Ranking Explained (saved multipliers, default hue ranges).

import { useEffect, useState } from "react";
import { fetchScoringConfig, proxied } from "./api.js";
import { loadImageData } from "./hsv.js";
import { COLORS, DEFAULT_COLOR_RANGES, DEFAULT_FORMULA, scoreImage } from "./scoring.js";

// sunset_process.py's multipliers at the time of writing; used only if /api/scoring-config fails.
const DEFAULT_MULTIPLIERS = { red: 4, orange: 3, yellow: 2, pink: 9 };

const COLOR_META = {
  red: { label: "Red", swatch: "hsl(0, 70%, 50%)" },
  orange: { label: "Orange", swatch: "hsl(20, 80%, 50%)" },
  yellow: { label: "Yellow", swatch: "hsl(45, 85%, 55%)" },
  pink: { label: "Pink/Purple", swatch: "hsl(300, 60%, 55%)" },
};

export default function ScoreBreakdown({ imageUrl }) {
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let live = true;
    setResult(null);
    setError(null);
    // If the live multipliers can't be read, fall back to the defaults rather than showing nothing.
    Promise.all([fetchScoringConfig().catch(() => DEFAULT_MULTIPLIERS), loadImageData(proxied(imageUrl))])
      .then(([multipliers, image]) => {
        if (!live) return;
        setResult(scoreImage(image, { multipliers, colorRanges: DEFAULT_COLOR_RANGES, formulaParams: DEFAULT_FORMULA }));
      })
      .catch((e) => live && setError(e.message));
    return () => {
      live = false;
    };
  }, [imageUrl]);

  return (
    <div className="score-breakdown-bars">
      <div className="metric-label">Color breakdown</div>
      {error && <div className="status-error">{error}</div>}
      {COLORS.map((color) => {
        const points = result?.perColor[color];
        const coverage = result?.coverage[color] ?? 0;
        return (
          <div key={color} className="breakdown-row">
            <div className="breakdown-head">
              <span className="breakdown-label">
                <i style={{ background: COLOR_META[color].swatch }} /> {COLOR_META[color].label}
              </span>
              <span className="breakdown-value">{points == null ? "…" : `${points.toFixed(1)} pts`}</span>
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
              {result
                ? `${(coverage * 100).toFixed(2)}% of image · avg saturation ${Math.round(result.avgSaturation[color])}`
                : " " /* keeps the row height while loading */}
            </div>
          </div>
        );
      })}
      {result && (
        <div className="breakdown-total">
          Score = Σ coverage × saturation² ÷ 40 × multiplier = <strong>{result.total.toFixed(1)}</strong>
          {result.total >= 100 && " (capped at 100)"}
        </div>
      )}
    </div>
  );
}
