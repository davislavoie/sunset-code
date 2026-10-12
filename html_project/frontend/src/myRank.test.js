import { test } from "node:test";
import assert from "node:assert/strict";
import { byScore, move, withAuto } from "./myRank.js";

const day = (score, n) => ({ date: `2026-08-${String(n).padStart(2, "0")}`, score });
const apply = (list, i, dir) => {
  const updates = Object.fromEntries(move(list, i, dir).map((r) => [r.date, r]));
  return list.map((r) => updates[r.date] ?? r).sort(byScore);
};

test("smashing an arrow moves a day one place per press, through ties and the 0/100 ends", () => {
  for (const scores of [[90, 80, 70, 60], [100, 100, 80, 80, 80, 0, 0, 0], [50, 50, 50], [100, 99.99, 0.01, 0]]) {
    for (const dir of [1, -1]) {
      let list = scores.map(day).sort(byScore);
      const start = dir > 0 ? 0 : list.length - 1;
      const date = list[start].date;
      for (let k = 1; k < list.length; k++) {
        list = apply(list, list.findIndex((r) => r.date === date), dir);
        const at = list.findIndex((r) => r.date === date);
        // One place per press; inside a run of identical scores it may skip ahead, never stall.
        assert.ok(scores.length === new Set(scores).size ? at === start + dir * k : (at - start) * dir >= k, `${scores} dir ${dir} press ${k}`);
        assert.ok(list.every((r) => r.score >= 0 && r.score <= 100));
      }
      if ((list.findIndex((r) => r.date === date) - start) * dir < list.length - 1) continue;
      assert.deepEqual(move(list, list.findIndex((r) => r.date === date), dir), []); // already at the end
    }
  }
});

test("days without your pick fall back to the auto best frame", () => {
  const frames = { "2026-08-01": [{ ts: "a", Label: "07_sunset", Image: "s.jpg" }, { ts: "b", Label: "05_30m_pre", Image: "p.jpg" }],
    "2026-08-02": [{ ts: "c", Label: "07_sunset", Image: "t.jpg" }] };
  const ranked = [{ Date: "2026-08-01", "Raw Image": "p.jpg", Score: 61.234 }, { Date: "2026-08-02", "Raw Image": "t.jpg", Score: 40, Excluded: "dark" }];
  const rows = withAuto([{ date: "2026-08-02", ts: "c", score: 77 }], frames, ranked);
  assert.deepEqual(rows[0], { date: "2026-08-01", ts: "b", label: "05_30m_pre", url: "p.jpg", score: 61.23, auto: true });
  assert.equal(rows[1].score, 77);
  assert.equal(withAuto([], frames, ranked)[1].score, 0); // ruled-out days start at 0
});
