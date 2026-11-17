// Hue / saturation / value histograms of a photo's sky (shares of sky pixels), drawn as three stacked
// strips, each on its own axis. Stored by sunset_process.py with each capture (/api/hist); captures scored before that
// are counted here in the browser instead.

import { useEffect, useId, useRef, useState } from "react";
import { AreaClosed } from "@visx/shape";
import { scaleLinear } from "@visx/scale";
import { ParentSize } from "@visx/responsive";
import { curveMonotoneX } from "@visx/curve";
import { fetchScoringConfig, getJson, thumb } from "./api.js";
import { COLOR_META } from "./ScoreBreakdown.jsx";
import { loadImage, rgbToOpenCvHsv, toResizedCanvas } from "./hsv.js";
import { bandHistograms } from "./scoring.js";

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

/** highlight: score colors (scoring.js COLORS): their hue range is shaded, and the saturation and value
 *  strips switch to only the pixels counted as those colors. */
export default function HsvHistogram({ imageUrl, camera, ts, highlight = [] }) {
  const ref = useRef(null);
  const [hist, setHist] = useState(null);
  const [error, setError] = useState(false);
  const [config, setConfig] = useState(null); // hsv_score.json
  const [byColor, setByColor] = useState(null); // scoring.js bandHistograms of this photo
  const wanted = highlight.length > 0;
  useEffect(() => {
    if (wanted && !config) fetchScoringConfig().then(setConfig, () => {});
  }, [wanted, config]);
  // Counted from the photo the first time a color is highlighted (the stored histograms are whole-sky only).
  useEffect(() => {
    if (!wanted || !config || !imageUrl) return;
    let live = true;
    loadImage(thumb(imageUrl, 960)).then((img) => {
      const ctx = toResizedCanvas(img, SAMPLE_WIDTH).getContext("2d");
      if (live) setByColor(bandHistograms(ctx.getImageData(0, 0, ctx.canvas.width, ctx.canvas.height), config, camera));
    }, () => {});
    return () => { live = false; };
  }, [wanted, config, imageUrl, camera]);
  useEffect(() => setByColor(null), [imageUrl]);

  // Only fetch and crunch the photo once the row scrolls near the screen.
  useEffect(() => {
    const el = ref.current;
    if (!el || !imageUrl) return;
    let live = true;
    const observer = new IntersectionObserver(([entry]) => {
      if (!entry.isIntersecting) return;
      observer.disconnect();
      const compute = () =>
        loadImage(thumb(imageUrl, 960)).then((img) => {
          const ctx = toResizedCanvas(img, SAMPLE_WIDTH).getContext("2d");
          return hsvHistograms(ctx.getImageData(0, 0, ctx.canvas.width, ctx.canvas.height));
        });
      const stored = camera && ts ? getJson(`/api/hist?camera=${encodeURIComponent(camera)}&ts=${encodeURIComponent(ts)}`) : Promise.reject();
      stored
        .catch(compute)
        .then((h) => live && setHist(h))
        .catch(() => live && setError(true));
    }, { rootMargin: "400px" });
    observer.observe(el);
    return () => {
      live = false;
      observer.disconnect();
    };
  }, [imageUrl, camera, ts]);

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
        <HistChart hist={hist} byColor={byColor} marks={config ? highlight.map((c) => ({ color: c, hue: config.bands[c].hue })) : []} />
      )}
    </div>
  );
}

// One strip each, on its own axis (OpenCV: hue 0-179 = half-degrees, saturation and value 0-255).
const SERIES = [
  { key: "hue", label: "Hue", fill: "url(#hue-spectrum)", opacity: 0.85 },
  { key: "saturation", label: "Saturation", fill: "var(--chart-2)", opacity: 0.5 },
  { key: "value", label: "Value", fill: "var(--muted-foreground)", opacity: 0.45 },
];

const M = { top: 4, right: 6, bottom: 15, left: 30 };

// marks: highlighted score colors. Their hue range is shaded on the hue strip; the saturation and value strips
// show only the pixels counted as those colors (byColor), each in the color's tint.
function HistChart({ hist, byColor, marks }) {
  const tinted = byColor && marks.length > 0;
  const layers = (sr) => (sr.key !== "hue" && tinted
    ? marks.map(({ color }) => ({ key: color, label: COLOR_META[color].label, data: byColor[color][sr.key], fill: COLOR_META[color].swatch, opacity: 0.6 }))
    : [{ ...sr, data: hist[sr.key] }]);
  return (
    <>
      <div className="hsv-hist-title">HSV histogram</div>
      <div className="hsv-hist-legend">% of sky at each number · drag to zoom</div>
      <div className="hsv-hist-plot">
        {hist ? SERIES.map((sr) => (
          <Strip key={sr.key} sr={sr} layers={layers(sr)}
            marks={sr.key === "hue" ? marks.map((b) => ({ color: b.color, range: [b.hue[0] - 0.5, b.hue[1] + 0.5] })) : []} />
        )) : <div className="skeleton" style={{ height: "100%" }} />}
      </div>
    </>
  );
}

