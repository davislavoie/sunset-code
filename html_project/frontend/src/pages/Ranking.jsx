// Ranked Images (mirrors streamlit_project/ranking_tab.py)

import { useEffect, useRef, useState } from "react";
import { Link } from "react-router";
import { ArrowRight, ChevronDown } from "lucide-react";
import { dayPath } from "../api.js";
import DayDetail, { captureName } from "../DayDetail.jsx";
import { ForecastMetric } from "../Forecast.jsx";
import HsvHistogram from "../HsvHistogram.jsx";
import Reveal from "../Reveal.jsx";
import ScoreOverlay from "../ScoreOverlay.jsx";
import { CloudProfile, WeatherStats, cloudSource } from "../Weather.jsx";
import { GlassPill } from "../Thumbs.jsx";
import Select from "../Select.jsx";

const PAGE_SIZE = 20;
// Sort options: the row's own fields, then the weather at the best shot (Open-Meteo, stored with each capture).
const SORTS = {
  Score: (r) => r.Score, Date: (r) => r.Date, Time: (r) => r.dt_local?.slice(11),
  Temperature: (r) => r.Weather?.temperature_2m, Humidity: (r) => r.Weather?.relative_humidity_2m,
  "Cloud cover": (r) => r.Weather?.cloud_cover_total,
  Precipitation: (r) => r.Weather?.precipitation, Wind: (r) => r.Weather?.obs_wind_mph ?? r.Weather?.wind_speed_10m,
};

export default function Ranking({ data, camera, onLoadToHsv }) {
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
    const av = SORTS[sortBy](a), bv = SORTS[sortBy](b);
    if (av == null || bv == null) return (av == null) - (bv == null); // no weather: last either way
    const cmp = av < bv ? -1 : av > bv ? 1 : 0;
    return ascending ? cmp : -cmp;
  });

  return (
    <>
      <h1>Ranked images</h1>
      <div className="ranking-controls">
        <Select label="Sort by:" options={Object.keys(SORTS)} value={sortBy} onChange={setSortBy} />
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
        <RankingRow key={row["Ranked Image"]} row={row} camera={camera} event={event} allData={data.all_data} onLoadToHsv={onLoadToHsv} />
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

function RankingRow({ row, camera, event, allData, onLoadToHsv }) {
  const [showDay, setShowDay] = useState(false);
  const rawUrl = row["Raw Image"];

  return (
    <>
      <div className="ranking-card">
        <div className="ranking-title">
          <div className="ranking-score">
            <div className="metric-label">Score</div>
            <div className="ranking-score-value">{row.Score.toFixed(1)}%</div>
            {!!(row.Glass || row.Zoom) && (
              <div className="metric-label">
                {[row["HSV Score"].toFixed(1), row.Glass && `+ ${row.Glass.bonus} glass`, row.Zoom && `− ${-row.Zoom} zoomed in`]
                  .filter(Boolean).join(" ")}
              </div>
            )}
          </div>
          <ForecastMetric date={row.Date} allData={allData} />
          <div className="ranking-when">
            <h2>{longDate(row.Date)}</h2>
            <span>{[row.Time, captureName(rawUrl, event)].filter(Boolean).join(" · ")}</span>
            <GlassPill glass={row.Glass} hsv={row["HSV Score"]} />
          </div>
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
          <ScoreOverlay imageUrl={rawUrl} camera={camera} interactive />
          <HsvHistogram imageUrl={rawUrl} camera={camera} ts={row.ts} />
          <div className="rank-media">
            <div className="hsv-hist-title">Clouds toward the sun{row.Weather && <span className="cp-source"> · {cloudSource(row.Weather)}</span>}</div>
            {row.Weather ? <CloudProfile w={row.Weather} fill /> : <div className="rank-media-empty">No weather saved</div>}
          </div>
          <div className="rank-media info-cell">
            <div className="hsv-hist-title">Weather</div>
            <WeatherStats w={row.Weather} />
          </div>
        </div>
      </div>
      <Reveal show={showDay}>
        <DayDetail date={row.Date} start={rawUrl} allData={allData} onClose={() => setShowDay(false)} onLoadToHsv={onLoadToHsv} />
      </Reveal>
    </>
  );
}

const longDate = (iso) =>
  iso ? new Date(`${iso}T12:00`).toLocaleDateString(undefined, { weekday: "short", month: "long", day: "numeric", year: "numeric" }) : "Unknown date";

/** True when the day's best shot doesn't count (until ai_judge re-picks the day). */
function ruledOut(row) {
  return !!row.Excluded;
}
