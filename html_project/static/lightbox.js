// Shared fullscreen image viewer used across pages.

let overlayEl = null;

function ensureOverlay() {
  if (overlayEl) return overlayEl;

  overlayEl = document.createElement("div");
  overlayEl.className = "lightbox-overlay";
  overlayEl.addEventListener("click", closeLightbox);

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

export function openLightbox(src) {
  const overlay = ensureOverlay();
  overlay.querySelector("img").src = src;
  overlay.classList.add("open");
}

export function closeLightbox() {
  if (overlayEl) overlayEl.classList.remove("open");
}

/** Makes an <img> clickable to open it fullscreen. */
export function makeZoomable(imgEl) {
  imgEl.classList.add("zoomable");
  imgEl.addEventListener("click", () => openLightbox(imgEl.src));
}
