// Shared "all images from this date" viewer: main image + prev/next + thumbnail
// strip. Used by the calendar's day-expand view and ranking.js's "Show in
// Calendar" button. Self-managing: re-renders only its own mount point.

import { makeZoomable } from "./lightbox.js";

export function mountDayDetail(mountEl, date, allData, { onClose, initialIndex = 0, onLoadToHsv } = {}) {
  let index = initialIndex;

  const dateImages = allData.filter((img) => img.Date === date);
  const regular = dateImages
    .filter((img) => !img.Label.toLowerCase().includes("ranked") && !img.Label.toLowerCase().includes("histogram"))
    .sort((a, b) => (a.Time > b.Time ? 1 : -1));
  const special = dateImages.filter(
    (img) => img.Label.toLowerCase().includes("ranked") || img.Label.toLowerCase().includes("histogram")
  );
  const images = [...regular, ...special];

  function render() {
    mountEl.innerHTML = "";
    if (!images.length) return;
    if (index >= images.length) index = 0;
    const current = images[index];

    const wrap = document.createElement("div");
    wrap.className = "detail";

    const header = document.createElement("div");
    header.className = "detail-header";
    const title = document.createElement("h4");
    title.textContent = `${current.Label.slice(3)} - ${date}`;
    header.appendChild(title);

    const actions = document.createElement("div");
    actions.className = "detail-header-actions";

    if (onLoadToHsv) {
      const hsvBtn = document.createElement("button");
      hsvBtn.className = "btn";
      hsvBtn.textContent = "Load to HSV Tuner";
      hsvBtn.addEventListener("click", () => onLoadToHsv(current.Image));
      actions.appendChild(hsvBtn);
    }

    const closeBtn = document.createElement("button");
    closeBtn.className = "btn";
    closeBtn.textContent = "✕ Close";
    closeBtn.addEventListener("click", () => {
      mountEl.innerHTML = "";
      if (onClose) onClose();
    });
    actions.appendChild(closeBtn);

    header.appendChild(actions);
    wrap.appendChild(header);

    const nav = document.createElement("div");
    nav.className = "detail-nav";
    const prevBtn = document.createElement("button");
    prevBtn.className = "btn";
    prevBtn.textContent = "← Previous";
    prevBtn.addEventListener("click", () => {
      index = index === 0 ? images.length - 1 : index - 1;
      render();
    });
    const info = document.createElement("div");
    info.className = "info";
    info.textContent = `Image ${index + 1} of ${images.length} | Time: ${current.Time} | Score: ${current.Score.toFixed(1)}%`;
    const nextBtn = document.createElement("button");
    nextBtn.className = "btn";
    nextBtn.textContent = "Next →";
    nextBtn.addEventListener("click", () => {
      index = index >= images.length - 1 ? 0 : index + 1;
      render();
    });
    nav.append(prevBtn, info, nextBtn);
    wrap.appendChild(nav);

    const mainImgWrap = document.createElement("div");
    mainImgWrap.className = "detail-main-img";
    const mainImg = document.createElement("img");
    mainImg.src = current.Image;
    makeZoomable(mainImg);
    mainImgWrap.appendChild(mainImg);
    wrap.appendChild(mainImgWrap);

    const stripHeading = document.createElement("h5");
    stripHeading.textContent = "All images from this date:";
    wrap.appendChild(stripHeading);

    const strip = document.createElement("div");
    strip.className = "thumb-strip";
    strip.style.gridTemplateColumns = `repeat(${images.length}, 1fr)`;
    images.forEach((img, idx) => {
      const thumb = document.createElement("div");
      thumb.className = "thumb" + (idx === index ? " selected" : "");
      const thumbImg = document.createElement("img");
      thumbImg.src = img.Image;
      thumbImg.loading = "lazy";
      const label = document.createElement("div");
      label.className = "label";
      label.textContent = img.Label.slice(3);
      thumb.append(thumbImg, label);
      thumb.addEventListener("click", () => {
        index = idx;
        render();
      });
      strip.appendChild(thumb);
    });
    wrap.appendChild(strip);

    mountEl.appendChild(wrap);
  }

  render();

  return {
    close() {
      mountEl.innerHTML = "";
    },
  };
}
