// HSV Mask Tuner (mirrors streamlit_project/hsv_tuner.py). Its state lives in
// App so "Load to HSV Tuner" on other pages can add images before navigating here.

import { useEffect, useMemo, useRef, useState } from "react";
import Dropdown from "../Dropdown.jsx";
import RangeSlider from "../RangeSlider.jsx";
import { loadImage, maskCanvas, toResizedCanvas } from "../hsv.js";

export const MAX_WIDTH = 800;

export const INITIAL_TUNER = {
  ranges: { h_min: 0, h_max: 179, s_min: 0, s_max: 255, v_min: 0, v_max: 255 },
  loaded: [], // [{ id, url, canvas }] -- canvas holds the decoded/resized source frame
  upload: null, // canvas
};

/** Fetches a gallery image via the same-origin proxy (so its pixels are readable). */
export async function loadGalleryCanvas(url) {
  const img = await loadImage(`/api/image-proxy?url=${encodeURIComponent(url)}`);
  return toResizedCanvas(img, MAX_WIDTH);
}

// OpenCV's HSV scale: H 0-179 (degrees / 2), S and V 0-255. Each track previews its channel.
const CHANNELS = [
  {
    label: "Hue",
    keys: ["h_min", "h_max"],
    max: 179,
    track: `linear-gradient(to right, ${[0, 60, 120, 180, 240, 300, 358].map((d) => `hsl(${d} 90% 50%)`).join(", ")})`,
  },
  { label: "Saturation", keys: ["s_min", "s_max"], max: 255, track: "linear-gradient(to right, hsl(30 0% 50%), hsl(30 100% 50%))" },
  { label: "Value", keys: ["v_min", "v_max"], max: 255, track: "linear-gradient(to right, #000, hsl(30 100% 60%))" },
];

const REFERENCE_IMAGES = [
  { src: "/stock_images/color_wheel.jpg", caption: "Color Wheel" },
  { src: "/stock_images/hsv_cone.jpg", caption: "HSV Cone" },
];

export default function HsvTuner({ allData, tuner, setTuner, onLoadToHsv }) {
  const { ranges } = tuner;
  const [selectedDate, setSelectedDate] = useState(null);
  const [selectedUrl, setSelectedUrl] = useState(null);

  // 4000+ captures is too many for one list, so pick a day, then a capture from it.
  const dates = useMemo(() => [...new Set(allData.map((item) => item.Date))].sort().reverse(), [allData]);
  const captures = allData
    .filter((item) => item.Date === selectedDate)
    .map((item) => {
      const label = /^(07_|11_|12_)/.test(item.Label) ? item.Label.slice(3) : item.Label;
      return { value: item.Image, label: `${item.Time} - ${label} (Score: ${item.Score.toFixed(1)}%)` };
    });
  const [status, setStatus] = useState("");

  async function loadSelected() {
    if (!selectedUrl) return;
    setStatus("Loading image from gallery…");
    try {
      await onLoadToHsv(selectedUrl, { navigate: false });
      setStatus("");
    } catch (e) {
      setStatus(`Error loading image: ${e}`);
    }
  }

  async function onUpload(e) {
    const file = e.target.files[0];
    if (!file) return;
    const img = await loadImage(URL.createObjectURL(file));
    const canvas = toResizedCanvas(img, MAX_WIDTH);
    setTuner((t) => ({ ...t, upload: canvas }));
  }

  return (
    <>
      <h2>HSV Mask Tuner for Sunset Analysis</h2>

      <div className="hsv-layout">
        <div className="hsv-sliders">
          <h4>HSV Range Controls</h4>
          {CHANNELS.map(({ label, keys: [lo, hi], max, track }) => (
            <RangeSlider
              key={label}
              label={label}
              min={0}
              max={max}
              value={[ranges[lo], ranges[hi]]}
              onChange={([a, b]) => setTuner((t) => ({ ...t, ranges: { ...t.ranges, [lo]: a, [hi]: b } }))}
              trackBackground={track}
            />
          ))}
        </div>

        <div className="hsv-ref">
          <h4>Fixed Reference Images</h4>
          <div className="ref-images">
            {REFERENCE_IMAGES.map(({ src, caption }) => (
              <ReferenceImage key={src} src={src} caption={caption} ranges={ranges} />
            ))}
          </div>
        </div>
      </div>

      <hr />

      <h4>Load Image from Gallery</h4>
      <div className="gallery-loader">
        <Dropdown
          label="Day"
          placeholder="Pick a day…"
          options={dates}
          value={selectedDate}
          onChange={(d) => {
            setSelectedDate(d);
            setSelectedUrl(null);
          }}
        />
        <Dropdown
          label="Capture"
          placeholder={selectedDate ? "Pick a capture…" : "Pick a day first"}
          options={captures}
          value={selectedUrl}
          onChange={setSelectedUrl}
        />
        <button className="btn" onClick={loadSelected}>
          Load Image
        </button>
        <button
          className="btn"
          disabled={!tuner.loaded.length}
          onClick={() => setTuner((t) => ({ ...t, loaded: [] }))}
        >
          Clear All
        </button>
      </div>
      <div style={{ color: "var(--text-muted)", margin: "4px 0 12px" }}>{status}</div>

      <div>
        {tuner.loaded.map((entry, idx) => (
          <SideBySide
            key={entry.id}
            label={`Gallery Image ${idx + 1}`}
            source={entry.canvas}
            ranges={ranges}
            onRemove={() => setTuner((t) => ({ ...t, loaded: t.loaded.filter((l) => l.id !== entry.id) }))}
          />
        ))}
      </div>

      <hr />

      <h4>Upload Your Own Image</h4>
      <input type="file" accept="image/jpeg,image/png" onChange={onUpload} />
      <div>{tuner.upload && <SideBySide label="Uploaded Image" source={tuner.upload} ranges={ranges} />}</div>
    </>
  );
}

/** Canvas showing `source` with the HSV mask applied; re-masks whenever ranges change. */
function MaskedCanvas({ source, ranges }) {
  const ref = useRef(null);
  useEffect(() => {
    if (source) maskCanvas(source, ref.current, ranges);
  }, [source, ranges]);
  return <canvas ref={ref} className="masked" />;
}

function CopyCanvas({ source }) {
  const ref = useRef(null);
  useEffect(() => {
    const canvas = ref.current;
    canvas.width = source.width;
    canvas.height = source.height;
    canvas.getContext("2d").drawImage(source, 0, 0);
  }, [source]);
  return <canvas ref={ref} />;
}

function ReferenceImage({ src, caption, ranges }) {
  const [source, setSource] = useState(null);
  useEffect(() => {
    loadImage(src).then((img) => setSource(toResizedCanvas(img, null)));
  }, [src]);
  return (
    <figure>
      <MaskedCanvas source={source} ranges={ranges} />
      <figcaption>{caption}</figcaption>
    </figure>
  );
}

function SideBySide({ label, source, ranges, onRemove }) {
  return (
    <div className="side-by-side-block">
      {onRemove && (
        <button className="btn remove-loaded-btn" onClick={onRemove}>
          ✕ Remove
        </button>
      )}
      <div className="side-by-side">
        <figure>
          <CopyCanvas source={source} />
          <figcaption>{`${label} (Original)`}</figcaption>
        </figure>
        <figure>
          <MaskedCanvas source={source} ranges={ranges} />
          <figcaption>{`${label} (Masked)`}</figcaption>
        </figure>
      </div>
    </div>
  );
}
