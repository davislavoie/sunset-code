import { test } from "node:test";
import assert from "node:assert/strict";
import { step, withAuto } from "./myRank.js";

test("arrows step the score half a point, within 0-100", () => {
  assert.equal(step(61.23, -1), 61.73);
  assert.equal(step(61.23, 1), 60.73);
  assert.equal(step(99.8, -1), 100);
  assert.equal(step(0.2, 1), 0);
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
