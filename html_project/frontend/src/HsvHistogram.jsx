// Hue / saturation / value histograms of a photo's sky, computed in the browser. Same data as
// the pipeline's 12_histogram PNG (sunset_process.py: cv2.calcHist on the top half + 30 rows),
// drawn as three overlaid area charts. Shares of sky pixels rather than raw counts.

import { useEffect, useRef, useState } from "react";
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

function HistChart({ hist }) {
  const [hover, setHover] = useState(null);
  const peak = hist ? Math.max(...SERIES.map((sr) => Math.max(...hist[sr.key]))) : 0;
  const pct = (key) => (hist[key][hover] == null ? "–" : `${(hist[key][hover] * 100).toFixed(1)}%`);

  return (
    <>
      <div className="hsv-hist-legend">
        {SERIES.slice().reverse().map((sr) => (
          <span key={sr.key}>
            <i style={{ background: sr.swatch }} /> {sr.label}
            {hover != null && hist && <b>{pct(sr.key)}</b>}
          </span>
        ))}
        {hover != null && <span className="hsv-hist-bin">at {hover}</span>}
      </div>
      <div className="hsv-hist-plot">
        {hist ? (
          <ParentSize>
            {({ width, height }) => {
              if (!width) return null;
              const x = scaleLinear({ domain: [0, 255], range: [0, width] });
              const y = scaleLinear({ domain: [0, peak || 1], range: [height, 2] });
              return (
                <svg
                  width={width}
                  height={height}
                  onMouseMove={(e) => {
                    const bin = Math.round(x.invert(e.clientX - e.currentTarget.getBoundingClientRect().left));
                    setHover(Math.max(0, Math.min(255, bin)));
                  }}
                  onMouseLeave={() => setHover(null)}
                >
                  {SERIES.map((sr) => (
                    <AreaClosed key={sr.key} data={hist[sr.key]} x={(_, i) => x(i)} y={(d) => y(d)} yScale={y}
                      curve={curveMonotoneX} fill={sr.fill} fillOpacity={sr.opacity} />
                  ))}
                  {hover != null && <line className="hsv-hist-cursor" x1={x(hover)} x2={x(hover)} y1={0} y2={height} />}
                </svg>
              );
            }}
          </ParentSize>
        ) : (
          <div className="skeleton" style={{ height: "100%" }} />
        )}
      </div>
      <div className="hsv-hist-axis"><span>0</span><span>128</span><span>255</span></div>
    </>
  );
}
