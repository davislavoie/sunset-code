// My ranking: every day as a card, like Ranked images. Days you haven't touched show the auto
// ranking's best frame and score ("auto"); editing the score, moving a day or choosing another
// frame saves it as yours. Stored in InfluxDB (my_rank) as the source of truth for a good sunset.

import { useEffect, useRef, useState } from "react";
import { ArrowDown, ArrowUp, ChevronDown, RotateCcw } from "lucide-react";
import { getJson } from "../api.js";
import { captureName } from "../DayDetail.jsx";
import Img, { SIZES } from "../Img.jsx";
import Reveal from "../Reveal.jsx";
import Tip from "../Tip.jsx";
import { byScore, nudge, withAuto } from "../myRank.js";

const PAGE_SIZE = 20;
const FILTERS = { all: "All days", mine: "Mine", auto: "Not reviewed" };

export default function MyRanking({ data, camera }) {
  const [ranks, setRanks] = useState(null);
  const [error, setError] = useState(null);
  const [filter, setFilter] = useState("all");
  const [visible, setVisible] = useState(PAGE_SIZE);
  const sentinel = useRef(null);

  useEffect(() => {
    setRanks(null);
    getJson(`/api/my-ranks?camera=${encodeURIComponent(camera)}`).then(setRanks, (e) => setError(e.message));
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
  }, [!!ranks]);

  if (error) return <div className="status-error">Couldn't load your ranking: {error}</div>;
  if (!ranks) return <div className="empty">Loading…</div>;

  // Sunset frames per day (no ranked/histogram plots), in shooting order.
  const frames = {};
  for (const img of data.all_data) {
    if (/^1[12]_/.test(img.Label)) continue;
    (frames[img.Date] ??= []).push(img);
  }
  for (const list of Object.values(frames)) list.sort((a, b) => (a.ts < b.ts ? -1 : 1));

  const all = withAuto(ranks, frames, data.ranked_images);
  const rows = all.filter((r) => filter === "all" || (filter === "auto") === !!r.auto).sort(byScore);

  async function save({ auto, ...row }) {
    const previous = ranks;
    setRanks((rs) => [...rs.filter((r) => r.date !== row.date), ...(row.score >= 0 ? [row] : [])]);
    setError(null);
    try {
      const res = await fetch("/api/admin/my-rank", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ camera, ...row }),
      });
      if (!res.ok) throw new Error((await res.json().catch(() => ({}))).error ?? res.status);
    } catch (e) {
      setRanks(previous);
      alert(`Couldn't save: ${e.message}`);
    }
  }

  return (
    <>
      <h1>My ranking</h1>
      <p className="muted">
        Every day starts with the auto ranking's best frame and score. Fix the ones that are wrong: change the score,
        move a day up or down, or choose another frame. Only days you've touched are saved as yours.{" "}
        {ranks.length} of {all.length} days reviewed.
      </p>
      <div className="ranking-controls">
        {Object.entries(FILTERS).map(([k, label]) => (
          <button key={k} className={`rank-chip${filter === k ? " active" : ""}`} aria-pressed={filter === k}
            onClick={() => { setFilter(k); setVisible(PAGE_SIZE); }}>
            {label}
          </button>
        ))}
      </div>
      <hr />
      {!rows.length && <div className="empty">No days here.</div>}
      {rows.slice(0, visible).map((r, i) => (
        <RankCard key={r.date} r={r} place={i + 1} frames={frames[r.date] ?? []} save={save}
          up={i > 0 && (() => save({ ...r, score: nudge(rows, i, -1) }))}
          down={i < rows.length - 1 && (() => save({ ...r, score: nudge(rows, i, 1) }))} />
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

function RankCard({ r, place, frames, save, up, down }) {
  const [score, setScore] = useState(r.score);
  const [choosing, setChoosing] = useState(false);
  useEffect(() => setScore(r.score), [r.score]);

  const commit = () => {
    const s = Math.min(100, Math.max(0, Number(score)));
    if (score !== "" && s !== r.score) save({ ...r, score: s });
    else setScore(r.score);
  };

  return (
    <>
      <div className={`ranking-card myrank-card${r.auto ? " is-auto" : ""}`}>
        <div className="ranking-title">
          <div className="myrank-place">{place}</div>
          <div className="ranking-score">
            <div className="metric-label">Score</div>
            <input className="ranking-score-value myrank-score" type="number" min="0" max="100" step="any"
              value={score} aria-label={`Score for ${r.date}`} onChange={(e) => setScore(e.target.value)}
              onBlur={commit} onKeyDown={(e) => e.key === "Enter" && e.target.blur()} />
          </div>
          <div className="ranking-when">
            <h2>{longDate(r.date)}</h2>
            <span>{captureName(r.label)}</span>
            {r.auto && <span className="bubble">auto</span>}
          </div>
          <div className="ranking-actions">
            <Tip label="Move up">
              <button className="icon-btn" disabled={!up} onClick={up || undefined}><ArrowUp size={16} /></button>
            </Tip>
            <Tip label="Move down">
              <button className="icon-btn" disabled={!down} onClick={down || undefined}><ArrowDown size={16} /></button>
            </Tip>
            {!r.auto && (
              <Tip label="Reset to the auto pick">
                <button className="icon-btn" onClick={() => save({ ...r, score: -1 })}><RotateCcw size={16} /></button>
              </Tip>
            )}
            <button className="btn" aria-expanded={choosing} onClick={() => setChoosing(!choosing)}>
              Choose frame <ChevronDown size={16} className={`chevron${choosing ? " open" : ""}`} />
            </button>
          </div>
        </div>
        <div className="myrank-body">
          <Img src={r.url} loading="lazy" alt="" {...SIZES.photo} />
          <input type="range" min="0" max="100" step="any" value={score || 0} aria-label={`Score slider for ${r.date}`}
            onChange={(e) => setScore(Number(e.target.value))} onPointerUp={commit} onKeyUp={commit} />
        </div>
      </div>
      <Reveal show={choosing}>
        <div className="myrank-frames">
          {frames.map((f) => (
            <button key={f.ts} className={`myrank-frame${f.ts === r.ts ? " active" : ""}`}
              onClick={() => { save({ ...r, ts: f.ts, label: f.Label, url: f.Image }); setChoosing(false); }}>
              <Img src={f.Image} loading="lazy" alt={captureName(f.Label)} {...SIZES.photo} />
              <span>{captureName(f.Label)} · {f.Time}</span>
            </button>
          ))}
        </div>
      </Reveal>
    </>
  );
}

const longDate = (iso) =>
  new Date(`${iso}T12:00`).toLocaleDateString(undefined, { weekday: "short", month: "long", day: "numeric", year: "numeric" });
