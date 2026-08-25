// Interactive sunset scorer - real-time scoring with adjustable multipliers

import { loadImageIntoTuner } from "./hsvtuner.js";

let multipliers = { red: 4, orange: 3, yellow: 2, pink: 9 };
let testImages = []; // {url, name, canvas, scores}

export async function renderScorer(container, state) {
  container.innerHTML = "";

  const title = document.createElement("h2");
  title.textContent = "Interactive Scorer";
  container.appendChild(title);

  const intro = document.createElement("p");
  intro.textContent = "Adjust scoring multipliers and test on images in real-time.";
  container.appendChild(intro);

  container.appendChild(document.createElement("hr"));

  // Load current multipliers from backend
  try {
    const res = await fetch("/api/scoring-config");
    if (res.ok) {
      multipliers = await res.json();
    }
  } catch (e) {
    console.error("Failed to load scoring config:", e);
  }

  // Multipliers section
  const multipliersSection = document.createElement("section");
  multipliersSection.innerHTML = `
    <h3>Color Multipliers</h3>
    <div class="multiplier-controls">
      <div class="multiplier-row">
        <label>
          <span class="color-dot" style="background: #ff3333;"></span>
          Red
          <input type="range" id="mult-red" min="0" max="20" step="0.5" value="${multipliers.red}">
          <span class="mult-value" id="val-red">${multipliers.red}</span>
        </label>
      </div>
      <div class="multiplier-row">
        <label>
          <span class="color-dot" style="background: #ff8800;"></span>
          Orange
          <input type="range" id="mult-orange" min="0" max="20" step="0.5" value="${multipliers.orange}">
          <span class="mult-value" id="val-orange">${multipliers.orange}</span>
        </label>
      </div>
      <div class="multiplier-row">
        <label>
          <span class="color-dot" style="background: #ffdd00;"></span>
          Yellow
          <input type="range" id="mult-yellow" min="0" max="20" step="0.5" value="${multipliers.yellow}">
          <span class="mult-value" id="val-yellow">${multipliers.yellow}</span>
        </label>
      </div>
      <div class="multiplier-row">
        <label>
          <span class="color-dot" style="background: #ff00ff;"></span>
          Pink/Purple
          <input type="range" id="mult-pink" min="0" max="20" step="0.5" value="${multipliers.pink}">
          <span class="mult-value" id="val-pink">${multipliers.pink}</span>
        </label>
      </div>
    </div>
    <div class="multiplier-actions">
      <button id="save-multipliers" class="btn btn-primary">Save to Python</button>
      <button id="reset-multipliers" class="btn">Reset</button>
      <span id="mult-status"></span>
    </div>
  `;
  container.appendChild(multipliersSection);

  // Image test section
  const imageSection = document.createElement("section");
  imageSection.innerHTML = `
    <h3>Test Images</h3>
    <div class="image-source-controls">
      <button id="add-from-gallery" class="btn">Add from Gallery</button>
      <label class="btn">
        Upload Image
        <input type="file" id="upload-image" accept="image/*" hidden>
      </label>
    </div>
    <div id="test-images-grid" class="test-images-grid"></div>
  `;
  container.appendChild(imageSection);

  // Gallery picker modal (hidden by default)
  const galleryModal = document.createElement("div");
  galleryModal.id = "gallery-picker-modal";
  galleryModal.className = "edit-modal";
  galleryModal.style.display = "none";
  galleryModal.innerHTML = `
    <div class="edit-modal-content" style="max-width: 800px;">
      <h3>Select Images from Gallery</h3>
      <div id="gallery-picker-images" class="gallery-picker-grid"></div>
      <div class="form-actions">
        <button id="gallery-picker-done" class="btn btn-primary">Done</button>
        <button id="gallery-picker-cancel" class="btn">Cancel</button>
      </div>
    </div>
  `;
  container.appendChild(galleryModal);

  // Event handlers for multiplier sliders
  ["red", "orange", "yellow", "pink"].forEach((color) => {
    const slider = document.getElementById(`mult-${color}`);
    const valueSpan = document.getElementById(`val-${color}`);
    slider.addEventListener("input", () => {
      multipliers[color] = parseFloat(slider.value);
      valueSpan.textContent = slider.value;
      recalculateAllScores();
    });
  });

  // Save multipliers
  document.getElementById("save-multipliers").addEventListener("click", async () => {
    const status = document.getElementById("mult-status");
    status.textContent = "Saving...";
    try {
      const res = await fetch("/api/scoring-config", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(multipliers),
      });
      if (res.ok) {
        status.textContent = "Saved! Rebuild containers to apply.";
        status.className = "status-success";
      } else {
        const err = await res.json();
        status.textContent = err.error || "Save failed";
        status.className = "status-error";
      }
    } catch (e) {
      status.textContent = "Error: " + e.message;
      status.className = "status-error";
    }
  });

  // Reset multipliers
  document.getElementById("reset-multipliers").addEventListener("click", async () => {
    try {
      const res = await fetch("/api/scoring-config");
      if (res.ok) {
        multipliers = await res.json();
        ["red", "orange", "yellow", "pink"].forEach((color) => {
          document.getElementById(`mult-${color}`).value = multipliers[color];
          document.getElementById(`val-${color}`).textContent = multipliers[color];
        });
        recalculateAllScores();
      }
    } catch (e) {
      console.error(e);
    }
  });

  // Upload image
  document.getElementById("upload-image").addEventListener("change", (e) => {
    const file = e.target.files[0];
    if (file) {
      const url = URL.createObjectURL(file);
      addTestImage(url, file.name);
    }
  });

  // Add from gallery
  document.getElementById("add-from-gallery").addEventListener("click", () => {
    showGalleryPicker(state);
  });

  document.getElementById("gallery-picker-cancel").addEventListener("click", () => {
    galleryModal.style.display = "none";
  });

  document.getElementById("gallery-picker-done").addEventListener("click", () => {
    galleryModal.style.display = "none";
  });

  galleryModal.addEventListener("click", (e) => {
    if (e.target === galleryModal) galleryModal.style.display = "none";
  });
}

