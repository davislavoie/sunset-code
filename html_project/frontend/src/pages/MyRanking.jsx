// My ranking: every day as a card, like Ranked images. Days you haven't touched show the auto
// ranking's best frame and score ("auto"); editing the score, moving a day or choosing another
// frame saves it as yours. Stored in InfluxDB (my_rank) as the source of truth for a good sunset.

import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { ArrowDown, ArrowUp, ChevronDown, ChevronLeft, ChevronRight, RotateCcw } from "lucide-react";
import { getJson } from "../api.js";
import { captureName } from "../DayDetail.jsx";
import Img, { SIZES } from "../Img.jsx";
import Reveal from "../Reveal.jsx";
import Tip from "../Tip.jsx";
import { byScore, move, withAuto } from "../myRank.js";

const PAGE_SIZE = 20;
// The card an arrow just moved and where it was on screen, so the page scrolls to keep it under
// the pointer and the next press hits the same day.
let anchor = null;
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
      <div className="myrank-list">
        {rows.slice(0, visible).map((r, i) => (
          <RankCard key={r.date} r={r} place={i + 1} frames={frames[r.date] ?? []} save={save}
            last={i === rows.length - 1} onMove={(dir, el) => {
              anchor = { date: r.date, top: el.getBoundingClientRect().top };
              move(rows, i, dir).forEach(save);
            }} />
        ))}
      </div>
      <div ref={sentinel} />
      {visible < rows.length && (
        <button className="btn show-more-btn" onClick={() => setVisible((v) => v + PAGE_SIZE)}>
          Show more ({rows.length - visible} left)
        </button>
      )}
    </>
  );
}

function RankCard({ r, place, last, frames, save, onMove }) {
  const [score, setScore] = useState(r.score);
  const [choosing, setChoosing] = useState(false);
  const card = useRef(null);
  useEffect(() => setScore(r.score), [r.score]);
  useLayoutEffect(() => {
    if (anchor?.date !== r.date) return;
    window.scrollBy({ top: card.current.getBoundingClientRect().top - anchor.top, behavior: "instant" });
    anchor = null;
  }, [place]);

  const commit = () => {
    const s = Math.min(100, Math.max(0, Number(score)));
    if (score !== "" && s !== r.score) save({ ...r, score: s });
    else setScore(r.score);
  };

  return (
    <>
      <div ref={card} className={`ranking-card myrank-card${r.auto ? " is-auto" : ""}`}>
        <div className="myrank-place">{place}</div>
        <button className="myrank-thumb" onClick={() => setChoosing(!choosing)} aria-label={`Choose the frame for ${r.date}`}>
          <Img src={r.url} loading="lazy" alt="" {...SIZES.photo} />
        </button>
        <div className="myrank-main">
          <div className="ranking-when">
            <h2>{longDate(r.date)} {r.auto && <span className="bubble">auto</span>}</h2>
            <span>{captureName(r.label)}</span>
          </div>
          <div className="myrank-score-row">
            <input className="myrank-score" type="number" min="0" max="100" step="any" value={score}
              aria-label={`Score for ${r.date}`} onChange={(e) => setScore(e.target.value)}
              onBlur={commit} onKeyDown={(e) => e.key === "Enter" && e.target.blur()} />
            <input type="range" min="0" max="100" step="any" value={score || 0} aria-label={`Score slider for ${r.date}`}
              onChange={(e) => setScore(Number(e.target.value))} onPointerUp={commit} onKeyUp={commit} />
          </div>
        </div>
        <div className="myrank-actions">
          <Tip label="Move up">
            <button className="icon-btn" disabled={place === 1} onClick={() => onMove(-1, card.current)}><ArrowUp size={18} /></button>
          </Tip>
          <Tip label="Move down">
            <button className="icon-btn" disabled={last} onClick={() => onMove(1, card.current)}><ArrowDown size={18} /></button>
          </Tip>
          {!r.auto && (
            <Tip label="Reset to the auto pick">
              <button className="icon-btn" onClick={() => save({ ...r, score: -1 })}><RotateCcw size={16} /></button>
            </Tip>
          )}
          <button className="btn" aria-expanded={choosing} onClick={() => setChoosing(!choosing)}>
            Frames <ChevronDown size={16} className={`chevron${choosing ? " open" : ""}`} />
          </button>
        </div>
      </div>
      <Reveal show={choosing}>
        {choosing && (
          <FramePicker r={r} frames={frames} onClose={() => setChoosing(false)} onSave={(f) => {
            save({ ...r, ts: f.ts, label: f.Label, url: f.Image });
            setChoosing(false);
          }} />
        )}
      </Reveal>
    </>
  );
}

/** Flick through a day's frames (buttons or arrow keys), then save the one that shows the sunset best. */
function FramePicker({ r, frames, onSave, onClose }) {
  const [i, setI] = useState(Math.max(0, frames.findIndex((f) => f.ts === r.ts)));
  const panel = useRef(null);
  useEffect(() => panel.current?.focus({ preventScroll: true }), []);
  const go = (step) => setI((n) => (n + step + frames.length) % frames.length);
  const f = frames[i];
  if (!f) return null;

  return (
    <div className="myrank-picker" ref={panel} tabIndex={-1} onKeyDown={(e) => {
      if (e.key === "ArrowLeft" || e.key === "ArrowRight") {
        e.preventDefault();
        go(e.key === "ArrowLeft" ? -1 : 1);
      } else if (e.key === "Enter" && f.ts !== r.ts) onSave(f);
      else if (e.key === "Escape") onClose();
    }}>
      <div className="myrank-picker-view">
        <button className="icon-btn" onClick={() => go(-1)} aria-label="Previous frame"><ChevronLeft size={22} /></button>
        <Img src={f.Image} alt={captureName(f.Label)} {...SIZES.photo} />
        <button className="icon-btn" onClick={() => go(1)} aria-label="Next frame"><ChevronRight size={22} /></button>
      </div>
      <div className="myrank-picker-bar">
        <span>{i + 1} / {frames.length} · {captureName(f.Label)} · {f.Time} · HSV {Math.round(f["HSV Score"])}</span>
        <span className="muted">← → to flip, Enter to save, Esc to close</span>
        <button className="btn" onClick={onClose}>Cancel</button>
        <button className="btn btn-primary" disabled={f.ts === r.ts} onClick={() => onSave(f)}>
          {f.ts === r.ts ? "Current frame" : "Save this frame"}
        </button>
      </div>
      <div className="myrank-strip">
        {frames.map((x, j) => (
          <button key={x.ts} className={`myrank-frame${j === i ? " active" : ""}${x.ts === r.ts ? " saved" : ""}`}
            onClick={() => setI(j)} aria-label={captureName(x.Label)}>
            <Img src={x.Image} loading="lazy" alt="" {...SIZES.photo} />
          </button>
        ))}
      </div>
    </div>
  );
}

const longDate = (iso) =>
  new Date(`${iso}T12:00`).toLocaleDateString(undefined, { weekday: "short", month: "long", day: "numeric", year: "numeric" });
