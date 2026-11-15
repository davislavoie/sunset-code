// Zoom maths for the fullscreen viewer (lightbox.jsx). view = { s, x, y }: scale and offset in px,
// applied as translate(x, y) scale(s) about the image's centre.

export const FIT = { s: 1, x: 0, y: 0 };
export const MAX_ZOOM = 8;

/** view zoomed by factor, keeping the point (px, py) -- measured from the image's centre as shown now -- under the cursor. */
export function zoomAt(view, px, py, factor) {
  const s = Math.min(MAX_ZOOM, Math.max(1, view.s * factor));
  if (s === 1) return FIT;
  const k = s / view.s;
  return { s, x: view.x - px * (k - 1), y: view.y - py * (k - 1) };
}
