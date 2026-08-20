// Mirrors streamlit_project/sunset_gallery.py

const COLUMNS = 7;

export function renderGallery(container, state) {
  if (!state.gallery) {
    state.gallery = { selectedDate: null, selectedIndex: 0 };
  }
  const gallery = state.gallery;

  const sunsetData = [...state.sunsetData].sort((a, b) => {
    const ak = a.Date + a.Time, bk = b.Date + b.Time;
    return ak < bk ? 1 : ak > bk ? -1 : 0;
  });

  container.innerHTML = "";

  const heading = document.createElement("h3");
  heading.textContent = "All Sunset Images";
  container.appendChild(heading);

  if (!sunsetData.length) {
    const empty = document.createElement("div");
    empty.className = "empty";
    empty.textContent = "No data available.";
    container.appendChild(empty);
    return;
  }

  const rows = [];
  for (let i = 0; i < sunsetData.length; i += COLUMNS) {
    rows.push(sunsetData.slice(i, i + COLUMNS));
  }

  for (const row of rows) {
    const grid = document.createElement("div");
    grid.className = "gallery-grid";

    let rowHasSelected = false;

    for (const value of row) {
      const card = document.createElement("div");
      card.className = "thumb-card";

      const top = document.createElement("div");
      top.className = "caption-top";
      top.textContent = value.Date;
      card.appendChild(top);

      const img = document.createElement("img");
      img.src = value.Image;
      img.loading = "lazy";
      card.appendChild(img);

      const caption = document.createElement("div");
      caption.className = "caption";
      caption.textContent = `Time: ${value.Time} | Score: ${value.Score.toFixed(1)}%`;
      card.appendChild(caption);

      const viewBtn = document.createElement("button");
      viewBtn.className = "view-all-btn";
      viewBtn.textContent = "View All";
      viewBtn.addEventListener("click", () => {
        gallery.selectedDate = value.Date;
        gallery.selectedIndex = 0;
        renderGallery(container, state);
      });
      card.appendChild(viewBtn);

      grid.appendChild(card);

      if (value.Date === gallery.selectedDate) rowHasSelected = true;
    }

    container.appendChild(grid);

    if (rowHasSelected && gallery.selectedDate) {
      container.appendChild(renderDetail(container, state));
    }
  }
}

function renderDetail(container, state) {
  const gallery = state.gallery;

  const dateImages = state.allData.filter((img) => img.Date === gallery.selectedDate);
  const regular = dateImages
    .filter((img) => !img.Label.toLowerCase().includes("ranked") && !img.Label.toLowerCase().includes("histogram"))
    .sort((a, b) => (a.Time > b.Time ? 1 : -1));
  const special = dateImages.filter(
    (img) => img.Label.toLowerCase().includes("ranked") || img.Label.toLowerCase().includes("histogram")
  );
  const images = [...regular, ...special];

  const wrap = document.createElement("div");
  wrap.className = "detail";

  if (!images.length) return wrap;

  if (gallery.selectedIndex >= images.length) gallery.selectedIndex = 0;
  const current = images[gallery.selectedIndex];

  const header = document.createElement("div");
  header.className = "detail-header";
  const title = document.createElement("h4");
  title.textContent = `${current.Label.slice(3)} - ${gallery.selectedDate}`;
  header.appendChild(title);
  const closeBtn = document.createElement("button");
  closeBtn.className = "btn";
  closeBtn.textContent = "✕ Close";
  closeBtn.addEventListener("click", () => {
    gallery.selectedDate = null;
    renderGallery(container, state);
  });
  header.appendChild(closeBtn);
  wrap.appendChild(header);

  const nav = document.createElement("div");
  nav.className = "detail-nav";
  const prevBtn = document.createElement("button");
  prevBtn.className = "btn";
  prevBtn.textContent = "← Previous";
  prevBtn.disabled = gallery.selectedIndex === 0;
  prevBtn.addEventListener("click", () => {
    gallery.selectedIndex -= 1;
    renderGallery(container, state);
  });
  const info = document.createElement("div");
  info.className = "info";
  info.textContent = `Image ${gallery.selectedIndex + 1} of ${images.length} | Time: ${current.Time} | Score: ${current.Score.toFixed(1)}%`;
  const nextBtn = document.createElement("button");
  nextBtn.className = "btn";
  nextBtn.textContent = "Next →";
  nextBtn.disabled = gallery.selectedIndex >= images.length - 1;
  nextBtn.addEventListener("click", () => {
    gallery.selectedIndex += 1;
    renderGallery(container, state);
  });
  nav.append(prevBtn, info, nextBtn);
  wrap.appendChild(nav);

  const mainImgWrap = document.createElement("div");
  mainImgWrap.className = "detail-main-img";
  const mainImg = document.createElement("img");
  mainImg.src = current.Image;
  mainImgWrap.appendChild(mainImg);
  wrap.appendChild(mainImgWrap);

  const stripHeading = document.createElement("h5");
  stripHeading.textContent = "All images from this date:";
  wrap.appendChild(stripHeading);

  const strip = document.createElement("div");
  strip.className = "thumb-strip";
  images.forEach((img, idx) => {
    const thumb = document.createElement("div");
    thumb.className = "thumb" + (idx === gallery.selectedIndex ? " selected" : "");
    const thumbImg = document.createElement("img");
    thumbImg.src = img.Image;
    thumbImg.loading = "lazy";
    const label = document.createElement("div");
    label.className = "label";
    label.textContent = img.Label.slice(3);
    thumb.append(thumbImg, label);
    thumb.addEventListener("click", () => {
      gallery.selectedIndex = idx;
      renderGallery(container, state);
    });
    strip.appendChild(thumb);
  });
  wrap.appendChild(strip);

  return wrap;
}
