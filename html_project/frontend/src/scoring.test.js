import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { paintMasks } from "./scoring.js";

// The same file sunset_process.py reads.
const config = JSON.parse(readFileSync(new URL("../../../sunset_code/helpers/hsv_score.json", import.meta.url)));

// 2x2 image: top row is the sky, bottom row the ground (ignored).
function solid(rgb) {
  const data = new Uint8ClampedArray(16);
  for (let i = 0; i < 16; i += 4) data.set([...rgb, 255], i);
  return { data, width: 2, height: 2 };
}

test("only the sky half is painted and counted", () => {
  const { overlay, coverage } = paintMasks(solid([255, 0, 0]), config);
  assert.equal(coverage.red, 0.5); // the whole sky, out of the whole image, as sunset_process.py stores it
  assert.deepEqual([...overlay.slice(8, 12)], [255, 0, 0, 255]);
});

test("grey sky is left untouched", () => {
  const img = solid([128, 128, 128]);
  const { overlay, coverage } = paintMasks(img, config);
  assert.equal(coverage.red + coverage.orange + coverage.yellow + coverage.pink, 0);
  assert.deepEqual(overlay, img.data);
});

test("hue is rounded like OpenCV, so boundary pixels match the Python scorer", () => {
  // rgb(255, 65, 0) has hue 7.65 on OpenCV's 0-180 scale: OpenCV rounds it to 8 (orange, not red).
  const { coverage } = paintMasks(solid([255, 65, 0]), config);
  assert.equal(coverage.red, 0);
  assert.ok(coverage.orange > 0);
});

test("near-black pixels and dim mauve cloud aren't counted", () => {
  assert.equal(paintMasks(solid([30, 2, 2]), config).coverage.red, 0); // ~12% bright: noise
  assert.equal(paintMasks(solid([100, 70, 100]), config).coverage.pink, 0); // pink hue, under half brightness
  assert.ok(paintMasks(solid([255, 0, 200]), config).coverage.pink > 0);
});

test("only the chosen bands are painted, but every band is counted", () => {
  const img = solid([255, 0, 0]);
  const { overlay, coverage } = paintMasks(img, config, undefined, []);
  assert.deepEqual([...overlay.slice(0, 4)], [...img.data.slice(0, 4)]);
  assert.ok(coverage.red > 0);
});
