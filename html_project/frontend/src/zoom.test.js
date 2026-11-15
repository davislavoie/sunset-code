import assert from "node:assert/strict";
import test from "node:test";
import { FIT, MAX_ZOOM, zoomAt } from "./zoom.js";

test("zoomAt keeps the point under the cursor, and stays between fit and the maximum", () => {
  // A point 100 px right of centre: after 2x about the centre it would sit at 200, so the image moves 100 left.
  assert.deepEqual(zoomAt(FIT, 100, -40, 2), { s: 2, x: -100, y: 40 });
  assert.equal(zoomAt({ s: 2, x: -100, y: 40 }, 0, 0, 0.1), FIT);
  assert.equal(zoomAt(FIT, 10, 10, 100).s, MAX_ZOOM);
});
