// Admin archive: every capture that doesn't count (thumbs down, same view as a thumbed-down
// shot, dark / no signal), newest day first. Clearing a thumbs down here brings it back.

import { useState } from "react";
import { CaptureCard } from "./Calendar.jsx";

export default function Archive({ data, camera }) {
  const [reason, setReason] = useState("all");
  const out = data.all_data.filter((img) => img.Excluded && !/^(11_|12_)/.test(img.Label));
  const counts = out.reduce((acc, img) => ({ ...acc, [img.Excluded]: (acc[img.Excluded] ?? 0) + 1 }), {});
  const shown = out.filter((img) => reason === "all" || img.Excluded === reason);
  const days = Map.groupBy(shown, (img) => img.Date);

  return (
    <div>
      <h1>Archive</h1>
      <p className="archive-intro">
        {out.length} {camera} shots don't count toward rankings. Clear a thumbs down to bring one
        back; the day's best shot updates within 10 minutes.
      </p>
      <div className="rank-chips">
        {[["all", out.length], ...Object.entries(counts)].map(([key, n]) => (
          <button key={key} className={`rank-chip${reason === key ? " active" : ""}`} onClick={() => setReason(key)}>
            {key === "all" ? "All" : key[0].toUpperCase() + key.slice(1)} ({n})
          </button>
        ))}
      </div>
      {!out.length && <div className="empty">Nothing ruled out for this camera.</div>}
      {[...days].sort(([a], [b]) => (a < b ? 1 : -1)).map(([date, imgs]) => (
        <section key={date}>
          <h4>
            {date} · {imgs.length}
          </h4>
          <div className="day-view-grid">
            {imgs.map((img) => (
              <CaptureCard key={img.Image} img={img} camera={camera} admin />
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}
