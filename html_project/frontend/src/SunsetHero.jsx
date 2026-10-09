// The best shot of a day: large photo, score, color breakdown, Share and Compare.
// Shown at the top of the calendar's Day tab.

import { useState } from "react";
import { Link } from "react-router";
import { sunsetPath } from "./api.js";
import { SIZES } from "./Img.jsx";
import { Zoomable } from "./lightbox.jsx";
import ScoreBreakdown from "./ScoreBreakdown.jsx";

export default function SunsetHero({ best, camera, date }) {
  return (
    <div className="sunset-hero">
      <Zoomable
        className="sunset-hero-img"
        src={best["Raw Image"] || best["Ranked Image"]}
        alt={`${camera} sunset on ${date}`}
        {...(best["Raw Image"] ? SIZES.photo : SIZES.ranked)}
      />
      <aside className="sunset-hero-side">
        <div className="metric-label">Score</div>
        <div className="sunset-score">{best.Score.toFixed(1)}%</div>
        <div className="sunset-meta">Best shot at {best.Time}</div>
        <AiVerdict ai={best.AI} />
        {best["Raw Image"] && <ScoreBreakdown imageUrl={best["Raw Image"]} />}
        <div className="sunset-actions">
          {/* Share the /sunset/... permalink: Flask adds link-preview tags there. */}
          <ShareButton path={sunsetPath(camera, date)} title={`${camera} sunset · ${date}`} />
          <Link className="btn" to={`/compare?a=${camera}:${date}`}>
            Compare…
          </Link>
        </div>
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

const VIEW_LABELS = { obstructed: "obstructed view", dark: "too dark", no_signal: "no camera signal" };

/** The local AI judge's take on a photo (only shown once ai_judge has judged it). */
export function AiVerdict({ ai, compact = false }) {
  if (!ai) return null;
  if (!ai.is_sunset) {
    return <div className="ai-verdict ai-flagged">Not the sky: {VIEW_LABELS[ai.view] ?? ai.view}</div>;
  }
  return (
    <div className="ai-verdict" title={`Judged by ${ai.model}`}>
      <span className="ai-score">AI {Math.round(ai.score)}</span>
      {!compact && ai.reason && <> · {ai.reason}</>}
    </div>
  );
}
