// Documentation page explaining how sunset ranking works

export function renderRankingExplained(container) {
  container.innerHTML = "";

  const title = document.createElement("h2");
  title.textContent = "How Sunset Ranking Works";
  container.appendChild(title);

  const intro = document.createElement("p");
  intro.textContent = "Each sunset image is scored from 0-100 based on the colors detected in the sky portion of the image.";
  container.appendChild(intro);

  container.appendChild(document.createElement("hr"));

  // Color Detection Section
  const colorSection = document.createElement("section");
  colorSection.innerHTML = `
    <h3>Color Detection</h3>
    <p>The algorithm analyzes the <strong>top half</strong> of each image (the sky) and identifies pixels in specific hue ranges using HSV color space:</p>

    <table class="info-table">
      <thead>
        <tr>
          <th>Color</th>
          <th>Hue Range</th>
          <th>Min Saturation</th>
          <th>Multiplier</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td><span class="color-swatch" style="background: hsl(0, 70%, 50%)"></span> Red</td>
          <td>0 - 8</td>
          <td>20</td>
          <td><strong>4x</strong></td>
        </tr>
        <tr>
          <td><span class="color-swatch" style="background: hsl(20, 70%, 50%)"></span> Orange</td>
          <td>8 - 25</td>
          <td>20</td>
          <td><strong>3x</strong></td>
        </tr>
        <tr>
          <td><span class="color-swatch" style="background: hsl(30, 70%, 50%)"></span> Yellow</td>
          <td>25 - 35</td>
          <td>20</td>
          <td><strong>2x</strong></td>
        </tr>
        <tr>
          <td><span class="color-swatch" style="background: hsl(300, 70%, 50%)"></span> Pink/Purple</td>
          <td>140 - 179</td>
          <td>20</td>
          <td><strong>9x</strong></td>
        </tr>
      </tbody>
    </table>
  `;
  container.appendChild(colorSection);

  // Score Calculation Section
  const scoreSection = document.createElement("section");
  scoreSection.innerHTML = `
    <h3>Score Calculation</h3>
    <p>For each color, a weighted score is calculated:</p>

    <div class="formula-box">
      <code>color_score = (pixel_ratio × avg_saturation²) / 40</code>
    </div>

    <p>Where:</p>
    <ul>
      <li><strong>pixel_ratio</strong> = matching pixels / total pixels in image</li>
      <li><strong>avg_saturation</strong> = average saturation (0-255) of matching pixels</li>
      <li>Saturation is squared to reward vibrant colors exponentially</li>
    </ul>

    <h4>Final Score Formula</h4>
    <div class="formula-box">
      <code>final_score = (red × 4) + (orange × 3) + (yellow × 2) + (pink × 9)</code>
    </div>

    <p>The final score is capped at <strong>100</strong>.</p>
  `;
  container.appendChild(scoreSection);

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

  // Overlay Colors Section
  const overlaySection = document.createElement("section");
  overlaySection.innerHTML = `
    <h3>Ranked Image Overlays</h3>
    <p>The ranked images show colored overlays indicating which pixels were detected:</p>
    <table class="info-table">
      <tbody>
        <tr>
          <td><span class="color-swatch" style="background: rgb(255, 0, 0)"></span></td>
          <td>Warm pixels (high saturation red/orange)</td>
        </tr>
        <tr>
          <td><span class="color-swatch" style="background: rgb(255, 165, 0)"></span></td>
          <td>Warm dull pixels (lower saturation warm tones)</td>
        </tr>
        <tr>
          <td><span class="color-swatch" style="background: rgb(255, 0, 255)"></span></td>
          <td>Pink/purple pixels</td>
        </tr>
        <tr>
          <td><span class="color-swatch" style="background: rgb(220, 130, 150)"></span></td>
          <td>Pink dull pixels (lower saturation)</td>
        </tr>
        <tr>
          <td><span class="color-swatch" style="background: rgb(255, 255, 0)"></span></td>
          <td>Yellow pixels</td>
        </tr>
        <tr>
          <td><span class="color-swatch" style="background: rgb(0, 0, 255)"></span></td>
          <td>Dark blue pixels (cloud contrast)</td>
        </tr>
      </tbody>
    </table>
  `;
  container.appendChild(overlaySection);

  // Future Section
  const futureSection = document.createElement("section");
  futureSection.innerHTML = `
    <h3>Coming Soon</h3>
    <ul>
      <li>Adjustable multipliers from this page</li>
      <li>Re-rank command to recalculate scores with new settings</li>
      <li>Custom color range definitions</li>
    </ul>
  `;
  container.appendChild(futureSection);
}
