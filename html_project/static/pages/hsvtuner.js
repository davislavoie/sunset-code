// Mirrors streamlit_project/hsv_tuner.py

import { drawResized, maskCanvas, loadImage } from "../hsv.js";

const MAX_WIDTH = 800;

export function renderHsvTuner(container, state) {
  if (!state.hsvtuner) {
    state.hsvtuner = {
      h_min: 0, h_max: 179,
      s_min: 0, s_max: 255,
      v_min: 0, v_max: 255,
      galleryUrl: null,
      galleryImg: null,
      uploadImg: null,
    };
  }
  const t = state.hsvtuner;

  container.innerHTML = "";

  const title = document.createElement("h2");
  title.textContent = "HSV Mask Tuner for Sunset Analysis";
  container.appendChild(title);

  const layout = document.createElement("div");
  layout.className = "hsv-layout";
  container.appendChild(layout);

  // --- Sliders ---
  const sliderCol = document.createElement("div");
  sliderCol.className = "hsv-sliders";
  sliderCol.innerHTML = `<h4>HSV Range Controls</h4>`;

  const sliderRefs = {};
  const pairs = [
    ["Hue Min", "h_min", 0, 179], ["Hue Max", "h_max", 0, 179],
    ["Sat Min", "s_min", 0, 255], ["Sat Max", "s_max", 0, 255],
    ["Val Min", "v_min", 0, 255], ["Val Max", "v_max", 0, 255],
  ];
  for (let i = 0; i < pairs.length; i += 2) {
    const row = document.createElement("div");
    row.className = "slider-pair";
    for (const [label, key, min, max] of [pairs[i], pairs[i + 1]]) {
      const cell = document.createElement("div");
      const lab = document.createElement("label");
      lab.textContent = `${label}: ${t[key]}`;
      const input = document.createElement("input");
      input.type = "range";
      input.min = min;
      input.max = max;
      input.value = t[key];
      input.addEventListener("input", () => {
        t[key] = Number(input.value);
        lab.textContent = `${label}: ${t[key]}`;
        updateAll();
      });
      sliderRefs[key] = input;
      cell.append(lab, input);
      row.appendChild(cell);
    }
    sliderCol.appendChild(row);
  }
  layout.appendChild(sliderCol);

  // --- Reference images ---
  const refCol = document.createElement("div");
  refCol.className = "hsv-ref";
  refCol.innerHTML = `<h4>Fixed Reference Images</h4>`;
  const refImages = document.createElement("div");
  refImages.className = "ref-images";
  refCol.appendChild(refImages);
  layout.appendChild(refCol);

  const refCanvases = [];
  const refSources = [
    { src: "stock_images/color_wheel.jpg", caption: "Color Wheel" },
    { src: "stock_images/hsv_cone.jpg", caption: "HSV Cone" },
  ];
  for (const { src, caption } of refSources) {
    const fig = document.createElement("figure");
    const canvas = document.createElement("canvas");
    const figcaption = document.createElement("figcaption");
    figcaption.textContent = caption;
    fig.append(canvas, figcaption);
    refImages.appendChild(fig);

    const sourceCanvas = document.createElement("canvas");
    loadImage(src).then((img) => {
      drawResized(img, sourceCanvas, null);
      refCanvases.push({ sourceCanvas, destCanvas: canvas });
      remaskOne(sourceCanvas, canvas);
    });
  }

  container.appendChild(document.createElement("hr"));

  // --- Gallery loader ---
  const galleryHeading = document.createElement("h4");
  galleryHeading.textContent = "Load Image from Gallery";
  container.appendChild(galleryHeading);

  const loaderRow = document.createElement("div");
  loaderRow.className = "gallery-loader";
  const gallerySelect = document.createElement("select");
  const noneOpt = document.createElement("option");
  noneOpt.value = "";
  noneOpt.textContent = "None";
  gallerySelect.appendChild(noneOpt);

  const options = (state.allData || []).map((item) => {
    const displayLabel = /^(07_|11_|12_)/.test(item.Label) ? item.Label.slice(3) : item.Label;
    return { url: item.Image, text: `${item.Date} ${item.Time} - ${displayLabel} (Score: ${item.Score.toFixed(1)}%)` };
  });
  for (const opt of options) {
    const o = document.createElement("option");
    o.value = opt.url;
    o.textContent = opt.text;
    gallerySelect.appendChild(o);
  }
  if (t.galleryUrl) gallerySelect.value = t.galleryUrl;

  const loadBtn = document.createElement("button");
  loadBtn.className = "btn";
  loadBtn.textContent = "Load Image";
  const clearBtn = document.createElement("button");
  clearBtn.className = "btn";
  clearBtn.textContent = "Clear";
  clearBtn.disabled = !t.galleryUrl;

  loaderRow.append(gallerySelect, loadBtn, clearBtn);
  container.appendChild(loaderRow);

  const galleryStatus = document.createElement("div");
  galleryStatus.style.color = "var(--muted)";
  galleryStatus.style.margin = "4px 0 12px";
  container.appendChild(galleryStatus);

  const gallerySourceCanvas = document.createElement("canvas");
  const galleryPane = document.createElement("div");
  container.appendChild(galleryPane);

  loadBtn.addEventListener("click", async () => {
    const url = gallerySelect.value;
    if (!url) return;
    t.galleryUrl = url;
    galleryStatus.textContent = "Loading image from gallery…";
    try {
      const img = await loadImage(`/api/image-proxy?url=${encodeURIComponent(url)}`);
      drawResized(img, gallerySourceCanvas, MAX_WIDTH);
      t.galleryImg = gallerySourceCanvas;
      galleryStatus.textContent = "";
      clearBtn.disabled = false;
      renderSideBySide(galleryPane, "Gallery Image", gallerySourceCanvas, updateAll);
    } catch (e) {
      galleryStatus.textContent = `Error loading image: ${e}`;
    }
  });

  clearBtn.addEventListener("click", () => {
    t.galleryUrl = null;
    t.galleryImg = null;
    galleryPane.innerHTML = "";
    clearBtn.disabled = true;
  });

  if (t.galleryImg) {
    renderSideBySide(galleryPane, "Gallery Image", t.galleryImg, updateAll);
  }

  container.appendChild(document.createElement("hr"));

  // --- Upload ---
  const uploadHeading = document.createElement("h4");
  uploadHeading.textContent = "Upload Your Own Image";
  container.appendChild(uploadHeading);
  const uploadInput = document.createElement("input");
  uploadInput.type = "file";
  uploadInput.accept = "image/jpeg,image/png";
  container.appendChild(uploadInput);

  const uploadPane = document.createElement("div");
  container.appendChild(uploadPane);
  const uploadSourceCanvas = document.createElement("canvas");

  uploadInput.addEventListener("change", async () => {
    const file = uploadInput.files[0];
    if (!file) return;
    const img = await loadImage(URL.createObjectURL(file));
    drawResized(img, uploadSourceCanvas, MAX_WIDTH);
    t.uploadImg = uploadSourceCanvas;
    renderSideBySide(uploadPane, "Uploaded Image", uploadSourceCanvas, updateAll);
  });

  if (t.uploadImg) {
    renderSideBySide(uploadPane, "Uploaded Image", t.uploadImg, updateAll);
  }

  // --- Mask refresh ---
  function remaskOne(sourceCanvas, destCanvas) {
    maskCanvas(sourceCanvas, destCanvas, t.h_min, t.h_max, t.s_min, t.s_max, t.v_min, t.v_max);
  }

  function updateAll() {
    for (const { sourceCanvas, destCanvas } of refCanvases) {
      remaskOne(sourceCanvas, destCanvas);
    }
    const galleryDest = galleryPane.querySelector("canvas.masked");
    if (galleryDest && t.galleryImg) remaskOne(t.galleryImg, galleryDest);
    const uploadDest = uploadPane.querySelector("canvas.masked");
    if (uploadDest && t.uploadImg) remaskOne(t.uploadImg, uploadDest);
  }
}

function renderSideBySide(pane, label, sourceCanvas, onReady) {
  pane.innerHTML = "";
  const wrap = document.createElement("div");
  wrap.className = "side-by-side";

  const origFig = document.createElement("figure");
  const origCanvas = document.createElement("canvas");
  origCanvas.width = sourceCanvas.width;
  origCanvas.height = sourceCanvas.height;
  origCanvas.getContext("2d").drawImage(sourceCanvas, 0, 0);
  const origCaption = document.createElement("figcaption");
  origCaption.textContent = `${label} (Original)`;
  origFig.append(origCanvas, origCaption);

  const maskFig = document.createElement("figure");
  const maskCanvasEl = document.createElement("canvas");
  maskCanvasEl.className = "masked";
  const maskCaption = document.createElement("figcaption");
  maskCaption.textContent = `${label} (Masked)`;
  maskFig.append(maskCanvasEl, maskCaption);

  wrap.append(origFig, maskFig);
  pane.appendChild(wrap);

  onReady();
}
