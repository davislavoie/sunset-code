// "All images from this date" viewer: main image + prev/next + thumbnail strip.
// Used by the calendar's day-expand view and Ranked Images' "Show in Calendar".

import { useState } from "react";
import { Link } from "react-router";
import { ArrowRight, ChevronLeft, ChevronRight, X } from "lucide-react";
import Img, { sizeForLabel } from "./Img.jsx";
import { Zoomable } from "./lightbox.jsx";
import Tip from "./Tip.jsx";

const isSpecial = (img) => /ranked|histogram/i.test(img.Label);

/** "06_5m_pre_05-26-2025.jpg" -> "5 min before sunset", "07_sunset_..." -> "At sunset". */
export function captureName(label, event = "sunset") {
  const name = label?.split("/").pop() ?? "";
  const m = /^\d+_(\d+)(m|h)_(pre|post)/.exec(name);
  if (m) return `${m[1]} ${m[2] === "h" ? "hr" : "min"} ${m[3] === "pre" ? "before" : "after"} ${event}`;
  const at = /^\d+_(sunset|sunrise)/.exec(name);
  if (at) return `At ${at[1]}`;
  if (/ranked/i.test(name)) return "Ranked image";
  if (/histogram/i.test(name)) return "HSV histogram";
  return name.split(".")[0];
}

export default function DayDetail({ date, allData, onClose, onLoadToHsv, permalink }) {
  const [index, setIndex] = useState(0);

  const dateImages = allData.filter((img) => img.Date === date);
  const images = [
    ...dateImages.filter((img) => !isSpecial(img)).sort((a, b) => (a.Time > b.Time ? 1 : -1)),
    ...dateImages.filter(isSpecial),
  ];
  const i = index < images.length ? index : 0;
  const current = images[i];
  const event = images.some((img) => /^\d+_sunrise/.test(img.Label)) ? "sunrise" : "sunset";
  const step = (d) => setIndex((i + d + images.length) % images.length);

  if (!images.length) return null;

  return (
    <div className="detail">
      <div className="detail-header">
        <div className="detail-title">
          <h3>{captureName(current.Label, event)}</h3>
          <span>{`${current.Time} · Score ${current.Score.toFixed(1)}%`}</span>
        </div>
        <div className="detail-header-actions">
          {permalink && (
            <Link className="btn" to={permalink}>
              Open day <ArrowRight size={16} />
            </Link>
          )}
          {onLoadToHsv && (
            <button className="btn" onClick={() => onLoadToHsv(current.Image)}>
              Load to HSV Tuner
            </button>
          )}
          {onClose && (
            <button className="btn" onClick={onClose}>
              <X size={16} /> Close
            </button>
          )}
        </div>
      </div>

      <div className="detail-main-img">
        <Zoomable
          src={current.Image}
          alt={current.Label}
          fetchPriority="high"
          {...sizeForLabel(current.Label)}
        />
        <Tip label="Previous capture">
          <button className="icon-btn hero-nav prev" aria-label="Previous capture" onClick={() => step(-1)}>
            <ChevronLeft size={20} />
          </button>
        </Tip>
        <Tip label="Next capture">
          <button className="icon-btn hero-nav next" aria-label="Next capture" onClick={() => step(1)}>
            <ChevronRight size={20} />
          </button>
        </Tip>
        <div className="hero-count">{`${i + 1} / ${images.length}`}</div>
      </div>

      <div className="detail-strip-title">All captures from {date}</div>
      <div className="thumb-strip" style={{ gridTemplateColumns: `repeat(${images.length}, 1fr)` }}>
        {images.map((img, idx) => (
          <div key={img.Image} className={`thumb${idx === i ? " selected" : ""}`} onClick={() => setIndex(idx)}>
            {/* Eager: the whole day loads as soon as the viewer opens. Thumbnails use the same
                files as the main view, so once loaded, clicking any of them is instant. */}
            <Img src={img.Image} alt="" fetchPriority="low" {...sizeForLabel(img.Label)} />
            <div className="label">{img.Time}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
