// Ranked Images: one row per day with the original photo, ranked by score.
// "Show analysis" expands the ranked image and HSV histogram. Filter by period,
// click any image to view it fullscreen, or open the day in the calendar.

import { useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router";
import { dayPath } from "../api.js";
import Dropdown from "../Dropdown.jsx";
import { SIZES } from "../Img.jsx";
import { Zoomable } from "../lightbox.jsx";
import Reveal from "../Reveal.jsx";

const PAGE_SIZE = 20;

const SORTS = [
  { value: "score-desc", label: "Highest score" },
  { value: "score-asc", label: "Lowest score" },
  { value: "date-desc", label: "Newest" },
  { value: "date-asc", label: "Oldest" },
];

const iso = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;

/** Periods anchored on today. Seasons are meteorological (Dec-Feb is winter). */
function periods(now = new Date()) {
  const m = now.getMonth();
  const seasonStart = new Date(now.getFullYear(), m - ((m + 1) % 3), 1);
  const seasonEnd = new Date(seasonStart.getFullYear(), seasonStart.getMonth() + 3, 1);
  const seasonName = { 11: "Winter", 2: "Spring", 5: "Summer", 8: "Fall" }[seasonStart.getMonth()];
  const seasonYear =
    seasonName === "Winter" ? `${seasonStart.getFullYear()}–${String(seasonEnd.getFullYear()).slice(2)}` : seasonStart.getFullYear();
  const monthPrefix = iso(now).slice(0, 7);
  const year = String(now.getFullYear());
  return [
    {
      value: "month",
      label: now.toLocaleDateString(undefined, { month: "long", year: "numeric" }),
      test: (d) => d.startsWith(monthPrefix),
    },
    { value: "season", label: `${seasonName} ${seasonYear}`, test: (d) => d >= iso(seasonStart) && d < iso(seasonEnd) },
    { value: "year", label: year, test: (d) => d.startsWith(year) },
    { value: "all", label: "All time", test: () => true },
  ];
}

export default function Ranking({ data }) {
  const [period, setPeriod] = useState("all");
  const [sort, setSort] = useState("score-desc");
  const [visible, setVisible] = useState(PAGE_SIZE);
  const sentinel = useRef(null);
  const periodList = useMemo(() => periods(), []);

  // Every best shot ranked all-time by score (for "Top X%").
  const entries = useMemo(() => {
    const list = [...data.ranked_images].sort((a, b) => b.Score - a.Score);
    return list.map((e, i) => ({ ...e, topPercent: Math.max(1, Math.ceil(((i + 1) / list.length) * 100)) }));
  }, [data]);

  const shown = useMemo(() => {
    const test = periodList.find((p) => p.value === period).test;
    // Rank within the period (entries are already best-first), then apply the display order.
    // Ties share a rank (1, 1, 1, 4...): many days hit the 100 cap, and their order would be arbitrary.
    const ranked = [];
    entries
      .filter((e) => test(e.Date))
      .forEach((e, i) => {
        const prev = ranked[i - 1];
        const rank = prev && prev.Score === e.Score ? prev.rank : i + 1;
        ranked.push({ ...e, rank, tied: false });
        if (prev && prev.rank === rank) prev.tied = ranked[i].tied = true;
      });
    if (sort === "score-desc") return ranked;
    if (sort === "score-asc") return [...ranked].reverse();
    const sign = sort === "date-asc" ? 1 : -1;
    return [...ranked].sort((a, b) => sign * a.Date.localeCompare(b.Date));
  }, [entries, period, sort, periodList]);

  // New filters start from the first page again.
  useEffect(() => setVisible(PAGE_SIZE), [period, sort]);

  // Load the next page when the end of the list scrolls near.
  useEffect(() => {
    const el = sentinel.current;
    if (!el) return;
    const observer = new IntersectionObserver(([entry]) => entry.isIntersecting && setVisible((v) => v + PAGE_SIZE), {
      rootMargin: "800px",
    });
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  const periodLabel = periodList.find((p) => p.value === period).label;

  return (
    <>
      <h2>Ranked Images</h2>

      <div className="rank-filters">
        <div className="rank-chips" role="group" aria-label="Period">
          {periodList.map((p) => (
            <button
              key={p.value}
              className={`rank-chip${period === p.value ? " active" : ""}`}
              aria-pressed={period === p.value}
              onClick={() => setPeriod(p.value)}
            >
              {p.label}
            </button>
          ))}
        </div>
        <Dropdown label="Sort" value={sort} onChange={setSort} options={SORTS} />
      </div>
      <hr />

      {!shown.length ? (
        <div className="empty">No sunsets {period === "all" ? "yet" : `in ${periodLabel}`}.</div>
      ) : (
        <>
          {shown.slice(0, visible).map((e) => (
            <RankRow key={e.Date} entry={e} />
          ))}
          {visible < shown.length && (
            <button className="btn show-more-btn" onClick={() => setVisible((v) => v + PAGE_SIZE)}>
              Show more ({shown.length - visible} left)
            </button>
          )}
        </>
      )}
      <div ref={sentinel} />
    </>
  );
}

function RankRow({ entry }) {
  const [showAnalysis, setShowAnalysis] = useState(false);
  const date = new Date(`${entry.Date}T12:00:00`).toLocaleDateString(undefined, {
    weekday: "short", month: "long", day: "numeric", year: "numeric",
  });
  const photo = entry["Raw Image"] || entry["Ranked Image"];
  const analysis = [
    [entry["Ranked Image"], SIZES.ranked, "Ranked image"],
    [entry["HSV Image"], SIZES.histogram, "HSV histogram"],
  ].filter(([src]) => src);

  return (
    <div className="rank-row">
      <div className="rank-row-main">
        <Zoomable className="rank-row-photo" src={photo} alt={`Sunset, ${entry.Date}`} loading="lazy" {...SIZES.photo} />
        <div className="rank-row-info">
          <span
            className={`rank-badge${entry.rank <= 3 ? ` rank-medal-${entry.rank}` : ""}`}
            title={entry.tied ? `Tied for #${entry.rank}` : undefined}
          >
            {entry.tied ? "T-" : "#"}
            {entry.rank}
          </span>
          <div className="rank-score">{entry.Score.toFixed(1)}%</div>
          <div className="rank-pct">Top {entry.topPercent}%</div>
          <div className="rank-date">{date}</div>
          <div className="rank-time">Best shot at {entry.Time}</div>
          <div className="rank-actions">
            {analysis.length > 0 && (
              <button className="btn" aria-expanded={showAnalysis} onClick={() => setShowAnalysis(!showAnalysis)}>
                {showAnalysis ? "Hide analysis" : "Show analysis"}
              </button>
            )}
            <Link className="btn rank-open" to={dayPath(entry.Date)}>
              Open day →
            </Link>
          </div>
        </div>
      </div>
      <Reveal show={showAnalysis}>
        <div className="rank-analysis">
          {analysis.map(([src, size, label]) => (
            <figure key={label}>
              <Zoomable src={src} alt={`${label}, ${entry.Date}`} {...size} />
              <figcaption>{label}</figcaption>
            </figure>
          ))}
        </div>
      </Reveal>
    </div>
  );
}
