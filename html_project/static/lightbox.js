// Shared fullscreen image viewer used across pages.

let overlayEl = null;
let activeOnClose = null;

function ensureOverlay() {
  if (overlayEl) return overlayEl;

  overlayEl = document.createElement("div");
  overlayEl.className = "lightbox-overlay";
  // stopPropagation so closing the lightbox (clicking its backdrop) never
  // bubbles up to the document-level "click outside collapses sidebar" handler.
  overlayEl.addEventListener("click", (e) => {
    e.stopPropagation();
    closeLightbox();
  });

  const img = document.createElement("img");
  img.className = "lightbox-img";
  img.addEventListener("click", (e) => e.stopPropagation());
  overlayEl.appendChild(img);

  document.body.appendChild(overlayEl);
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeLightbox();
  });

  return overlayEl;
}

export function openLightbox(src, { onClose } = {}) {
  const overlay = ensureOverlay();
  overlay.querySelector("img").src = src;
  overlay.classList.add("open");
  activeOnClose = onClose || null;
}

export function closeLightbox() {
  if (!overlayEl) return;
  overlayEl.classList.remove("open");
  if (activeOnClose) {
    const cb = activeOnClose;
    activeOnClose = null;
    cb();
  }
}

/** Makes an <img> clickable to open it fullscreen. */
export function makeZoomable(imgEl) {
  imgEl.classList.add("zoomable");
  imgEl.addEventListener("click", () => openLightbox(imgEl.src));
}
