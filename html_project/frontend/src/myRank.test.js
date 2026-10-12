import { test } from "node:test";
import assert from "node:assert/strict";
import { byScore, nudge, withAuto } from "./myRank.js";

const list = [90, 80, 70, 60].map((score, i) => ({ date: `2026-08-0${i + 1}`, score }));
const moved = (i, dir) => list.map((r, j) => (j === i ? { ...r, score: nudge(list, i, dir) } : r)).sort(byScore);

test("arrows move a day exactly one place", () => {
  assert.equal(moved(2, -1)[1].score, 85); // 70 slots between 90 and 80
  assert.equal(moved(1, -1)[0].date, "2026-08-02"); // to the top: 91
  assert.equal(moved(1, 1)[2].date, "2026-08-02"); // 80 -> 65, between 70 and 60
  assert.equal(moved(2, 1)[3].date, "2026-08-03"); // to the bottom: 59
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
