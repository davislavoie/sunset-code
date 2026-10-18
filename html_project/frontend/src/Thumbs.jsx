// Thumbs up / down on one capture. Down = it never counts as the day's best shot (and,
// with "all shots like this", neither does any near-identical shot from this camera);
// up = it's the day's pick. ai_analysis re-picks the ranked image within ~10 minutes.

import { useState } from "react";
import { ThumbsDown, ThumbsUp } from "lucide-react";
import Tip from "./Tip.jsx";
import { forgetCameraData } from "./api.js";

/** Why a capture is out, given its (possibly just changed) thumb. Mirrors backend.exclusion. */
export function exclusionFor(img, thumb) {
  if (thumb > 0) return null;
  if (thumb < 0) return "thumbs down";
  return img.Excluded === "thumbs down" ? null : img.Excluded;
}

/** "Flagged" for any shot that doesn't count (it still shows, scored 0%); the reason on hover. */
export function FlagPill({ reason, className = "" }) {
  if (!reason) return null;
  return (
    <Tip label={`Doesn't count: ${reason}`}>
      <span className={`bubble destructive flag-pill ${className}`}>Flagged</span>
    </Tip>
  );
}

/** "Glass lake +5" on btv shots where the lake mirrors the sky (ai_analysis/reflect.py); the bump is in Score, HSV unchanged. */
export function GlassPill({ glass, hsv, className = "" }) {
  if (!glass) return null;
  const base = hsv != null ? ` on the ${hsv.toFixed(1)} HSV score` : "";
  return (
    <Tip label={`Mirror-calm lake (reflection ${glass.mirror.toFixed(2)}): +${glass.bonus}${base}`}>
      <span className={`bubble success glass-pill ${className}`}>Glass lake +{glass.bonus}</span>
    </Tip>
  );
}

export default function Thumbs({ camera, img, onChange }) {
  const [state, setState] = useState({ thumb: img.Thumb ?? 0, badView: !!img.BadView });
  const [error, setError] = useState(null);

  async function save(thumb, badView = false) {
    const previous = state;
    const next = { thumb, badView };
    setState(next);
    onChange?.(next);
    setError(null);
    try {
      const res = await fetch("/api/admin/thumb", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ camera, label: img.Label, ts: img.ts, thumb, bad_view: badView }),
      });
      if (!res.ok) throw new Error((await res.json().catch(() => ({}))).error ?? res.status);
      forgetCameraData(camera);
    } catch (e) {
      setState(previous);
      onChange?.(previous);
      setError(`Couldn't save: ${e.message}`);
    }
  }

  return (
    <div className="thumbs">
      <Tip label="Good one: make it the day's pick">
        <button type="button" className="thumb-up" aria-pressed={state.thumb === 1} aria-label="Thumbs up"
          onClick={() => save(state.thumb === 1 ? 0 : 1)}>
          <ThumbsUp size={14} />
        </button>
      </Tip>
      <Tip label="Never count this shot">
        <button type="button" className="thumb-down" aria-pressed={state.thumb === -1} aria-label="Thumbs down"
          onClick={() => save(state.thumb === -1 ? 0 : -1)}>
          <ThumbsDown size={14} />
        </button>
      </Tip>
      {state.thumb === -1 && (
        <Tip label="Also rule out every near-identical shot from this camera (e.g. a bad preset view)">
          <label>
            <input type="checkbox" checked={state.badView} onChange={(e) => save(-1, e.target.checked)} /> all shots like this
          </label>
        </Tip>
      )}
      {error && <span className="thumbs-error">{error}</span>}
    </div>
  );
}
