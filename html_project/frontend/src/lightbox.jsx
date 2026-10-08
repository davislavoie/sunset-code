// Shared fullscreen image viewer used across pages.

import { createContext, useContext, useEffect, useState } from "react";
import Img from "./Img.jsx";

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
        {src && <img className="lightbox-img" src={src} alt="" onClick={(e) => e.stopPropagation()} />}
      </div>
    </LightboxContext.Provider>
  );
}

export const useLightbox = () => useContext(LightboxContext);

/** A fade-in <img> that opens fullscreen on click. */
export function Zoomable({ className = "", ...props }) {
  const { open } = useLightbox();
  return <Img {...props} className={`zoomable ${className}`.trim()} onClick={() => open(props.src)} />;
}

