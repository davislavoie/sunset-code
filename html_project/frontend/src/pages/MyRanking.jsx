// My ranking: pick the frame that best shows each day's sunset and score it 0-100. The list
// sorts itself by score; the arrows move a day one place by slotting its score between its new
// neighbours. Stored in InfluxDB (my_rank) as the source of truth for what a good sunset is.

import { useEffect, useState } from "react";
import { ArrowDown, ArrowUp, X } from "lucide-react";
import { getJson } from "../api.js";
import { captureName } from "../DayDetail.jsx";
import Img, { SIZES } from "../Img.jsx";
import Tip from "../Tip.jsx";
import { byScore, nudge } from "../myRank.js";

export default function MyRanking({ data, camera }) {
  const [ranks, setRanks] = useState(null);
  const [error, setError] = useState(null);
  const [day, setDay] = useState(null);
  const [pick, setPick] = useState(null);
  const [score, setScore] = useState(50);

  useEffect(() => {
    setRanks(null);
    setDay(null);
    getJson(`/api/my-ranks?camera=${encodeURIComponent(camera)}`).then(setRanks, (e) => setError(e.message));
  }, [camera]);

  // Sunset frames per day (no ranked/histogram plots), in shooting order.
  const frames = {};
  for (const img of data.all_data) {
    if (/^1[12]_/.test(img.Label)) continue;
    (frames[img.Date] ??= []).push(img);
  }
  for (const list of Object.values(frames)) list.sort((a, b) => (a.ts < b.ts ? -1 : 1));
  const dates = Object.keys(frames).sort().reverse();

  if (error) return <div className="status-error">Couldn't load your ranking: {error}</div>;
  if (!ranks) return <div className="empty">Loading…</div>;

  const ranked = [...ranks].sort(byScore);
  const rankedDates = new Set(ranks.map((r) => r.date));
  const unranked = dates.filter((d) => !rankedDates.has(d));
  const current = day ?? unranked[0];
  const existing = ranks.find((r) => r.date === current);

  async function save(row) {
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

  function open(date) {
    const r = ranks.find((x) => x.date === date);
    setDay(date);
    setPick(r ? frames[date]?.find((f) => f.ts === r.ts) ?? null : null);
    setScore(r ? r.score : 50);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function savePick() {
    save({ date: current, ts: pick.ts, label: pick.Label, url: pick.Image, score: Number(score) });
    setDay(null);
    setPick(null);
    setScore(50);
  }

  const skipTo = (step) => {
    const i = dates.indexOf(current);
    const next = dates[i + step];
    if (next) open(next);
  };

  return (
    <>
      <h1>My ranking</h1>
      <p className="muted">
        Pick the frame that best shows each day's sunset and give it a score. Your ranking is the source of truth
        the forecast is trained against. {ranks.length} of {dates.length} days ranked.
      </p>

      {current && (
        <section className="myrank-pick">
          <div className="myrank-pick-head">
            <button className="btn-small" onClick={() => skipTo(1)} disabled={dates.indexOf(current) === dates.length - 1}>
              ← Older
            </button>
            <h2>
              {current} {existing && <span className="bubble">ranked {existing.score}</span>}
            </h2>
            <button className="btn-small" onClick={() => skipTo(-1)} disabled={dates.indexOf(current) === 0}>
              Newer →
            </button>
          </div>
          <div className="myrank-frames">
            {(frames[current] ?? []).map((f) => (
              <button key={f.ts} className={`myrank-frame${pick?.ts === f.ts ? " active" : ""}`} onClick={() => setPick(f)}>
                <Img src={f.Image} loading="lazy" alt={captureName(f.Label)} {...SIZES.photo} />
                <span>
                  {captureName(f.Label)} · {f.Time}
                </span>
              </button>
            ))}
          </div>
          <div className="myrank-save">
            <label>
              Score{" "}
              <input type="number" min="0" max="100" value={score} onChange={(e) => setScore(e.target.value)} />
            </label>
            <input type="range" min="0" max="100" value={score} onChange={(e) => setScore(e.target.value)} />
            <button className="btn btn-primary" disabled={!pick || score === ""} onClick={savePick}>
              {existing ? "Update" : "Save"}
            </button>
            {unranked.length > 0 && current !== unranked[0] && (
              <button className="btn-small" onClick={() => open(unranked[0])}>
                Next unranked day
              </button>
            )}
          </div>
        </section>
      )}

      <h2>Your ranking</h2>
      {!ranked.length && <div className="empty">Nothing ranked yet.</div>}
      <ol className="myrank-list">
        {ranked.map((r, i) => (
          <li key={r.date}>
            <span className="myrank-place">{i + 1}</span>
            <button className="myrank-thumb" onClick={() => open(r.date)} aria-label={`Change the frame for ${r.date}`}>
              <Img src={r.url} loading="lazy" alt="" {...SIZES.photo} />
            </button>
            <div className="myrank-info">
              <strong>{r.date}</strong>
              <span className="muted">{captureName(r.label)}</span>
            </div>
            <input
              type="number"
              min="0"
              max="100"
              step="any"
              defaultValue={r.score}
              key={r.score}
              aria-label={`Score for ${r.date}`}
              onBlur={(e) => e.target.value !== "" && Number(e.target.value) !== r.score &&
                save({ ...r, score: Math.min(100, Math.max(0, Number(e.target.value))) })}
              onKeyDown={(e) => e.key === "Enter" && e.target.blur()}
            />
            <Tip label="Move up">
              <button className="icon-btn" disabled={i === 0} onClick={() => save({ ...r, score: nudge(ranked, i, -1) })}>
                <ArrowUp size={16} />
              </button>
            </Tip>
            <Tip label="Move down">
              <button className="icon-btn" disabled={i === ranked.length - 1}
                onClick={() => save({ ...r, score: nudge(ranked, i, 1) })}>
                <ArrowDown size={16} />
              </button>
            </Tip>
            <Tip label="Remove from the ranking">
              <button className="icon-btn" onClick={() => save({ ...r, score: -1 })}>
                <X size={16} />
              </button>
            </Tip>
          </li>
        ))}
      </ol>
    </>
  );
}
