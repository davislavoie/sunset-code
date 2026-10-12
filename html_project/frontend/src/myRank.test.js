import { test } from "node:test";
import assert from "node:assert/strict";
import { byScore, nudge } from "./myRank.js";

const list = [90, 80, 70, 60].map((score, i) => ({ date: `2026-08-0${i + 1}`, score }));
const moved = (i, dir) => list.map((r, j) => (j === i ? { ...r, score: nudge(list, i, dir) } : r)).sort(byScore);

test("arrows move a day exactly one place", () => {
  assert.equal(moved(2, -1)[1].score, 85); // 70 slots between 90 and 80
  assert.equal(moved(1, -1)[0].date, "2026-08-02"); // to the top: 91
  assert.equal(moved(1, 1)[2].date, "2026-08-02"); // 80 -> 65, between 70 and 60
  assert.equal(moved(2, 1)[3].date, "2026-08-03"); // to the bottom: 59
});
