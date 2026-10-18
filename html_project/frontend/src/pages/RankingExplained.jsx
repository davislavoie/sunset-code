// How sunset ranking works. Every number comes from /api/scoring-config, which serves
// sunset_code/helpers/hsv_score.json: the same file sunset_process.py scores with.

import { useEffect, useState } from "react";
import { fetchScoringConfig } from "../api.js";

const COLOR_ROWS = [
  { color: "red", label: "Red", swatch: "hsl(0, 70%, 50%)", why: "Deep reds indicate intense light scattering, typically seen at peak sunset moments." },
  { color: "orange", label: "Orange", swatch: "hsl(20, 70%, 50%)", why: "Common in good sunsets but less dramatic than reds." },
  { color: "yellow", label: "Yellow", swatch: "hsl(30, 70%, 50%)", why: "Often present but can indicate earlier/later timing or less atmospheric drama." },
  { color: "pink", label: "Pink/Purple", swatch: "hsl(300, 70%, 50%)", why: "Rare and visually striking. Only counted when bright: dim mauve dusk cloud isn't a pink sunset." },
];

export default function RankingExplained() {
  const [config, setConfig] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchScoringConfig().then(setConfig, (e) => setError(e.message));
  }, []);

  if (error) return <div className="status-error">{error}</div>;
  if (!config) return <div className="skeleton" style={{ height: 400 }} />;
  const { bands, power, divisor, contrast: c, soft_cap: cap, min_brightness: minV } = config;

  return (
    <>
      <h1>How sunset ranking works</h1>
      <p>Each sunset image is scored from 0-100 based on the colors detected in the sky portion of the image.</p>
      <hr />

      <section>
        <h3>Color detection &amp; multipliers</h3>
        <p>
          The algorithm analyzes the <strong>sky</strong> of each image (the top half, or above the horizon on cameras where it sits higher) and identifies pixels in
          specific hue ranges (OpenCV scale: hue 0-179, saturation and brightness 0-255). Pixels darker than {minV} are
          ignored: their color is noise.
        </p>
        <table className="info-table multiplier-table">
          <thead>
            <tr>
              <th>Color</th>
              <th>Hue</th>
              <th>Min saturation</th>
              <th>Min brightness</th>
              <th>Multiplier</th>
            </tr>
          </thead>
          <tbody>
            {COLOR_ROWS.map(({ color, label, swatch }) => (
              <tr key={color}>
                <td>
                  <span className="color-swatch" style={{ background: swatch }} /> {label}
                </td>
                <td>{`${bands[color].hue[0]}-${bands[color].hue[1]}`}</td>
                <td>{bands[color].sat_min}</td>
                <td>{bands[color].val_min}</td>
                <td>{bands[color].weight}x</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section>
        <h3>Score calculation</h3>
        <p>For each color:</p>
        <div className="formula-box">
          <code>
            points = pixel_ratio × avg_saturation^{power} ÷ {divisor} × multiplier
          </code>
        </div>
        <ul>
          <li><strong>pixel_ratio</strong> = matching pixels / total pixels in image</li>
          <li><strong>avg_saturation</strong> = average saturation (0-255) of matching pixels</li>
        </ul>
        <p>
          The four colors' points are added up and multiplied by the <strong>cloud contrast</strong> factor:
        </p>
        <div className="formula-box">
          <code>
            ({c.hue_base} + {c.hue_slope} × hue spread) × ({c.lit_base} + {c.lit_slope} × lit contrast)
          </code>
        </div>
        <ul>
          <li><strong>hue spread</strong>: how many different hues the colored pixels cover (orange and pink together scores higher than one flat color)</li>
          <li><strong>lit contrast</strong>: how much brighter the colored pixels are than the rest of the sky (lit cloud against dark cloud)</li>
        </ul>
        <p>Then it is soft-capped, so big days spread out instead of all tying at 100:</p>
        <div className="formula-box">
          <code>score = 100 × (1 − e^(−total / {cap}))</code>
        </div>
        <p>
          A day&apos;s best shot is its highest score (plus the glass-lake bonus), leaving out thumbed-down shots
          (and shots with the same view as one); a thumbs up wins outright.
        </p>
        <p>
          The up and down arrows beside each day on Ranked images give feedback that the image is ranked too low (up)
          or too high (down). Anyone can vote without logging in. Votes don&apos;t change the score; they show where
          the color score is off, to guide tuning it.
        </p>
      </section>

      <hr />

      <section>
        <h3>Why these multipliers?</h3>
        <table className="info-table">
          <tbody>
            {[...COLOR_ROWS].sort((a, b) => bands[b.color].weight - bands[a.color].weight).map(({ color, label, why }) => (
              <tr key={color}>
                <td><strong>{`${label} (${bands[color].weight}x)`}</strong></td>
                <td>{why}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </>
  );
}