// Drag across a strip to zoom into that range; double-click to zoom back out.
// layers: the areas drawn on it, all on the same axis.
function Strip({ sr, layers, marks }) {
  const full = [0, layers[0].data.length - 1];
  const [hover, setHover] = useState(null);
  const [domain, setDomain] = useState(full);
  const [drag, setDrag] = useState(null); // [startBin, currentBin] while dragging
  const clipId = useId();
  const zoomed = domain[0] !== full[0] || domain[1] !== full[1];
  // Y fits the tallest bar in view, so small peaks grow when zoomed in.
  const peak = Math.max(...layers.flatMap((l) => l.data.slice(domain[0], domain[1] + 1)));

  return (
    <div className="hsv-hist-strip">
      <div className="hsv-hist-name">{sr.label}{zoomed && ` ${domain[0]}-${domain[1]} · double-click to reset`}</div>
      <ParentSize>
        {({ width, height }) => {
          if (!width) return null;
          const left = M.left, right = width - M.right, bottom = height - M.bottom;
          const x = scaleLinear({ domain, range: [left, right] });
          const binAt = (e) => Math.round(x.invert(e.clientX - e.currentTarget.getBoundingClientRect().left));
          const clampBin = (b) => Math.max(domain[0], Math.min(domain[1], b));
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
              onDoubleClick={() => setDomain(full)}
            >
              <clipPath id={clipId}>
                <rect x={left} y={0} width={right - left} height={bottom} />
              </clipPath>
              {x.ticks(6).map((t) => (
                <g key={`x${t}`}>
                  <line className="hsv-hist-grid" x1={x(t)} x2={x(t)} y1={M.top} y2={bottom} />
                  <text className="hsv-hist-tick" x={x(t)} y={bottom + 11} textAnchor="middle">{t}</text>
                </g>
              ))}
              {y.ticks(2).map((t) => (
                <g key={`y${t}`}>
                  <line className="hsv-hist-grid" x1={left} x2={right} y1={y(t)} y2={y(t)} />
                  <text className="hsv-hist-tick" x={left - 4} y={y(t) + 3} textAnchor="end">{`${+(t * 100).toFixed(1)}%`}</text>
                </g>
              ))}
              <g clipPath={`url(#${clipId})`}>
                {marks.map(({ color, range }) => (
                  <rect key={color} x={x(range[0])} width={x(range[1]) - x(range[0])} y={M.top} height={bottom - M.top}
                    fill={COLOR_META[color].swatch} fillOpacity={0.25} />
                ))}
                {layers.map((l) => (
                  <AreaClosed key={l.key} data={l.data} x={(_, i) => x(i)} y={(d) => y(Math.min(d, y.domain()[1]))} yScale={y}
                    curve={curveMonotoneX} fill={l.fill} fillOpacity={l.opacity} />
                ))}
              </g>
              {drag && drag[0] !== drag[1] && (
                <rect className="hsv-hist-brush" x={x(Math.min(...drag))} y={M.top}
                  width={Math.abs(x(drag[1]) - x(drag[0]))} height={bottom - M.top} />
              )}
              <line className="hsv-hist-axis-line" x1={left} x2={right} y1={bottom} y2={bottom} />
              {hover != null && <line className="hsv-hist-cursor" x1={x(hover)} x2={x(hover)} y1={M.top} y2={bottom} />}
            </svg>
            {hover != null && !drag && (
              // The share of the sky's pixels at exactly the number under the cursor; flips left past the middle to stay inside.
              <div className="scatter-tip hsv-hist-tip" style={x(hover) > width / 2
                ? { right: width - x(hover) + 10, top: 2 } : { left: x(hover) + 10, top: 2 }}>
                {layers.map((l) => (
                  <div key={l.key}>
                    <span>{sr.key === "hue" ? `Hue ${hover} (${hover * 2}°)` : `${l.label} ${hover}`}</span>
                    <b>{`${(l.data[hover] * 100).toFixed(1)}%`}</b>
                  </div>
                ))}
              </div>
            )}
            </>
          );
        }}
      </ParentSize>
    </div>
  );
}
