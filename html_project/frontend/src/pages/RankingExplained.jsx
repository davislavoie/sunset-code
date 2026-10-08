// How sunset ranking works + an interactive scorer.
// Public visitors can tweak every parameter but changes stay in their browser;
// only the admin route can save multipliers back to sunset_process.py.

import { useEffect, useMemo, useRef, useState } from "react";
import { loadImageData } from "../hsv.js";
import Img, { SIZES } from "../Img.jsx";
import { COLORS, DEFAULT_COLOR_RANGES, DEFAULT_FORMULA, scoreImage } from "../scoring.js";

const COLOR_ROWS = [
  { color: "red", label: "Red", swatch: "hsl(0, 70%, 50%)" },
  { color: "orange", label: "Orange", swatch: "hsl(20, 70%, 50%)" },
  { color: "yellow", label: "Yellow", swatch: "hsl(30, 70%, 50%)" },
  { color: "pink", label: "Pink/Purple", swatch: "hsl(300, 70%, 50%)" },
];

const toNumber = (value, fallback = 0) => parseFloat(value) || fallback;

export default function RankingExplained({ rankedImages, admin = false }) {
  const [savedMultipliers, setSavedMultipliers] = useState(null);
  const [multipliers, setMultipliers] = useState({ red: 4, orange: 3, yellow: 2, pink: 9 });
  const [colorRanges, setColorRanges] = useState(DEFAULT_COLOR_RANGES);
  const [formulaParams, setFormulaParams] = useState(DEFAULT_FORMULA);
  const [testImages, setTestImages] = useState([]);
  const [pickerOpen, setPickerOpen] = useState(false);
  const [status, setStatus] = useState(null);
  // Inputs are uncontrolled so a half-typed value isn't snapped to 0; bump to re-seed them.
  const [inputsVersion, setInputsVersion] = useState(0);
  const nextId = useRef(0);

  useEffect(() => {
    fetch("/api/scoring-config")
      .then((res) => (res.ok ? res.json() : null))
      .then((config) => {
        if (!config) return;
        setSavedMultipliers(config);
        setMultipliers(config);
        setInputsVersion((v) => v + 1);
      })
      .catch((e) => console.error("Failed to load scoring config:", e));
  }, []);

  const params = useMemo(() => ({ multipliers, colorRanges, formulaParams }), [multipliers, colorRanges, formulaParams]);

  function reset() {
    if (savedMultipliers) setMultipliers(savedMultipliers);
    setColorRanges(DEFAULT_COLOR_RANGES);
    setFormulaParams(DEFAULT_FORMULA);
    setInputsVersion((v) => v + 1);
  }

  async function save() {
    setStatus({ text: "Saving..." });
    try {
      const res = await fetch("/api/admin/scoring-config", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(multipliers),
      });
      if (res.ok) {
        setSavedMultipliers(multipliers);
        setStatus({ text: "Saved! Rebuild to apply.", className: "status-success" });
      } else {
        const err = await res.json();
        setStatus({ text: err.error || "Save failed", className: "status-error" });
      }
    } catch (e) {
      setStatus({ text: "Error: " + e.message, className: "status-error" });
    }
  }

  async function addTestImage(url, name) {
    const id = nextId.current++;
    setTestImages((list) => [...list, { id, name, image: null, error: null }]);
    const update = (fields) =>
      setTestImages((list) => list.map((t) => (t.id === id ? { ...t, ...fields } : t)));
    try {
      update({ image: await loadImageData(url) });
    } catch (e) {
      update({ error: e.message });
    }
  }

  const setRange = (color, param, value) =>
    setColorRanges((ranges) => ({ ...ranges, [color]: { ...ranges[color], [param]: toNumber(value) } }));

  return (
    <>
      <h2>How Sunset Ranking Works</h2>
      <p>Each sunset image is scored from 0-100 based on the colors detected in the sky portion of the image.</p>
      <hr />

      <section key={inputsVersion}>
        <h3>Color Detection &amp; Multipliers</h3>
        <p>
          The algorithm analyzes the <strong>top half</strong> of each image (the sky) and identifies pixels in
          specific hue ranges:
        </p>

        <table className="info-table multiplier-table">
          <thead>
            <tr>
              <th>Color</th>
              <th>Hue Min</th>
              <th>Hue Max</th>
              <th>Min Sat</th>
              <th>Multiplier</th>
            </tr>
          </thead>
          <tbody>
            {COLOR_ROWS.map(({ color, label, swatch }) => (
              <tr key={color}>
                <td>
                  <span className="color-swatch" style={{ background: swatch }}></span> {label}
                </td>
                {["hueMin", "hueMax", "satMin"].map((param) => (
                  <td key={param}>
                    <input
                      type="number"
                      className="param-input-small"
                      defaultValue={colorRanges[color][param]}
                      onChange={(e) => setRange(color, param, e.target.value)}
                    />
                  </td>
                ))}
                <td>
                  <input
                    type="number"
                    className="param-input"
                    step="0.5"
                    defaultValue={multipliers[color]}
                    onChange={(e) => setMultipliers((m) => ({ ...m, [color]: toNumber(e.target.value) }))}
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        <div className="multiplier-actions">
          {admin && (
            <button className="btn btn-primary" onClick={save}>
              Save to Python
            </button>
          )}
          <button className="btn" onClick={reset}>
            Reset
          </button>
          {admin ? (
            status && <span className={status.className}>{status.text}</span>
          ) : (
            <span>Try your own values. Changes only affect this page.</span>
          )}
        </div>

        <h3>Score Calculation</h3>
        <p>For each color, a weighted score is calculated:</p>

        <div className="formula-box editable-formula">
          <code>
            color_score = (pixel_ratio × avg_saturation
            <sup>
              <input
                type="number"
                className="param-input-small"
                step="0.1"
                defaultValue={formulaParams.power}
                onChange={(e) => setFormulaParams((f) => ({ ...f, power: toNumber(e.target.value, 2.0) }))}
              />
            </sup>
            ) /{" "}
            <input
              type="number"
              className="param-input-small"
              step="1"
              defaultValue={formulaParams.divisor}
              onChange={(e) => setFormulaParams((f) => ({ ...f, divisor: toNumber(e.target.value, 40) }))}
            />
          </code>
        </div>
      </section>

      <p>Where:</p>
      <ul>
        <li><strong>pixel_ratio</strong> = matching pixels / total pixels in image</li>
        <li><strong>avg_saturation</strong> = average saturation (0-255) of matching pixels</li>
        <li><strong>power</strong> = exponent to reward vibrant colors (higher = more exponential)</li>
        <li><strong>divisor</strong> = normalizing factor</li>
      </ul>

      <div className="formula-box">
        <code>
          final_score = (red × {multipliers.red}) + (orange × {multipliers.orange}) + (yellow × {multipliers.yellow}) +
          (pink × {multipliers.pink})
        </code>
      </div>

      <p>The final score is capped at <strong>100</strong>.</p>

      <hr />

      <section>
        <h3>Test Scoring</h3>
        <p>
          Add images to see how they score with the current multipliers. Scores update in real-time as you adjust
          the values above.
        </p>
        <div className="image-source-controls">
          <button className="btn" onClick={() => setPickerOpen(true)}>
            Add from Gallery
          </button>
          <label className="btn">
            Upload Image
            <input
              type="file"
              accept="image/*"
              hidden
              onChange={(e) => {
                const file = e.target.files[0];
                if (file) addTestImage(URL.createObjectURL(file), file.name);
                e.target.value = "";
              }}
            />
          </label>
        </div>
        <div className="test-images-grid">
          {testImages.map((entry) => (
            <TestImageCard
              key={entry.id}
              entry={entry}
              params={params}
              onRemove={() => setTestImages((list) => list.filter((t) => t.id !== entry.id))}
            />
          ))}
        </div>
      </section>

      {pickerOpen && (
        <GalleryPicker
          rankedImages={rankedImages}
          onPick={(img) => {
            const url = img["Raw Image"] || img["Ranked Image"];
            addTestImage(`/api/image-proxy?url=${encodeURIComponent(url)}`, img.Date);
          }}
          onClose={() => setPickerOpen(false)}
        />
      )}

      <hr />

      <section>
        <h3>Why These Multipliers?</h3>
        <table className="info-table">
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
      </section>
    </>
  );
}

function TestImageCard({ entry, params, onRemove }) {
  const originalRef = useRef(null);
  const overlayRef = useRef(null);
  const { image } = entry;
  const result = useMemo(() => image && scoreImage(image, params), [image, params]);

  useEffect(() => {
    if (!image) return;
    for (const canvas of [originalRef.current, overlayRef.current]) {
      canvas.width = image.width;
      canvas.height = image.height;
    }
    originalRef.current.getContext("2d").putImageData(image, 0, 0);
  }, [image]);

  useEffect(() => {
    if (!result) return;
    overlayRef.current
      .getContext("2d")
      .putImageData(new ImageData(result.overlay, image.width, image.height), 0, 0);
  }, [result, image]);

  return (
    <div className="test-image-card">
      <div className="test-image-header">
        <span>{entry.name}</span>
        <button className="btn btn-small btn-delete" onClick={onRemove}>
          X
        </button>
      </div>
      <div className="test-image-views">
        <div className="test-image-container">
          <div className="view-label">Original</div>
          <canvas className="test-canvas" ref={originalRef}></canvas>
          {!image && <div className="test-image-loading">{entry.error || "Loading..."}</div>}
        </div>
        <div className="test-image-container">
          <div className="view-label">Overlay</div>
          <canvas className="test-canvas" ref={overlayRef}></canvas>
        </div>
      </div>
      <div className="test-image-scores">
        <div className="score-breakdown">
          {COLORS.map((color) => (
            <span key={color} className={`color-score ${color}-score`}>
              {color[0].toUpperCase() + color.slice(1)}: {result ? result.perColor[color].toFixed(2) : "--"}
            </span>
          ))}
        </div>
        <div className="total-score">
          Score: <strong>{result ? result.total.toFixed(2) + "%" : "--"}</strong>
        </div>
      </div>
    </div>
  );
}

function GalleryPicker({ rankedImages, onPick, onClose }) {
  const [picked, setPicked] = useState(new Set());

  return (
    <div className="edit-modal" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="edit-modal-content" style={{ maxWidth: 800 }}>
        <h3>Select Images from Gallery</h3>
        <div className="gallery-picker-grid">
          {rankedImages.length === 0 && <div className="empty">No images available</div>}
          {rankedImages.slice(0, 30).map((img, i) => (
            <div
              key={i}
              className={`gallery-picker-item${picked.has(i) ? " selected" : ""}`}
              onClick={() => {
                onPick(img);
                setPicked((s) => new Set(s).add(i));
              }}
            >
              <Img src={img["Raw Image"] || img["Ranked Image"]} alt="" loading="lazy" {...SIZES.photo} />
              <div className="picker-label">{img.Date}</div>
            </div>
          ))}
        </div>
        <div className="form-actions">
          <button className="btn btn-primary" onClick={onClose}>
            Done
          </button>
          <button className="btn" onClick={onClose}>
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}
