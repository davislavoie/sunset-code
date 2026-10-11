// The photo with the colors the score counts painted over the sky, drawn in the browser with
// the same scorer as the Day view's breakdown. Replaces the pipeline's 11_ranked PNG, whose
// style changed over time and whose label boxes don't match the dashboard.

import { useEffect, useRef, useState } from "react";
import { Maximize2, X } from "lucide-react";
import { proxied } from "./api.js";
import { loadImage, toResizedCanvas } from "./hsv.js";
import { useLightbox } from "./lightbox.jsx";
import { COLOR_META } from "./ScoreBreakdown.jsx";
import { COLORS, DEFAULT_COLOR_RANGES, DEFAULT_FORMULA, scoreImage } from "./scoring.js";
import Tip from "./Tip.jsx";

// Big enough to look sharp fullscreen, small enough to score quickly in a long list.
const WIDTH = 1280;
// Only coverage is shown, so the multipliers don't matter here.
const MULTIPLIERS = { red: 1, orange: 1, yellow: 1, pink: 1 };

export default function ScoreOverlay({ imageUrl }) {
  const ref = useRef(null);
  const canvasRef = useRef(null);
  const [sky, setSky] = useState(null); // share of the sky per color, 0-1
  const [error, setError] = useState(false);
  const [fullSrc, setFullSrc] = useState(null);
  const lightbox = useLightbox();

  // Only fetch and score the photo once the row scrolls near the screen.
  useEffect(() => {
    const el = ref.current;
    if (!el || !imageUrl) return;
    let live = true;
    const observer = new IntersectionObserver(([entry]) => {
      if (!entry.isIntersecting) return;
      observer.disconnect();
      loadImage(proxied(imageUrl))
        .then((img) => {
          if (!live) return;
          const ctx = toResizedCanvas(img, WIDTH).getContext("2d");
          const { width, height } = ctx.canvas;
          const image = ctx.getImageData(0, 0, width, height);
          const result = scoreImage(image, { multipliers: MULTIPLIERS, colorRanges: DEFAULT_COLOR_RANGES, formulaParams: DEFAULT_FORMULA });
          const canvas = canvasRef.current;
          canvas.width = width;
          canvas.height = height;
          canvas.getContext("2d").putImageData(new ImageData(result.overlay, width, height), 0, 0);
          // coverage is a share of the whole frame; the scorer only looks at the top half.
          const skyShare = Math.floor(height / 2) / height;
          setSky(Object.fromEntries(COLORS.map((c) => [c, result.coverage[c] / skyShare])));
        })
        .catch(() => live && setError(true));
    }, { rootMargin: "400px" });
    observer.observe(el);
    return () => {
      live = false;
      observer.disconnect();
    };
  }, [imageUrl]);

  const isOpen = fullSrc && lightbox.src === fullSrc;
  const toggleFull = (e) => {
    e.stopPropagation();
    if (isOpen) return lightbox.close();
    const src = fullSrc || canvasRef.current.toDataURL("image/jpeg", 0.9);
    setFullSrc(src);
    lightbox.open(src);
  };

  if (!imageUrl || error) {
    return <div className="score-overlay empty">{imageUrl ? "Couldn't read the photo" : "No photo"}</div>;
  }
  return (
    <div className="score-overlay ranked-img-cell" ref={ref}>
      <canvas ref={canvasRef} width={1920} height={1080} className={sky ? "ready" : ""} />
      {!sky && <div className="skeleton score-overlay-skeleton" />}
      {sky && (
        <>
          <div className="score-overlay-chips">
            {COLORS.map((c) => (
              <Tip key={c} label={`${COLOR_META[c].label}: ${(sky[c] * 100).toFixed(1)}% of the sky counted toward the score`}>
                <span className="score-chip">
                  <i style={{ background: COLOR_META[c].swatch }} />
                  {(sky[c] * 100).toFixed(1)}%
                </span>
              </Tip>
            ))}
          </div>
          <Tip label={isOpen ? "Close fullscreen" : "View fullscreen"}>
            <button className="fullscreen-toggle-btn" aria-label={isOpen ? "Close fullscreen" : "View fullscreen"} onClick={toggleFull}>
              {isOpen ? <X size={16} /> : <Maximize2 size={16} />}
            </button>
          </Tip>
        </>
      )}
    </div>
  );
}