function showGalleryPicker(state) {
  const modal = document.getElementById("gallery-picker-modal");
  const grid = document.getElementById("gallery-picker-images");
  modal.style.display = "flex";

  // Load ranked images from state
  if (!state.rankedImages || !state.rankedImages.length) {
    grid.innerHTML = '<div class="empty">No images available</div>';
    return;
  }

  grid.innerHTML = "";
  state.rankedImages.slice(0, 30).forEach((img) => {
    const div = document.createElement("div");
    div.className = "gallery-picker-item";
    div.innerHTML = `
      <img src="${img["Raw Image"] || img["Ranked Image"]}" loading="lazy">
      <div class="picker-label">${img.Date}</div>
    `;
    div.addEventListener("click", () => {
      const url = img["Raw Image"] || img["Ranked Image"];
      addTestImage(`/api/image-proxy?url=${encodeURIComponent(url)}`, img.Date);
      div.classList.add("selected");
    });
    grid.appendChild(div);
  });
}

async function addTestImage(url, name) {
  const grid = document.getElementById("test-images-grid");

  const card = document.createElement("div");
  card.className = "test-image-card";
  card.innerHTML = `
    <div class="test-image-header">
      <span>${name}</span>
      <button class="btn btn-small btn-delete remove-image">X</button>
    </div>
    <div class="test-image-container">
      <canvas class="test-canvas"></canvas>
      <div class="test-image-loading">Loading...</div>
    </div>
    <div class="test-image-scores">
      <div class="score-breakdown">
        <span class="color-score red-score">Red: --</span>
        <span class="color-score orange-score">Orange: --</span>
        <span class="color-score yellow-score">Yellow: --</span>
        <span class="color-score pink-score">Pink: --</span>
      </div>
      <div class="total-score">Score: <strong>--</strong></div>
    </div>
  `;

  grid.appendChild(card);

  const canvas = card.querySelector(".test-canvas");
  const loadingDiv = card.querySelector(".test-image-loading");
  const ctx = canvas.getContext("2d");

  // Load image
  const img = new Image();
  img.crossOrigin = "anonymous";
  img.onload = () => {
    canvas.width = img.width;
    canvas.height = img.height;
    ctx.drawImage(img, 0, 0);
    loadingDiv.style.display = "none";

    const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
    const entry = { url, name, card, imageData };
    testImages.push(entry);
    calculateScore(entry);
  };
  img.onerror = () => {
    loadingDiv.textContent = "Failed to load";
  };
  img.src = url;

  // Remove button
  card.querySelector(".remove-image").addEventListener("click", () => {
    testImages = testImages.filter((t) => t.card !== card);
    card.remove();
  });
}

