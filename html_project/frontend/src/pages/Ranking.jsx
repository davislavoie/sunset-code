// Ranked Images (mirrors streamlit_project/ranking_tab.py)

import { useEffect, useRef, useState } from "react";
import { Link } from "react-router";
import { dayPath } from "../api.js";
import DayDetail from "../DayDetail.jsx";
import Img, { SIZES } from "../Img.jsx";
import Reveal from "../Reveal.jsx";
import { useLightbox } from "../lightbox.jsx";
import Select from "../Select.jsx";

const PAGE_SIZE = 20;

export default function Ranking({ data, onLoadToHsv }) {
  const [sortBy, setSortBy] = useState("Score");
  const [order, setOrder] = useState("Highest to Lowest");
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

  const ascending = order === "Lowest to Highest";
  const rows = [...data.ranked_images].sort((a, b) => {
    const av = a[sortBy], bv = b[sortBy];
    const cmp = av < bv ? -1 : av > bv ? 1 : 0;
    return ascending ? cmp : -cmp;
  });

  return (
    <>
      <h2>Ranked Images</h2>
      <div className="ranking-controls">
        <Select label="Sort by:" options={["Score", "Date", "Time"]} value={sortBy} onChange={setSortBy} />
        <Select label="Order:" options={["Highest to Lowest", "Lowest to Highest"]} value={order} onChange={setOrder} />
      </div>
      <hr />
      {!rows.length && <div className="empty">No data available.</div>}
      {rows.slice(0, visible).map((row) => (
        <RankingRow key={row["Ranked Image"]} row={row} allData={data.all_data} onLoadToHsv={onLoadToHsv} />
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

function RankingRow({ row, allData, onLoadToHsv }) {
  const [showDay, setShowDay] = useState(false);
  const rawUrl = row["Raw Image"];

  return (
    <>
      <div className="ranking-row">
        <ImageCell url={row["Ranked Image"]} size={SIZES.ranked} />
        <ImageCell url={rawUrl} size={SIZES.photo} />
        <ImageCell url={row["HSV Image"]} size={SIZES.histogram} />
        <div className="score-cell">
          <div className="metric-label">Score</div>
          <div className="metric-value">{row.Score.toFixed(2)}%</div>
        </div>
        <div className="info-cell">
          <div><strong>Date:</strong> {row.Date || "N/A"}</div>
          <div><strong>Time:</strong> {row.Time || "N/A"}</div>
          <div><strong>Label:</strong> {rawUrl ? rawUrl.split("/").pop().split(".")[0] : "No raw image"}</div>
          <button className="btn show-in-calendar-btn" onClick={() => setShowDay(!showDay)}>
            {showDay ? "Hide" : "Show in Calendar"}
          </button>
          <Link className="btn show-in-calendar-btn" to={dayPath(row.Date)}>
            Open day →
          </Link>
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
      <button
        className="fullscreen-toggle-btn"
        title={isOpen ? "Close fullscreen" : "View fullscreen"}
        onClick={(e) => {
          e.stopPropagation();
          isOpen ? lightbox.close() : lightbox.open(url);
        }}
      >
        {isOpen ? "✕" : "⛶"}
      </button>
    </div>
  );
}
