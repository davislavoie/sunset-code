// Ordering helpers for the My ranking page.

const round = (x) => Math.round(x * 100) / 100;
export const byScore = (a, b) => b.score - a.score || (a.date < b.date ? 1 : -1);

/** Score that puts row i one place up (dir -1) or down (dir 1) in a list sorted high to low. */
export function nudge(list, i, dir) {
  const score = (j) => list[j]?.score;
  if (dir < 0) {
    if (i === 0) return list[0].score;
    return round(i === 1 ? Math.min(100, score(0) + 1) : (score(i - 1) + score(i - 2)) / 2);
  }
  if (i === list.length - 1) return list[i].score;
  return round(i === list.length - 2 ? Math.max(0, score(i + 1) - 1) : (score(i + 1) + score(i + 2)) / 2);
}

/** One row per day: your saved pick, else the auto ranking's best frame and score (auto: true). */
export function withAuto(ranks, frames, rankedImages) {
  const best = {};
  for (const r of rankedImages) if (!best[r.Date] || r.Score > best[r.Date].Score) best[r.Date] = r;
  const mine = Object.fromEntries(ranks.map((r) => [r.date, r]));
  return Object.keys(frames).map((date) => {
    if (mine[date]) return mine[date];
    const b = best[date];
    const f = frames[date].find((x) => x.Image === b?.["Raw Image"]) ?? frames[date].find((x) => /^07_/.test(x.Label)) ?? frames[date][0];
    return { date, ts: f.ts, label: f.Label, url: f.Image, score: b && !b.Excluded ? round(b.Score) : 0, auto: true };
  });
}
