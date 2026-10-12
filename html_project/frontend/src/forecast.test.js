import { test } from "node:test";
import assert from "node:assert/strict";
import { accuracy, actualPct, callFor, dailyBests, horizonOf, summary } from "./forecast.js";

const day = (i) => `2026-08-${String(i + 1).padStart(2, "0")}`;
// 12 days whose in-window best is 0..11; the 2h shot scores 99 but is outside the window.
const rows = Array.from({ length: 12 }, (_, i) => [
  { Date: day(i), Label: "01_2h_pre", Score: 99, Forecast: { pct: 90, score: 10, call: "banger" } },
  { Date: day(i), Label: "07_sunset_08-01-2026.jpg", Score: i },
]).flat();

test("daily best counts only the sunset window", () => {
  assert.equal(dailyBests(rows)[day(3)], 3);
});

test("actual percentile uses earlier days only and needs 10 of them", () => {
  const bests = dailyBests(rows);
  assert.equal(actualPct(bests, day(5)), null);
  assert.equal(actualPct(bests, day(11)), 100);
  assert.equal(actualPct(bests, day(10)), 100);
});

test("calls and accuracy", () => {
  assert.deepEqual([10, 40, 70, 95].map(callFor), ["poor", "maybe", "good", "banger"]);
  assert.deepEqual(accuracy(90, 100), { verdict: "Hit", points: 10 });
  assert.deepEqual(accuracy(70, 90), { verdict: "Close", points: 20 });
  assert.deepEqual(accuracy(10, 90), { verdict: "Miss", points: 80 });
  assert.equal(accuracy(null, 50), null);
});

test("horizon labels, old date-suffixed ones too", () => {
  assert.equal(horizonOf("02_1h_pre_05-16-2025.jpg"), "02_1h_pre");
  assert.equal(horizonOf("06_5m_pre"), "06_5m_pre");
  assert.equal(horizonOf("07_sunset"), null);
});

test("summary counts days with an actual result", () => {
  assert.deepEqual(summary(rows), { "01_2h_pre": { days: 2, Hit: 2, Close: 0, Miss: 0 } });
});
