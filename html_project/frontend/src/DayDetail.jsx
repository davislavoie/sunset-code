// "All images from this date" viewer: main image + prev/next + thumbnail strip.
// Used by the calendar's day-expand view and Ranked Images' "Show in Calendar".

import { useState } from "react";
import { Link } from "react-router";
import Img, { sizeForLabel } from "./Img.jsx";
import { Zoomable } from "./lightbox.jsx";

const isSpecial = (img) => /ranked|histogram/i.test(img.Label);

export default function DayDetail({ date, allData, onClose, onLoadToHsv, permalink }) {
  const [index, setIndex] = useState(0);

  const dateImages = allData.filter((img) => img.Date === date);
  const images = [
    ...dateImages.filter((img) => !isSpecial(img)).sort((a, b) => (a.Time > b.Time ? 1 : -1)),
    ...dateImages.filter(isSpecial),
  ];
  const i = index < images.length ? index : 0;
  const current = images[i];

  if (!images.length) return null;

  return (
    <div className="detail">
      <div className="detail-header">
        <h4>{`${current.Label.slice(3)} - ${date}`}</h4>
        <div className="detail-header-actions">
          {permalink && (
            <Link className="btn" to={permalink}>
              Open day →
            </Link>
          )}
          {onLoadToHsv && (
            <button className="btn" onClick={() => onLoadToHsv(current.Image)}>
              Load to HSV Tuner
            </button>
          )}
          {onClose && (
            <button className="btn" onClick={onClose}>
              ✕ Close
            </button>
          )}
        </div>
      </div>

      <div className="detail-nav">
        <button className="btn" onClick={() => setIndex(i === 0 ? images.length - 1 : i - 1)}>
          ← Previous
        </button>
        <div className="info">
          {`Image ${i + 1} of ${images.length} | Time: ${current.Time} | Score: ${current.Score.toFixed(1)}%`}
        </div>
        <button className="btn" onClick={() => setIndex(i >= images.length - 1 ? 0 : i + 1)}>
          Next →
        </button>
      </div>

      <div className="detail-main-img">
        <Zoomable
          src={current.Image}
          alt={current.Label}
          fetchPriority="high"
          {...sizeForLabel(current.Label)}
        />
      </div>

      <h5>All images from this date:</h5>
      <div className="thumb-strip" style={{ gridTemplateColumns: `repeat(${images.length}, 1fr)` }}>
        {images.map((img, idx) => (
          <div key={img.Image} className={`thumb${idx === i ? " selected" : ""}`} onClick={() => setIndex(idx)}>
            {/* Eager: the whole day loads as soon as the viewer opens. Thumbnails use the same
                files as the main view, so once loaded, clicking any of them is instant. */}
            <Img src={img.Image} alt="" fetchPriority="low" {...sizeForLabel(img.Label)} />
            <div className="label">{img.Label.slice(3)}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
