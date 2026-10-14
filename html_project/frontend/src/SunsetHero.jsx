// One shot of a day: large photo, score, weather, color breakdown, Share and Compare.
// Shown at the top of the calendar's Day tab; arrows (or ←/→) step through the day's shots.

import { useEffect, useState } from "react";
import { Link } from "react-router";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { sunsetPath, thumb } from "./api.js";
import { sizeForLabel } from "./Img.jsx";
import { Zoomable } from "./lightbox.jsx";
import ScoreBreakdown from "./ScoreBreakdown.jsx";
import { FlagPill } from "./Thumbs.jsx";
import Tip from "./Tip.jsx";
import Weather from "./Weather.jsx";

export default function SunsetHero({ shots, index, onSelect, best, camera, date }) {
  const shot = shots[index];
  const isBest = !!best && shot.Image === best["Raw Image"];
  const step = (d) => onSelect((index + d + shots.length) % shots.length);

  useEffect(() => {
    const onKey = (e) => {
      if (e.target.closest("input, textarea, select, [contenteditable]")) return;
      if (e.key === "ArrowLeft") step(-1);
      if (e.key === "ArrowRight") step(1);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  return (
    <div className="sunset-hero">
      <div className="sunset-hero-photo">
        <Zoomable
          className="sunset-hero-img"
          src={shot.Image}
          placeholder={thumb(shot.Image)}
          alt={`${camera} ${shot.Label.slice(3)} on ${date}`}
          fetchPriority="high"
          {...sizeForLabel(shot.Label)}
        />
        {shots.length > 1 && (
          <>
            <Tip label="Previous shot (←)">
              <button className="icon-btn hero-nav prev" aria-label="Previous shot" onClick={() => step(-1)}>
                <ChevronLeft size={20} />
              </button>
            </Tip>
            <Tip label="Next shot (→)">
              <button className="icon-btn hero-nav next" aria-label="Next shot" onClick={() => step(1)}>
                <ChevronRight size={20} />
              </button>
            </Tip>
            <div className="hero-count">{`${index + 1} / ${shots.length}`}</div>
          </>
        )}
      </div>
      <aside className="sunset-hero-side">
        <div className="hero-side-head">
          <div className="metric-label">Score</div>
          <div className="sunset-actions">
            {/* Share the /sunset/... permalink: Flask adds link-preview tags there. */}
            <ShareButton path={sunsetPath(camera, date)} title={`${camera} sunset · ${date}`} />
            <Link className="btn" to={`/compare?a=${camera}:${date}`}>
              Compare…
            </Link>
          </div>
        </div>
        <div className="score-row">
          <div className="sunset-score">{(isBest ? best.Score : shot.Score).toFixed(1)}%</div>
          <div className="score-row-meta">
            {isBest && <span className="bubble">Best shot</span>}
            <FlagPill reason={shot.Excluded} />
            <div className="sunset-meta">{`${shot.Label.slice(3).replaceAll("_", " ")} · ${shot.Time}`}</div>
          </div>
        </div>
        <AiVerdict ai={shot.AI} />
        <Weather w={shot.Weather} fill />
        <ScoreBreakdown breakdown={shot.Breakdown} score={shot["HSV Score"]} />
      </aside>
    </div>
  );
}

function ShareButton({ path, title }) {
  const [copied, setCopied] = useState(false);

  async function share() {
    const url = new URL(path, window.location.origin).href;
    if (navigator.share) {
      try {
        await navigator.share({ title, url });
      } catch {
        // dismissed by the user
      }
      return;
    }
    await navigator.clipboard.writeText(url);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <button className="btn btn-primary" onClick={share}>
      {copied ? "Link copied" : "Share"}
    </button>
  );
}

const VIEW_LABELS = { dark: "too dark", no_signal: "no camera signal" };

/** The local AI judge's take on a photo (only shown once ai_judge has judged it). */
export function AiVerdict({ ai, compact = false }) {
  if (!ai) return null;
  // Only dark / no-signal verdicts rule a frame out; the HSV score decides the rest.
  if (VIEW_LABELS[ai.view]) {
    return (
      <Tip label={ai.reason}>
        <span className="bubble destructive">Ruled out: {VIEW_LABELS[ai.view]}</span>
      </Tip>
    );
  }
  return (
    <Tip label={`Judged by ${ai.model}`}>
      <div className="ai-verdict">
        <span className="ai-score">AI {Math.round(ai.score)}</span>
        {!compact && ai.reason && <> · {ai.reason}</>}
      </div>
    </Tip>
  );
}
