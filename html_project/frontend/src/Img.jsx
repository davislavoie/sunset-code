// <img> that pulses while loading, then fades in. Width/height (the image's natural
// size) let the browser reserve the right space up front, so nothing jumps.
// Only the first load animates: when src changes (e.g. Next in a viewer) the browser
// keeps showing the current image until the new one is ready, so it swaps in place.

import { useState } from "react";

// Every camera shoots 1920x1080; the generated ranked/histogram plots are close to fixed sizes.
export const SIZES = {
  photo: { width: 1920, height: 1080 },
  ranked: { width: 1760, height: 1115 },
  histogram: { width: 2780, height: 1406 },
};

export const sizeForLabel = (label) =>
  /ranked/i.test(label) ? SIZES.ranked : /histogram/i.test(label) ? SIZES.histogram : SIZES.photo;

export default function Img({ className = "", onLoad, ...props }) {
  const [loaded, setLoaded] = useState(false);

  return (
    <img
      decoding="async"
      {...props}
      className={`img-fade${loaded ? " is-loaded" : ""} ${className}`.trim()}
      onLoad={(e) => {
        setLoaded(true);
        onLoad?.(e);
      }}
      onError={() => setLoaded(true)}
    />
  );
}
