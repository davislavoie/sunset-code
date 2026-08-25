// Documentation page explaining how sunset ranking works + interactive scorer

let multipliers = { red: 4, orange: 3, yellow: 2, pink: 9 };
let formulaParams = { power: 2.0, divisor: 40 };
let testImages = []; // {url, name, card, imageData, scores}

export async function renderRankingExplained(container, state) {
  container.innerHTML = "";

  const title = document.createElement("h2");
  title.textContent = "How Sunset Ranking Works";
  container.appendChild(title);

  const intro = document.createElement("p");
  intro.textContent = "Each sunset image is scored from 0-100 based on the colors detected in the sky portion of the image.";
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

  // Color Detection Section with live multipliers
  const colorSection = document.createElement("section");
  colorSection.innerHTML = `
    <h3>Color Detection & Multipliers</h3>
    <p>The algorithm analyzes the <strong>top half</strong> of each image (the sky) and identifies pixels in specific hue ranges:</p>

    <table class="info-table multiplier-table">
      <thead>
        <tr>
          <th>Color</th>
          <th>Hue Range</th>
          <th>Min Sat</th>
          <th>Multiplier</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td><span class="color-swatch" style="background: hsl(0, 70%, 50%)"></span> Red</td>
          <td>0 - 8</td>
          <td>20</td>
          <td><input type="number" id="mult-red" class="param-input" step="0.5" value="${multipliers.red}"></td>
        </tr>
        <tr>
          <td><span class="color-swatch" style="background: hsl(20, 70%, 50%)"></span> Orange</td>
          <td>8 - 25</td>
          <td>20</td>
          <td><input type="number" id="mult-orange" class="param-input" step="0.5" value="${multipliers.orange}"></td>
        </tr>
        <tr>
          <td><span class="color-swatch" style="background: hsl(30, 70%, 50%)"></span> Yellow</td>
          <td>25 - 35</td>
          <td>20</td>
          <td><input type="number" id="mult-yellow" class="param-input" step="0.5" value="${multipliers.yellow}"></td>
        </tr>
        <tr>
          <td><span class="color-swatch" style="background: hsl(300, 70%, 50%)"></span> Pink/Purple</td>
          <td>140 - 179</td>
          <td>20</td>
          <td><input type="number" id="mult-pink" class="param-input" step="0.5" value="${multipliers.pink}"></td>
        </tr>
      </tbody>
    </table>

    <div class="multiplier-actions">
      <button id="save-multipliers" class="btn btn-primary">Save to Python</button>
      <button id="reset-multipliers" class="btn">Reset</button>
      <span id="mult-status"></span>
    </div>
  `;
  container.appendChild(colorSection);

  // Score Calculation Section
  const scoreSection = document.createElement("section");
  scoreSection.innerHTML = `
    <h3>Score Calculation</h3>
    <p>For each color, a weighted score is calculated:</p>

    <div class="formula-box editable-formula">
      <code>color_score = (pixel_ratio × avg_saturation<sup><input type="number" id="param-power" class="param-input-small" step="0.1" value="${formulaParams.power}"></sup>) / <input type="number" id="param-divisor" class="param-input-small" step="1" value="${formulaParams.divisor}"></code>
    </div>

    <p>Where:</p>
    <ul>
      <li><strong>pixel_ratio</strong> = matching pixels / total pixels in image</li>
      <li><strong>avg_saturation</strong> = average saturation (0-255) of matching pixels</li>
      <li><strong>power</strong> = exponent to reward vibrant colors (higher = more exponential)</li>
      <li><strong>divisor</strong> = normalizing factor</li>
    </ul>

    <div class="formula-box" id="formula-display">
      <code>final_score = (red × <span id="formula-red">${multipliers.red}</span>) + (orange × <span id="formula-orange">${multipliers.orange}</span>) + (yellow × <span id="formula-yellow">${multipliers.yellow}</span>) + (pink × <span id="formula-pink">${multipliers.pink}</span>)</code>
    </div>

    <p>The final score is capped at <strong>100</strong>.</p>
  `;
  container.appendChild(scoreSection);

  container.appendChild(document.createElement("hr"));

  // Interactive Test Section
  const testSection = document.createElement("section");
  testSection.innerHTML = `
    <h3>Test Scoring</h3>
    <p>Add images to see how they score with the current multipliers. Scores update in real-time as you adjust sliders.</p>
    <div class="image-source-controls">
      <button id="add-from-gallery" class="btn">Add from Gallery</button>
      <label class="btn">
        Upload Image
        <input type="file" id="upload-image" accept="image/*" hidden>
      </label>
    </div>
    <div id="test-images-grid" class="test-images-grid"></div>
  `;
  container.appendChild(testSection);

  // Gallery picker modal
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

  container.appendChild(document.createElement("hr"));

  // Why These Multipliers Section
  const whySection = document.createElement("section");
  whySection.innerHTML = `
    <h3>Why These Multipliers?</h3>
    <table class="info-table">
      <tbody>
        <tr>
          <td><strong>Pink/Purple (9x)</strong></td>
          <td>Rare and visually striking. Only appears in exceptional sunsets with specific atmospheric conditions.</td>
        </tr>
        <tr>
          <td><strong>Red (4x)</strong></td>
          <td>Deep reds indicate intense light scattering, typically seen at peak sunset moments.</td>
        </tr>
        <tr>
          <td><strong>Orange (3x)</strong></td>
          <td>Common in good sunsets but less dramatic than reds.</td>
        </tr>
        <tr>
          <td><strong>Yellow (2x)</strong></td>
          <td>Often present but can indicate earlier/later timing or less atmospheric drama.</td>
        </tr>
      </tbody>
    </table>
  `;
  container.appendChild(whySection);

  // Event handlers for multiplier inputs
  ["red", "orange", "yellow", "pink"].forEach((color) => {
    const input = document.getElementById(`mult-${color}`);
    const formulaSpan = document.getElementById(`formula-${color}`);
    input.addEventListener("input", () => {
      multipliers[color] = parseFloat(input.value) || 0;
      formulaSpan.textContent = input.value;
      recalculateAllScores();
    });
  });

  // Event handlers for formula parameters
  document.getElementById("param-power").addEventListener("input", (e) => {
    formulaParams.power = parseFloat(e.target.value) || 2.0;
    recalculateAllScores();
  });
  document.getElementById("param-divisor").addEventListener("input", (e) => {
    formulaParams.divisor = parseFloat(e.target.value) || 40;
    recalculateAllScores();
  });

  // Save multipliers
  document.getElementById("save-multipliers").addEventListener("click", async () => {
    const status = document.getElementById("mult-status");
    status.textContent = "Saving...";
    status.className = "";
    try {
      const res = await fetch("/api/scoring-config", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(multipliers),
      });
      if (res.ok) {
        status.textContent = "Saved! Rebuild to apply.";
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
          document.getElementById(`formula-${color}`).textContent = multipliers[color];
        });
        // Reset formula params to defaults
        formulaParams = { power: 2.0, divisor: 40 };
        document.getElementById("param-power").value = 2.0;
        document.getElementById("param-divisor").value = 40;
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

  // Clear test images when leaving page
  testImages = [];
}

function showGalleryPicker(state) {
  const modal = document.getElementById("gallery-picker-modal");
  const grid = document.getElementById("gallery-picker-images");
  modal.style.display = "flex";

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
    <div class="test-image-views">
      <div class="test-image-container">
        <div class="view-label">Original</div>
        <canvas class="test-canvas original-canvas"></canvas>
        <div class="test-image-loading">Loading...</div>
      </div>
      <div class="test-image-container">
        <div class="view-label">Overlay</div>
        <canvas class="test-canvas overlay-canvas"></canvas>
      </div>
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

  const originalCanvas = card.querySelector(".original-canvas");
  const overlayCanvas = card.querySelector(".overlay-canvas");
  const loadingDiv = card.querySelector(".test-image-loading");
  const originalCtx = originalCanvas.getContext("2d");

  const img = new Image();
  img.crossOrigin = "anonymous";
  img.onload = () => {
    originalCanvas.width = img.width;
    originalCanvas.height = img.height;
    overlayCanvas.width = img.width;
    overlayCanvas.height = img.height;
    originalCtx.drawImage(img, 0, 0);
    loadingDiv.style.display = "none";

    const imageData = originalCtx.getImageData(0, 0, originalCanvas.width, originalCanvas.height);
    const entry = { url, name, card, imageData, originalCanvas, overlayCanvas };
    testImages.push(entry);
    calculateScore(entry);
  };
  img.onerror = () => {
    loadingDiv.textContent = "Failed to load";
  };
  img.src = url;

  card.querySelector(".remove-image").addEventListener("click", () => {
    testImages = testImages.filter((t) => t.card !== card);
    card.remove();
  });
}

function calculateScore(entry) {
  const { imageData, card, overlayCanvas } = entry;
  const data = imageData.data;
  const width = imageData.width;
  const height = imageData.height;

  const skyHeight = Math.floor(height / 2);
  const totalPixels = width * height;

  // Create overlay image data
  const overlayData = new Uint8ClampedArray(data.length);
  for (let i = 0; i < data.length; i++) overlayData[i] = data[i];

  let redCount = 0, orangeCount = 0, yellowCount = 0, pinkCount = 0;
  let redSatSum = 0, orangeSatSum = 0, yellowSatSum = 0, pinkSatSum = 0;

  const opacity = 0.5;

  for (let y = 0; y < skyHeight; y++) {
    for (let x = 0; x < width; x++) {
      const i = (y * width + x) * 4;
      const r = data[i], g = data[i + 1], b = data[i + 2];
      const [h, s, v] = rgbToHsv(r, g, b);
      const hue = h * 180;
      const sat = s * 255;

      if (sat < 20) continue;

      let overlayColor = null;

      if (hue < 8) {
        redCount++; redSatSum += sat;
        overlayColor = [255, 0, 0]; // Red overlay
      } else if (hue >= 8 && hue < 25) {
        orangeCount++; orangeSatSum += sat;
        overlayColor = [255, 140, 0]; // Orange overlay
      } else if (hue >= 25 && hue <= 35) {
        yellowCount++; yellowSatSum += sat;
        overlayColor = [255, 255, 0]; // Yellow overlay
      } else if (hue >= 140 && hue <= 179) {
        pinkCount++; pinkSatSum += sat;
        overlayColor = [255, 0, 255]; // Pink overlay
      }

      if (overlayColor) {
        overlayData[i] = Math.round(opacity * overlayColor[0] + (1 - opacity) * data[i]);
        overlayData[i + 1] = Math.round(opacity * overlayColor[1] + (1 - opacity) * data[i + 1]);
        overlayData[i + 2] = Math.round(opacity * overlayColor[2] + (1 - opacity) * data[i + 2]);
      }
    }
  }

  // Draw overlay
  const overlayCtx = overlayCanvas.getContext("2d");
  const overlayImageData = new ImageData(overlayData, width, height);
  overlayCtx.putImageData(overlayImageData, 0, 0);

  const { power, divisor } = formulaParams;
  let redScore = 0, orangeScore = 0, yellowScore = 0, pinkScore = 0;

  if (redCount > 0) {
    redScore = ((redCount / totalPixels) * Math.pow(redSatSum / redCount, power)) / divisor;
  }
  if (orangeCount > 0) {
    orangeScore = ((orangeCount / totalPixels) * Math.pow(orangeSatSum / orangeCount, power)) / divisor;
  }
  if (yellowCount > 0) {
    yellowScore = ((yellowCount / totalPixels) * Math.pow(yellowSatSum / yellowCount, power)) / divisor;
  }
  if (pinkCount > 0) {
    pinkScore = ((pinkCount / totalPixels) * Math.pow(pinkSatSum / pinkCount, power)) / divisor;
  }

  const total = Math.min(100,
    redScore * multipliers.red +
    orangeScore * multipliers.orange +
    yellowScore * multipliers.yellow +
    pinkScore * multipliers.pink
  );

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
