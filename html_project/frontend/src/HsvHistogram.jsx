// Hue / saturation / value histograms of a photo's sky, computed in the browser. Same data as
// the pipeline's 12_histogram PNG (sunset_process.py: cv2.calcHist on the top half + 30 rows),
// drawn as three overlaid area charts. Shares of sky pixels rather than raw counts.

import { useEffect, useId, useRef, useState } from "react";
import { AreaClosed } from "@visx/shape";
import { scaleLinear } from "@visx/scale";
import { ParentSize } from "@visx/responsive";
import { curveMonotoneX } from "@visx/curve";
import { proxied } from "./api.js";
import { loadImage, rgbToOpenCvHsv, toResizedCanvas } from "./hsv.js";

// Histogram shape doesn't need every pixel; 480 px wide is ~16x fewer and looks the same.
const SAMPLE_WIDTH = 480;

export function hsvHistograms({ data, width, height }) {
  const sky = Math.min(height, Math.floor(height / 2 + (30 * height) / 1080));
  const h = new Array(180).fill(0), s = new Array(256).fill(0), v = new Array(256).fill(0);
  for (let i = 0; i < sky * width * 4; i += 4) {
    const [hh, ss, vv] = rgbToOpenCvHsv(data[i], data[i + 1], data[i + 2]);
    h[Math.round(hh) % 180]++;
    s[Math.round(ss)]++;
    v[Math.round(vv)]++;
  }
  const n = sky * width;
  const share = (bins) => bins.map((c) => c / n);
  return { hue: share(h), saturation: share(s), value: share(v) };
}

// Drawn on one shared 0-255 axis like the pipeline's PNG (hue only runs to 179).
const SERIES = [
  { key: "value", label: "Value", fill: "var(--muted-foreground)", opacity: 0.35, swatch: "var(--muted-foreground)" },
  { key: "saturation", label: "Saturation", fill: "var(--chart-2)", opacity: 0.4, swatch: "var(--chart-2)" },
  { key: "hue", label: "Hue", fill: "url(#hue-spectrum)", opacity: 0.8, swatch: "linear-gradient(90deg, #e33, #ee3, #3e3, #3ee, #33e, #e3e)" },
];

export default function HsvHistogram({ imageUrl }) {
  const ref = useRef(null);
  const [hist, setHist] = useState(null);
  const [error, setError] = useState(false);

  // Only fetch and crunch the photo once the row scrolls near the screen.
  useEffect(() => {
    const el = ref.current;
    if (!el || !imageUrl) return;
    let live = true;
    const observer = new IntersectionObserver(([entry]) => {
      if (!entry.isIntersecting) return;
      observer.disconnect();
      loadImage(proxied(imageUrl))
        .then((img) => {
          const ctx = toResizedCanvas(img, SAMPLE_WIDTH).getContext("2d");
          if (live) setHist(hsvHistograms(ctx.getImageData(0, 0, ctx.canvas.width, ctx.canvas.height)));
        })
        .catch(() => live && setError(true));
    }, { rootMargin: "400px" });
    observer.observe(el);
    return () => {
      live = false;
      observer.disconnect();
    };
  }, [imageUrl]);

  return (
    <div className="hsv-hist" ref={ref}>
      <svg width="0" height="0" aria-hidden="true" style={{ position: "absolute" }}>
        <defs>
          {/* OpenCV hue 0-179 is 0-358 degrees: colour the hue chart by the hue it counts. */}
          <linearGradient id="hue-spectrum" x1="0" x2="1" y1="0" y2="0">
            {[0, 60, 120, 180, 240, 300, 360].map((deg) => (
              <stop key={deg} offset={deg / 360} stopColor={`hsl(${deg} 85% 55%)`} />
            ))}
          </linearGradient>
        </defs>
      </svg>
      {!imageUrl || error ? (
        <div className="hsv-hist-empty">{imageUrl ? "Couldn't read the photo" : "No photo"}</div>
      ) : (
        <HistChart hist={hist} />
      )}
    </div>
  );
}

const M = { top: 6, right: 6, bottom: 34, left: 36 };
// Gridline every 25 like the pipeline's PNG; labels every 50 so they fit a narrow cell.
const X_TICKS = Array.from({ length: 11 }, (_, i) => i * 25);
const FULL = [0, 255];

