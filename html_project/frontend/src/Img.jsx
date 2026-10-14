// <img> that fades in softly once loaded (instantly if it was already cached). Width/height (the image's natural
// size) let the browser reserve the right space up front, so nothing jumps.
// Only the first load animates: when src changes (e.g. Next in a viewer) the browser
// keeps showing the current image until the new one is ready, so it swaps in place.

import { useEffect, useLayoutEffect, useRef, useState } from "react";

// Every camera shoots 1920x1080; the generated ranked/histogram plots are close to fixed sizes.
export const SIZES = {
  photo: { width: 1920, height: 1080 },
  ranked: { width: 1760, height: 1115 },
  histogram: { width: 2780, height: 1406 },
};

export const sizeForLabel = (label) =>
  /ranked/i.test(label) ? SIZES.ranked : /histogram/i.test(label) ? SIZES.histogram : SIZES.photo;

// placeholder: a small copy to show at once (usually already cached from a tile) while the full
// photo in src downloads; the full one swaps in when it's ready.
export default function Img({ className = "", onLoad, placeholder, src, ...props }) {
  const ref = useRef(null);
  const [loaded, setLoaded] = useState(false);
  const [cached, setCached] = useState(false); // already complete before first paint: show it, no fade
  const [ready, setReady] = useState(null); // the full src once it has downloaded

  useLayoutEffect(() => {
    if (ref.current?.complete && ref.current.naturalWidth) {
      setCached(true);
      setLoaded(true);
    }
  }, []);

  useEffect(() => {
    if (!placeholder || !src) return;
    const full = new Image();
    full.onload = () => setReady(src);
    full.src = src;
    return () => { full.onload = null; };
  }, [src, placeholder]);

  return (
    <img
      decoding="async"
      {...props}
      src={placeholder && ready !== src ? placeholder : src}
      ref={ref}
      className={`img-fade${loaded ? " is-loaded" : ""}${cached ? " was-cached" : ""} ${className}`.trim()}
      onLoad={(e) => {
        setLoaded(true);
        onLoad?.(e);
      }}
      onError={() => setLoaded(true)}
    />
  );
}
