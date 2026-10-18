// The photo with the colors the score counts painted over the sky, drawn in the browser from the
// band limits in hsv_score.json (the score itself comes from sunset_process.py). Replaces the
// pipeline's 11_ranked PNG, which is no longer made.
//
// interactive: one photo, plain by default, with a row per color beside it: hover paints that color,
// click pins it (Ranked images). Otherwise every color is painted, with the shares as a legend above (Score tracker).

import { useEffect, useRef, useState } from "react";
import { Maximize2, X } from "lucide-react";
import { fetchScoringConfig, thumb } from "./api.js";
import { loadImage, toResizedCanvas } from "./hsv.js";
import { useLightbox } from "./lightbox.jsx";
import { COLOR_META } from "./ScoreBreakdown.jsx";
import { COLORS, paintMasks, skyShare } from "./scoring.js";
import Tip from "./Tip.jsx";

// The 960 px copy: sharp at row size, ~50 KB instead of the ~350 KB original. (Fullscreen shows it as painted.)
const WIDTH = 960;

export default function ScoreOverlay({ imageUrl, camera, interactive = false }) {
  const ref = useRef(null);
  const canvasRef = useRef(null);
  const source = useRef(null); // { image, config }: the unpainted photo, kept to repaint on toggle
  const [sky, setSky] = useState(null); // share of the sky per color, 0-1
  const [error, setError] = useState(false);
  const [fullSrc, setFullSrc] = useState(null);
  const [shown, setShown] = useState(() => new Set(interactive ? [] : COLORS)); // pinned
  const [preview, setPreview] = useState(null); // color under the mouse
  const lightbox = useLightbox();

  const paint = (show) => {
    const { image, config } = source.current;
    const result = paintMasks(image, config, camera, show);
    const canvas = canvasRef.current;
    canvas.width = image.width;
    canvas.height = image.height;
    canvas.getContext("2d").putImageData(new ImageData(result.overlay, image.width, image.height), 0, 0);
    return result;
  };

  // Only fetch and score the photo once the row scrolls near the screen.
  useEffect(() => {
    const el = ref.current;
    if (!el || !imageUrl) return;
    let live = true;
    const observer = new IntersectionObserver(([entry]) => {
      if (!entry.isIntersecting) return;
      observer.disconnect();
      Promise.all([loadImage(thumb(imageUrl, WIDTH)), fetchScoringConfig()])
        .then(([img, config]) => {
          if (!live) return;
          const ctx = toResizedCanvas(img, WIDTH).getContext("2d");
          const { width, height } = ctx.canvas;
          source.current = { image: ctx.getImageData(0, 0, width, height), config };
          const result = paint(shown);
          // coverage is a share of the whole frame; the scorer only looks above the horizon.
          const share = Math.floor(height * skyShare(config, camera)) / height;
          setSky(Object.fromEntries(COLORS.map((c) => [c, result.coverage[c] / share])));
        })
        .catch(() => live && setError(true));
    }, { rootMargin: "400px" });
    observer.observe(el);
    return () => {
      live = false;
      observer.disconnect();
    };
  }, [imageUrl, camera]);

  const painted = (pins, hover) => (hover ? new Set([...pins, hover]) : pins);
  const toggle = (color) => {
    const next = new Set(shown);
    next.has(color) ? next.delete(color) : next.add(color);
    setShown(next);
    if (source.current) paint(painted(next, preview));
  };
  const hover = (color) => {
    setPreview(color);
    if (source.current) paint(painted(shown, color));
  };

  // Fullscreen shows the photo as painted right now.
  const isOpen = fullSrc && lightbox.src === fullSrc;
  const toggleFull = (e) => {
    e.stopPropagation();
    if (isOpen) return lightbox.close();
    const src = canvasRef.current.toDataURL("image/jpeg", 0.9);
    setFullSrc(src);
    lightbox.open(src);
  };

  if (!imageUrl || error) {
    return <div className="score-overlay empty">{imageUrl ? "Couldn't read the photo" : "No photo"}</div>;
  }

  const photo = (
    <div className="score-overlay ranked-img-cell">
      <canvas ref={canvasRef} width={1920} height={1080} className={sky ? "ready" : ""} />
      {!sky && <div className="skeleton score-overlay-skeleton" />}
      {sky && (
        <Tip label={isOpen ? "Close fullscreen" : "View fullscreen"}>
          <button className="fullscreen-toggle-btn" aria-label={isOpen ? "Close fullscreen" : "View fullscreen"} onClick={toggleFull}>
            {isOpen ? <X size={16} /> : <Maximize2 size={16} />}
          </button>
        </Tip>
      )}
    </div>
  );

  if (interactive) {
    return (
      <div className="rank-media overlay-split" ref={ref}>
        <div className="hsv-hist-title">Photo</div>
        <div className="overlay-split-body">
          {photo}
          <div className="overlay-picker" role="group" aria-label="Colors the score counts: hover to preview on the photo, click to pin">
            <p className="overlay-help">{matchMedia("(hover: hover)").matches ? "Hover" : "Tap"} to overlay color</p>
            {COLORS.map((c) => (
              <button key={c} type="button" className={`overlay-pick${shown.has(c) ? " pinned" : ""}`}
                style={{ "--swatch": COLOR_META[c].swatch }} aria-pressed={shown.has(c)} disabled={!sky}
                // mouse only: a tap on a phone fires pointerenter too, and would leave the color stuck on
                onPointerEnter={(e) => e.pointerType === "mouse" && hover(c)}
                onPointerLeave={(e) => e.pointerType === "mouse" && hover(null)}
                onClick={() => toggle(c)}>
                <span className="overlay-pick-name">
                  <i />
                  {COLOR_META[c].label}
                </span>
                <b>{sky ? `${(sky[c] * 100).toFixed(1)}%` : "–"}</b>
                <span className="overlay-pick-bar" aria-hidden="true">
                  <span style={{ width: sky ? `${Math.min(100, sky[c] * 100)}%` : 0 }} />
                </span>
              </button>
            ))}
          </div>
        </div>
      </div>
    );
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
      {photo}
    </div>
  );
}
