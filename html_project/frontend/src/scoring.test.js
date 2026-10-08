import { test } from "node:test";
import assert from "node:assert/strict";
import { scoreImage, DEFAULT_COLOR_RANGES, DEFAULT_FORMULA } from "./scoring.js";

const params = {
  multipliers: { red: 4, orange: 3, yellow: 2, pink: 9 },
  colorRanges: DEFAULT_COLOR_RANGES,
  formulaParams: DEFAULT_FORMULA,
};

// 2x2 image: top row pure red (sky), bottom row pure red (ground, ignored).
function solid(rgb) {
  const data = new Uint8ClampedArray(16);
  for (let i = 0; i < 16; i += 4) data.set([...rgb, 255], i);
  return { data, width: 2, height: 2 };
}

test("only the sky half counts", () => {
  const { perColor, total } = scoreImage(solid([255, 0, 0]), params);
  // pixel_ratio = 2/4, avg_sat = 255 -> 0.5 * 255^2 / 40 * 4
  assert.equal(perColor.red, (0.5 * 255 ** 2) / 40 * 4);
  assert.equal(total, 100); // capped
  assert.equal(perColor.pink, 0);
});

test("grey sky scores zero and overlay is untouched", () => {
  const img = solid([128, 128, 128]);
  const { total, overlay } = scoreImage(img, params);
  assert.equal(total, 0);
  assert.deepEqual(overlay, img.data);
});

test("overlay blends matched sky pixels only", () => {
  const { overlay } = scoreImage(solid([255, 0, 255]), params); // magenta -> pink
  assert.deepEqual([...overlay.slice(0, 4)], [255, 0, 255, 255]);
  assert.deepEqual([...overlay.slice(8, 12)], [255, 0, 255, 255]);
});

test("hue is rounded like OpenCV, so boundary pixels match the Python scorer", () => {
  // rgb(255, 65, 0) has hue 7.65 on OpenCV's 0-180 scale: OpenCV rounds it to 8 (orange, not red).
  const { perColor } = scoreImage(solid([255, 65, 0]), params);
  assert.equal(perColor.red, 0);
  assert.ok(perColor.orange > 0);
});

test("reports coverage and average saturation like sunset_process.py", () => {
  const { coverage, avgSaturation } = scoreImage(solid([255, 0, 0]), params);
  assert.equal(coverage.red, 0.5); // whole sky half matched, out of the whole image
  assert.equal(avgSaturation.red, 255);
  assert.equal(coverage.pink, 0);
});
