// Ranked Images (mirrors streamlit_project/ranking_tab.py)

import { useEffect, useRef, useState } from "react";
import { Link } from "react-router";
import { ArrowRight, ChevronDown, Maximize2, X } from "lucide-react";
import { dayPath } from "../api.js";
import DayDetail from "../DayDetail.jsx";
import HsvHistogram from "../HsvHistogram.jsx";
import Img, { SIZES } from "../Img.jsx";
import Reveal from "../Reveal.jsx";
import ScoreOverlay from "../ScoreOverlay.jsx";
import Tip from "../Tip.jsx";
import { CloudProfile, WeatherStats } from "../Weather.jsx";
import { useLightbox } from "../lightbox.jsx";
import Select from "../Select.jsx";

const PAGE_SIZE = 20;

export default function Ranking({ data, onLoadToHsv }) {
  const [sortBy, setSortBy] = useState("Score");
  const [order, setOrder] = useState("Highest to Lowest");
  const [showHidden, setShowHidden] = useState(false);
  // Rows are full-size images, so render a page at a time and add more on scroll.
  const [visible, setVisible] = useState(PAGE_SIZE);
  const sentinel = useRef(null);

  useEffect(() => {
    const el = sentinel.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      ([entry]) => entry.isIntersecting && setVisible((v) => v + PAGE_SIZE),
      { rootMargin: "800px" },
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  // Sunrise cameras label the moment itself "sunrise"; captures before/after are relative to it.
  const event = data.ranked_images.some((r) => /^\d+_sunrise/.test(r["Raw Image"]?.split("/").pop())) ? "sunrise" : "sunset";
  const ascending = order === "Lowest to Highest";
  // Days whose best shot doesn't count (thumbs down, bad view, dark) would skew the
  // ranking, so they're left out unless shown with the toggle.
  const hiddenCount = data.ranked_images.filter(ruledOut).length;
  const rows = data.ranked_images.filter((r) => showHidden || !ruledOut(r)).sort((a, b) => {
    const av = a[sortBy], bv = b[sortBy];
    const cmp = av < bv ? -1 : av > bv ? 1 : 0;
    return ascending ? cmp : -cmp;
  });

  return (
    <>
      <h1>Ranked images</h1>
      <div className="ranking-controls">
        <Select label="Sort by:" options={["Score", "Date", "Time"]} value={sortBy} onChange={setSortBy} />
        <Select label="Order:" options={["Highest to Lowest", "Lowest to Highest"]} value={order} onChange={setOrder} />
        {hiddenCount > 0 && (
          <button
            className={`rank-chip ranking-hidden-toggle${showHidden ? " active" : ""}`}
            aria-pressed={showHidden}
            onClick={() => setShowHidden(!showHidden)}
          >
            {showHidden ? "Hide" : "Show"} {hiddenCount} ruled-out {hiddenCount === 1 ? "day" : "days"}
          </button>
        )}
      </div>
      <hr />
      {!rows.length && <div className="empty">No data available.</div>}
      {rows.slice(0, visible).map((row) => (
        <RankingRow key={row["Ranked Image"]} row={row} event={event} allData={data.all_data} onLoadToHsv={onLoadToHsv} />
      ))}
      <div ref={sentinel} />
      {visible < rows.length && (
        <button className="btn show-more-btn" onClick={() => setVisible((v) => v + PAGE_SIZE)}>
          Show more ({rows.length - visible} left)
        </button>
      )}
    </>
  );
}

function RankingRow({ row, event, allData, onLoadToHsv }) {
  const [showDay, setShowDay] = useState(false);
  const rawUrl = row["Raw Image"];

  return (
    <>
      <div className="ranking-card">
        <div className="ranking-title">
          <h2>{longDate(row.Date)}</h2>
          <span>{[row.Time, captureName(rawUrl, event)].filter(Boolean).join(" · ")}</span>
          <div className="ranking-actions">
            <button className="btn" aria-expanded={showDay} onClick={() => setShowDay(!showDay)}>
              {showDay ? "Hide captures" : "Expand all captures"}
              <ChevronDown size={16} className={`chevron${showDay ? " open" : ""}`} />
            </button>
            <Link className="btn" to={dayPath(row.Date)}>
              Open day <ArrowRight size={16} />
            </Link>
          </div>
        </div>
        <div className="ranking-row">
          <ImageCell url={rawUrl} size={SIZES.photo} />
          <ScoreOverlay imageUrl={rawUrl} />
          <HsvHistogram imageUrl={rawUrl} />
          <div className="score-cell">
            <div className="metric-label">Score</div>
            <div className="metric-value">{row.Score.toFixed(2)}%</div>
            {row.Weather && <CloudProfile w={row.Weather} />}
          </div>
          <div className="info-cell">
            <WeatherStats w={row.Weather} />
          </div>
        </div>
      </div>
      <Reveal show={showDay}>
        <DayDetail date={row.Date} allData={allData} onClose={() => setShowDay(false)} onLoadToHsv={onLoadToHsv} />
      </Reveal>
    </>
  );
}

function ImageCell({ url, size }) {
  const lightbox = useLightbox();
  if (!url) return <div />;
  const isOpen = lightbox.src === url;

  return (
    <div className="ranked-img-cell">
      <Img src={url} alt="" loading="lazy" {...size} />
      <Tip label={isOpen ? "Close fullscreen" : "View fullscreen"}>
        <button
          className="fullscreen-toggle-btn"
          aria-label={isOpen ? "Close fullscreen" : "View fullscreen"}
          onClick={(e) => {
            e.stopPropagation();
            isOpen ? lightbox.close() : lightbox.open(url);
          }}
        >
          {isOpen ? <X size={16} /> : <Maximize2 size={16} />}
        </button>
      </Tip>
    </div>
  );
}

const longDate = (iso) =>
  iso ? new Date(`${iso}T12:00`).toLocaleDateString(undefined, { weekday: "short", month: "long", day: "numeric", year: "numeric" }) : "Unknown date";

/** "06_5m_pre_05-26-2025.jpg" -> "5 min before sunset", "07_sunset_..." -> "At sunset". */
function captureName(url, event = "sunset") {
  const label = url?.split("/").pop() ?? "";
  const m = /^\d+_(\d+)(m|h)_(pre|post)/.exec(label);
  if (m) return `${m[1]} ${m[2] === "h" ? "hr" : "min"} ${m[3] === "pre" ? "before" : "after"} ${event}`;
  const at = /^\d+_(sunset|sunrise)/.exec(label);
  return at ? `At ${at[1]}` : label.split(".")[0];
}

/** True when the day's best shot doesn't count (until ai_judge re-picks the day). */
function ruledOut(row) {
  return !!row.Excluded;
}
