// Score tracker's "Distribution" tab: how the daily best scores spread out, against the normal curve
// with the same mean and spread. Ideally the bars follow the curve; grey days pile up at the low end.

import { useState } from "react";
import { scaleLinear } from "@visx/scale";
import { ParentSize } from "@visx/responsive";

const BIN = 5;
const M = { top: 12, right: 16, bottom: 36, left: 44 };

/** Counts per BIN-wide bin over 0-100, plus mean, standard deviation and skew. */
export function distribution(scores) {
  const bins = Array.from({ length: 100 / BIN }, (_, i) => ({ lo: i * BIN, n: 0 }));
  for (const s of scores) bins[Math.min(bins.length - 1, Math.max(0, Math.floor(s / BIN)))].n++;
  const n = scores.length;
  const mean = scores.reduce((a, b) => a + b, 0) / n;
  const sd = Math.sqrt(scores.reduce((a, b) => a + (b - mean) ** 2, 0) / n);
  const skew = sd ? scores.reduce((a, b) => a + ((b - mean) / sd) ** 3, 0) / n : 0;
  return { bins, n, mean, sd, skew };
}

export default function ScoreHistogram({ rows }) {
  const scores = rows.filter((r) => !r.Excluded).map((r) => r.Score);
  if (!scores.length) return <div className="empty">No data available.</div>;
  const dist = distribution(scores);

  return (
    <>
      <div className="hist-legend">
        <span><i className="hist-swatch bar" /> Days</span>
        <span><i className="hist-swatch line" /> Normal curve (mean {dist.mean.toFixed(1)}, sd {dist.sd.toFixed(1)})</span>
        <span className="hist-stat">
          {dist.n} days · skew {dist.skew.toFixed(2)} {Math.abs(dist.skew) < 0.5 ? "(close to normal)" : dist.skew > 0 ? "(bunched low)" : "(bunched high)"}
        </span>
      </div>
      <p className="chart-hint">Each day's best score in {BIN}-point bins. Ruled-out days are left out, like Ranked images.</p>
      <div className="scatter-chart">
        <ParentSize>{({ width, height }) => width > 0 && <Histogram {...{ width, height, dist }} />}</ParentSize>
      </div>
    </>
  );
}

function Histogram({ width, height, dist }) {
  const [hover, setHover] = useState(null);
  const { bins, n, mean, sd } = dist;
  // Expected days per bin under the normal curve: n * bin width * density.
  const expected = (v) => (sd ? (n * BIN * Math.exp(-(((v - mean) / sd) ** 2) / 2)) / (sd * Math.sqrt(2 * Math.PI)) : 0);
  const x = scaleLinear({ domain: [0, 100], range: [M.left, width - M.right] });
  const y = scaleLinear({ domain: [0, Math.max(...bins.map((b) => b.n), expected(mean))], range: [height - M.bottom, M.top], nice: true });
  const curve = Array.from({ length: 101 }, (_, v) => `${v ? "L" : "M"}${x(v)},${y(expected(v))}`).join("");
  const w = x(BIN) - x(0);

  return (
    <div className="scatter-wrap">
      <svg width={width} height={height} role="img" aria-label="Distribution of daily best scores with a normal curve"
        onMouseLeave={() => setHover(null)}>
        {y.ticks(5).map((t) => (
          <g key={`y${t}`}>
            <line className="scatter-grid" x1={M.left} x2={width - M.right} y1={y(t)} y2={y(t)} />
            <text className="scatter-tick" x={M.left - 8} y={y(t) + 4} textAnchor="end">{t}</text>
          </g>
        ))}
        {[0, 20, 40, 60, 80, 100].map((t) => (
          <text key={`x${t}`} className="scatter-tick" x={x(t)} y={height - M.bottom + 18} textAnchor="middle">{t}</text>
        ))}
        {bins.map((b) => (
          <g key={b.lo} onMouseEnter={() => setHover(b)}>
            {/* full-height hit target, wider than the bar */}
            <rect x={x(b.lo)} y={M.top} width={w} height={height - M.top - M.bottom} fill="transparent" />
            <rect className={`hist-bar${hover === b ? " active" : ""}`} x={x(b.lo) + 1} y={y(b.n)}
              width={Math.max(0, w - 2)} height={y(0) - y(b.n)} rx={2} />
          </g>
        ))}
        <path className="hist-curve" d={curve} />
      </svg>
      {hover && (
        <div className="scatter-tip" style={{ left: Math.min(x(hover.lo) + w + 8, width - 200), top: M.top }}>
          <div className="scatter-tip-title">Score {hover.lo}–{hover.lo + BIN}</div>
          <div><span>Days</span> <b>{hover.n}</b></div>
          <div><span>Normal curve</span> <b>{expected(hover.lo + BIN / 2).toFixed(1)}</b></div>
        </div>
      )}
    </div>
  );
}
