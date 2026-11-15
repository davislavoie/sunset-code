// Shared fullscreen image viewer used across pages. Scroll (or double-click) zooms in on the point
// under the cursor; drag moves the photo while zoomed.

import { createContext, useContext, useEffect, useRef, useState } from "react";
import { X } from "lucide-react";
import Img from "./Img.jsx";
import { photo } from "./api.js";
import { FIT, zoomAt } from "./zoom.js";

const LightboxContext = createContext(null);

export function LightboxProvider({ children }) {
  // Keep the last image mounted while closed so it can fade out instead of vanishing.
  const [{ src, open }, setState] = useState({ src: null, open: false });
  const [view, setView] = useState(FIT);
  const overlayRef = useRef(null);
  const imgRef = useRef(null);
  const dragging = useRef(false);
  const close = () => setState((s) => ({ ...s, open: false }));

  const zoom = (e, factor) => {
    const r = imgRef.current?.getBoundingClientRect();
    if (r) setView((v) => zoomAt(v, e.clientX - (r.left + r.width / 2), e.clientY - (r.top + r.height / 2), factor));
  };

  useEffect(() => {
    const onKey = (e) => e.key === "Escape" && close();
    document.addEventListener("keydown", onKey);
    // Not React's onWheel: that one is passive, so it couldn't stop the page scrolling behind.
    const onWheel = (e) => {
      e.preventDefault();
      zoom(e, e.deltaY < 0 ? 1.25 : 0.8);
    };
    const overlay = overlayRef.current;
    overlay.addEventListener("wheel", onWheel, { passive: false });
    return () => {
      document.removeEventListener("keydown", onKey);
      overlay.removeEventListener("wheel", onWheel);
    };
  }, []);

  const value = {
    src: open ? src : null,
    open: (next) => {
      setView(FIT);
      setState({ src: next, open: true });
    },
    close,
  };
  const zoomed = view.s > 1;

  return (
    <LightboxContext.Provider value={value}>
      {children}
      <div ref={overlayRef} className={`lightbox-overlay${open ? " open" : ""}`} onClick={close}>
        {src && (
          <div className="lightbox-frame" onClick={(e) => e.stopPropagation()}>
            {/* ponytail: no pinch handling; phones zoom the page with two fingers, or double-tap here. */}
            <img
              ref={imgRef}
              className="lightbox-img"
              src={photo(src)}
              alt=""
              draggable={false}
              style={zoomed
                ? { transform: `translate(${view.x}px, ${view.y}px) scale(${view.s})`, transition: "none", cursor: "grab", touchAction: "none" }
                : undefined}
              onDoubleClick={(e) => zoom(e, zoomed ? 0 : 2.5)}
              onPointerDown={(e) => {
                if (!zoomed) return;
                e.currentTarget.setPointerCapture(e.pointerId);
                dragging.current = true;
              }}
              onPointerMove={(e) => dragging.current && setView((v) => ({ ...v, x: v.x + e.movementX, y: v.y + e.movementY }))}
              onPointerUp={() => (dragging.current = false)}
              onPointerCancel={() => (dragging.current = false)}
            />
            <button className="lightbox-close" aria-label="Close fullscreen" onClick={close}>
              <X size={18} />
            </button>
          </div>
        )}
      </div>
    </LightboxContext.Provider>
  );
}

export const useLightbox = () => useContext(LightboxContext);

/** A fade-in <img> that opens fullscreen on click; full: the photo to open when src is a small copy. */
export function Zoomable({ className = "", full, ...props }) {
  const { open } = useLightbox();
  return <Img {...props} className={`zoomable ${className}`.trim()} onClick={() => open(full ?? props.src)} />;
}