// Drag across the chart to zoom into that range; double-click to zoom back out.
function HistChart({ hist }) {
  const [hover, setHover] = useState(null);
  const [hoverY, setHoverY] = useState(null); // cursor height in px, for the y readout
  const [domain, setDomain] = useState(FULL);
  const [drag, setDrag] = useState(null); // [startBin, currentBin] while dragging
  const clipId = useId();
  const zoomed = domain !== FULL;
  // Y fits the tallest bar in view, so small peaks grow when zoomed in.
  const peak = hist
    ? Math.max(...SERIES.map((sr) => Math.max(...hist[sr.key].slice(domain[0], domain[1] + 1))))
    : 0;
  const pct = (key) => (hist[key][hover] == null ? "–" : `${(hist[key][hover] * 100).toFixed(1)}%`);

  return (
    <>
      <div className="hsv-hist-title">HSV histogram</div>
      <div className="hsv-hist-legend">
        {SERIES.slice().reverse().map((sr) => (
          <span key={sr.key}>
            <i style={{ background: sr.swatch }} /> {sr.label}
            {/* Always there at a fixed width so the legend doesn't shift while hovering. */}
            <b>{hover != null && hist ? pct(sr.key) : ""}</b>
          </span>
        ))}
      </div>
      <div className="hsv-hist-plot">
        {/* Over the plot rather than in the legend, so zooming never changes the layout; hidden while the hover chip shows. */}
        {zoomed && hover == null && <div className="hsv-hist-zoom">{`${domain[0]}-${domain[1]} · double-click to reset`}</div>}
        {hist ? (
          <ParentSize>
            {({ width, height }) => {
              if (!width) return null;
              const left = M.left, right = width - M.right, bottom = height - M.bottom;
              const x = scaleLinear({ domain, range: [left, right] });
              const binAt = (e) => Math.round(x.invert(e.clientX - e.currentTarget.getBoundingClientRect().left));
              const clampBin = (b) => Math.max(domain[0], Math.min(domain[1], b));
              const xTicks = zoomed ? x.ticks(5) : X_TICKS;
              const y = scaleLinear({ domain: [0, peak || 1], range: [bottom, M.top], nice: true });
              return (
                <>
                <svg
                  width={width}
                  height={height}
                  onMouseDown={(e) => {
                    e.preventDefault(); // no text selection while dragging
                    const b = clampBin(binAt(e));
                    setDrag([b, b]);
                  }}
                  onMouseMove={(e) => {
                    const bin = binAt(e);
                    setHover(bin < domain[0] || bin > domain[1] ? null : bin);
                    setHoverY(Math.max(M.top, Math.min(bottom, e.clientY - e.currentTarget.getBoundingClientRect().top)));
                    if (drag) setDrag([drag[0], clampBin(bin)]);
                  }}
                  onMouseUp={() => {
                    if (drag) {
                      const [a, b] = [Math.min(...drag), Math.max(...drag)];
                      if (b - a >= 3) setDomain([a, b]);
                      setDrag(null);
                    }
                  }}
                  onMouseLeave={() => {
                    setHover(null);
                    setDrag(null);
                  }}
                  onDoubleClick={() => setDomain(FULL)}
                >
                  <clipPath id={clipId}>
                    <rect x={left} y={0} width={right - left} height={bottom} />
                  </clipPath>
                  {xTicks.map((t) => (
                    <g key={`x${t}`}>
                      <line className="hsv-hist-grid" x1={x(t)} x2={x(t)} y1={M.top} y2={bottom} />
                      {(zoomed || t % 50 === 0) && <text className="hsv-hist-tick" x={x(t)} y={bottom + 13} textAnchor="middle">{t}</text>}
                    </g>
                  ))}
                  {y.ticks(4).map((t) => (
                    <g key={`y${t}`}>
                      <line className="hsv-hist-grid" x1={left} x2={right} y1={y(t)} y2={y(t)} />
                      <text className="hsv-hist-tick" x={left - 4} y={y(t) + 3} textAnchor="end">{+(t * 100).toFixed(1)}</text>
                    </g>
                  ))}
                  <g clipPath={`url(#${clipId})`}>
                    {SERIES.map((sr) => (
                      <AreaClosed key={sr.key} data={hist[sr.key]} x={(_, i) => x(i)} y={(d) => y(Math.min(d, y.domain()[1]))} yScale={y}
                        curve={curveMonotoneX} fill={sr.fill} fillOpacity={sr.opacity} />
                    ))}
                  </g>
                  {drag && drag[0] !== drag[1] && (
                    <rect className="hsv-hist-brush" x={x(Math.min(...drag))} y={M.top}
                      width={Math.abs(x(drag[1]) - x(drag[0]))} height={bottom - M.top} />
                  )}
                  <line className="hsv-hist-axis-line" x1={left} x2={right} y1={bottom} y2={bottom} />
                  {hover != null && <line className="hsv-hist-cursor" x1={x(hover)} x2={x(hover)} y1={M.top} y2={bottom} />}
                  <text className="hsv-hist-axis-label" x={(left + right) / 2} y={height - 2} textAnchor="middle">
                    Channel value (0-255)
                  </text>
                  <text className="hsv-hist-axis-label" transform={`translate(10 ${(M.top + bottom) / 2}) rotate(-90)`} textAnchor="middle">
                    % of sky
                  </text>
                </svg>
                {hover != null && !drag && (
                  // The channel value under the cursor; flips left past the middle to stay inside the plot.
                  <div className="scatter-tip hsv-hist-tip" style={x(hover) > width / 2
                    ? { right: width - x(hover) + 10, top: Math.max(0, hoverY - 22) } : { left: x(hover) + 10, top: Math.max(0, hoverY - 22) }}>
                    {`${hover}, ${(y.invert(hoverY) * 100).toFixed(1)}%`}
                  </div>
                )}
                </>
              );
            }}
          </ParentSize>
        ) : (
          <div className="skeleton" style={{ height: "100%" }} />
        )}
      </div>
    </>
  );
}
