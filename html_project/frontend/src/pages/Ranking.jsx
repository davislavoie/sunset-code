// Ranked Images (mirrors streamlit_project/ranking_tab.py)

import { useEffect, useRef, useState } from "react";
import { Link } from "react-router";
import { ArrowRight, ChevronDown, ChevronUp } from "lucide-react";
import { dayPath, getJson } from "../api.js";
import DayDetail, { captureName } from "../DayDetail.jsx";
import { ForecastMetric } from "../Forecast.jsx";
import HsvHistogram from "../HsvHistogram.jsx";
import Reveal from "../Reveal.jsx";
import ScoreOverlay from "../ScoreOverlay.jsx";
import { CloudProfile, WeatherStats, cloudSource } from "../Weather.jsx";
import { GlassPill } from "../Thumbs.jsx";
import Select from "../Select.jsx";
import Tip from "../Tip.jsx";

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
  // Anonymous up/down votes per day (/api/votes): feedback for tuning the score later, not part of it.
  const [votes, setVotes] = useState({});

  useEffect(() => {
    let live = true;
    getJson(`/api/votes?camera=${encodeURIComponent(camera)}`).then(
      (list) => live && setVotes(Object.fromEntries(list.map((v) => [v.date, v]))),
      () => {}, // no counts: the arrows still work and show the totals once voted
    );
    return () => {
      live = false;
    };
  }, [camera]);

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
        <RankingRow key={row["Ranked Image"]} row={row} camera={camera} votes={votes[row.Date]}
          onVoted={(v) => setVotes((all) => ({ ...all, [v.date]: v }))} event={event} allData={data.all_data} onLoadToHsv={onLoadToHsv} />
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

function RankingRow({ row, camera, votes, onVoted, event, allData, onLoadToHsv }) {
  const [showDay, setShowDay] = useState(false);
  const rawUrl = row["Raw Image"];

  return (
    <>
      <div className="ranking-card">
        <div className="ranking-title">
          <Vote camera={camera} date={row.Date} totals={votes} onVoted={onVoted} />
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

/** Up / down arrows with the net count between them. The browser remembers its vote (localStorage), so
 * tapping again undoes it and the other arrow switches it; nothing ties a vote to a person. */
function Vote({ camera, date, totals, onVoted }) {
  const key = `vote:${camera}:${date}`;
  const [mine, setMine] = useState(() => {
    try {
      return Number(localStorage.getItem(key)) || 0;
    } catch {
      return 0;
    }
  });
  const up = totals?.up ?? 0, down = totals?.down ?? 0;

  async function cast(dir) {
    const to = mine === dir ? 0 : dir;
    const previous = { mine, totals };
    const shift = (d) => (to === d) - (mine === d);
    setMine(to);
    onVoted({ camera, date, up: up + shift(1), down: down + shift(-1) });
    try {
      const res = await fetch("/api/vote", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ camera, date, from: mine, to }),
      });
      if (!res.ok) throw new Error(res.status);
      onVoted(await res.json());
      try {
        if (to) localStorage.setItem(key, String(to));
        else localStorage.removeItem(key);
      } catch {} // private window: the vote still counts, it just won't be remembered
    } catch {
      setMine(previous.mine);
      onVoted(previous.totals ?? { camera, date, up: 0, down: 0 });
    }
  }

  return (
    <div className="ranking-vote" role="group" aria-label="Is this ranked right?">
      <Tip label="Rank higher">
        <button type="button" className="vote-up" aria-pressed={mine === 1} aria-label="Rank higher" onClick={() => cast(1)}>
          <ChevronUp size={18} strokeWidth={2.5} />
        </button>
      </Tip>
      <Tip label={`${up} up · ${down} down`}>
        <span className="vote-count">{up - down}</span>
      </Tip>
      <Tip label="Rank lower">
        <button type="button" className="vote-down" aria-pressed={mine === -1} aria-label="Rank lower" onClick={() => cast(-1)}>
          <ChevronDown size={18} strokeWidth={2.5} />
        </button>
      </Tip>
    </div>
  );
}

const longDate = (iso) =>
  iso ? new Date(`${iso}T12:00`).toLocaleDateString(undefined, { weekday: "short", month: "long", day: "numeric", year: "numeric" }) : "Unknown date";

/** True when the day's best shot doesn't count (until ai_judge re-picks the day). */
function ruledOut(row) {
  return !!row.Excluded;
}
