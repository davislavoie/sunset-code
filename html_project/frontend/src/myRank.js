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
