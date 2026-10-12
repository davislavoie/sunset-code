// Ordering helpers for the My ranking page.

const round = (x) => Math.round(x * 100) / 100;
export const byScore = (a, b) => b.score - a.score || (a.date < b.date ? 1 : -1);

/**
 * Rows to save so row i moves one place up (dir -1) or down (dir 1) in a list sorted high to low.
 * It takes a score between the day it passes and the next one; with no room there (a tie, or the
 * 0/100 end) the day it passes moves the other way instead. Inside a dead tie it steps 0.01 out.
 */
export function move(list, i, dir, flip = true) {
  const x = list[i], a = list[i + dir], b = list[i + 2 * dir];
  if (!a) return [];
  const edge = b ? b.score : dir < 0 ? 100 : 0;
  const s = round((a.score + edge) / 2);
  if (s !== a.score && (s !== edge || !b)) return [{ ...x, score: s }];
  const other = flip && move(list, i + dir, -dir, false);
  if (other?.length === 1) return other;
  const past = round(a.score - dir * 0.01);
  if (past >= 0 && past <= 100) return [{ ...x, score: past }];
  return [{ ...x, score: a.score }, { ...a, score: round(a.score + dir * 0.01) }];
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