function calculateScore(entry) {
  const { imageData, card } = entry;
  const data = imageData.data;
  const width = imageData.width;
  const height = imageData.height;

  // Only analyze top half (sky)
  const skyHeight = Math.floor(height / 2);
  const totalPixels = width * height;

  let redScore = 0, orangeScore = 0, yellowScore = 0, pinkScore = 0;
  let redCount = 0, orangeCount = 0, yellowCount = 0, pinkCount = 0;
  let redSatSum = 0, orangeSatSum = 0, yellowSatSum = 0, pinkSatSum = 0;

  for (let y = 0; y < skyHeight; y++) {
    for (let x = 0; x < width; x++) {
      const i = (y * width + x) * 4;
      const r = data[i], g = data[i + 1], b = data[i + 2];

      // Convert RGB to HSV
      const [h, s, v] = rgbToHsv(r, g, b);
      const hue = h * 180; // 0-180 like OpenCV
      const sat = s * 255; // 0-255

      if (sat < 20) continue;

      // Red: h < 8
      if (hue < 8) {
        redCount++;
        redSatSum += sat;
      }
      // Orange: 8 <= h < 25
      else if (hue >= 8 && hue < 25) {
        orangeCount++;
        orangeSatSum += sat;
      }
      // Yellow: 25 <= h <= 35
      else if (hue >= 25 && hue <= 35) {
        yellowCount++;
        yellowSatSum += sat;
      }
      // Pink: 140 <= h <= 179
      else if (hue >= 140 && hue <= 179) {
        pinkCount++;
        pinkSatSum += sat;
      }
    }
  }

  // Calculate saturation-weighted scores (matching Python)
  const power = 2.0;
  if (redCount > 0) {
    const avgSat = redSatSum / redCount;
    const ratio = redCount / totalPixels;
    redScore = (ratio * Math.pow(avgSat, power)) / 40;
  }
  if (orangeCount > 0) {
    const avgSat = orangeSatSum / orangeCount;
    const ratio = orangeCount / totalPixels;
    orangeScore = (ratio * Math.pow(avgSat, power)) / 40;
  }
  if (yellowCount > 0) {
    const avgSat = yellowSatSum / yellowCount;
    const ratio = yellowCount / totalPixels;
    yellowScore = (ratio * Math.pow(avgSat, power)) / 40;
  }
  if (pinkCount > 0) {
    const avgSat = pinkSatSum / pinkCount;
    const ratio = pinkCount / totalPixels;
    pinkScore = (ratio * Math.pow(avgSat, power)) / 40;
  }

  // Final score with multipliers
  const total = Math.min(100,
    redScore * multipliers.red +
    orangeScore * multipliers.orange +
    yellowScore * multipliers.yellow +
    pinkScore * multipliers.pink
  );

  // Update display
  card.querySelector(".red-score").textContent = `Red: ${(redScore * multipliers.red).toFixed(2)}`;
  card.querySelector(".orange-score").textContent = `Orange: ${(orangeScore * multipliers.orange).toFixed(2)}`;
  card.querySelector(".yellow-score").textContent = `Yellow: ${(yellowScore * multipliers.yellow).toFixed(2)}`;
  card.querySelector(".pink-score").textContent = `Pink: ${(pinkScore * multipliers.pink).toFixed(2)}`;
  card.querySelector(".total-score strong").textContent = total.toFixed(2) + "%";

  entry.scores = { redScore, orangeScore, yellowScore, pinkScore, total };
}

function recalculateAllScores() {
  testImages.forEach((entry) => calculateScore(entry));
}

function rgbToHsv(r, g, b) {
  r /= 255; g /= 255; b /= 255;
  const max = Math.max(r, g, b), min = Math.min(r, g, b);
  const d = max - min;
  let h = 0, s = max === 0 ? 0 : d / max, v = max;

  if (d !== 0) {
    switch (max) {
      case r: h = ((g - b) / d + (g < b ? 6 : 0)) / 6; break;
      case g: h = ((b - r) / d + 2) / 6; break;
      case b: h = ((r - g) / d + 4) / 6; break;
    }
  }
  return [h, s, v];
}
