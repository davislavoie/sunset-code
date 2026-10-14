// Shared fullscreen image viewer used across pages.

import { createContext, useContext, useEffect, useState } from "react";
import { X } from "lucide-react";
import Img from "./Img.jsx";
import { photo } from "./api.js";

const LightboxContext = createContext(null);

export function LightboxProvider({ children }) {
  // Keep the last image mounted while closed so it can fade out instead of vanishing.
  const [{ src, open }, setState] = useState({ src: null, open: false });
  const close = () => setState((s) => ({ ...s, open: false }));

  useEffect(() => {
    const onKey = (e) => e.key === "Escape" && close();
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, []);

  const value = { src: open ? src : null, open: (next) => setState({ src: next, open: true }), close };

  return (
    <LightboxContext.Provider value={value}>
      {children}
      <div className={`lightbox-overlay${open ? " open" : ""}`} onClick={close}>
        {src && (
          <div className="lightbox-frame" onClick={(e) => e.stopPropagation()}>
            <img className="lightbox-img" src={photo(src)} alt="" />
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

