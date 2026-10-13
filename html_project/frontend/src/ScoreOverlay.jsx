// The photo with the colors the score counts painted over the sky, drawn in the browser from the
// band limits in hsv_score.json (the score itself comes from sunset_process.py). Replaces the
// pipeline's 11_ranked PNG, which is no longer made.

import { useEffect, useRef, useState } from "react";
import { Maximize2, X } from "lucide-react";
import { fetchScoringConfig, proxied } from "./api.js";
import { loadImage, toResizedCanvas } from "./hsv.js";
import { useLightbox } from "./lightbox.jsx";
import { COLOR_META } from "./ScoreBreakdown.jsx";
import { COLORS, paintMasks } from "./scoring.js";
import Tip from "./Tip.jsx";

// Big enough to look sharp fullscreen, small enough to score quickly in a long list.
const WIDTH = 1280;

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
      Promise.all([loadImage(proxied(imageUrl)), fetchScoringConfig()])
        .then(([img, config]) => {
          if (!live) return;
          const ctx = toResizedCanvas(img, WIDTH).getContext("2d");
          const { width, height } = ctx.canvas;
          const image = ctx.getImageData(0, 0, width, height);
          const result = paintMasks(image, config);
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
    <div className="rank-media" ref={ref}>
      <div className="hsv-hist-title">Score overlay</div>
      <div className="hsv-hist-legend">
        {COLORS.map((c) => (
          <Tip key={c} label={`${COLOR_META[c].label}: share of the sky counted toward the score`}>
            <span>
              <i style={{ background: COLOR_META[c].swatch }} />
              {sky ? `${(sky[c] * 100).toFixed(1)}%` : "–"}
            </span>
          </Tip>
        ))}
      </div>
      <div className="score-overlay ranked-img-cell">
        <canvas ref={canvasRef} width={1920} height={1080} className={sky ? "ready" : ""} />
        {!sky && <div className="skeleton score-overlay-skeleton" />}
        {sky && (
          <>
            <Tip label={isOpen ? "Close fullscreen" : "View fullscreen"}>
              <button className="fullscreen-toggle-btn" aria-label={isOpen ? "Close fullscreen" : "View fullscreen"} onClick={toggleFull}>
                {isOpen ? <X size={16} /> : <Maximize2 size={16} />}
              </button>
            </Tip>
          </>
        )}
      </div>
    </div>
  );
}
