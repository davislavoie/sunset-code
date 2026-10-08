// In-browser port of the scorer from static/pages/rankingexplained.js.
// Pure function so it can be tested without a DOM.

export const COLORS = ["red", "orange", "yellow", "pink"];

export const DEFAULT_COLOR_RANGES = {
  red: { hueMin: 0, hueMax: 8, satMin: 20 },
  orange: { hueMin: 8, hueMax: 25, satMin: 20 },
  yellow: { hueMin: 25, hueMax: 35, satMin: 20 },
  pink: { hueMin: 140, hueMax: 179, satMin: 20 },
};

export const DEFAULT_FORMULA = { power: 2.0, divisor: 40 };

const OVERLAY_RGB = {
  red: [255, 0, 0],
  orange: [255, 140, 0],
  yellow: [255, 255, 0],
  pink: [255, 0, 255],
};
const OVERLAY_OPACITY = 0.5;

// Red/orange use an exclusive hueMax so the shared boundary (8, 25) isn't
// double counted; yellow/pink are inclusive. Mirrors the original page.
const EXCLUSIVE_MAX = new Set(["red", "orange"]);

function rgbToHsv(r, g, b) {
  r /= 255; g /= 255; b /= 255;
  const max = Math.max(r, g, b), min = Math.min(r, g, b);
  const d = max - min;
  let h = 0;
  if (d !== 0) {
    if (max === r) h = ((g - b) / d + (g < b ? 6 : 0)) / 6;
    else if (max === g) h = ((b - r) / d + 2) / 6;
    else h = ((r - g) / d + 4) / 6;
  }
  return [h, max === 0 ? 0 : d / max, max];
}

/**
 * Scores the sky (top half) of an image.
 * @param {{data: Uint8ClampedArray, width: number, height: number}} image
 * @returns {{perColor: Record<string, number>, coverage: Record<string, number>,
 *   avgSaturation: Record<string, number>, total: number, overlay: Uint8ClampedArray}}
 *   perColor is points (already multiplied). coverage is the matched share of the whole
 *   image (0-1), the pixel_ratio in sunset_process.py; avgSaturation is 0-255.
 *   overlay is RGBA pixels with color masks blended in.
 */
export function scoreImage({ data, width, height }, { multipliers, colorRanges, formulaParams }) {
  const totalPixels = width * height;
  const skyHeight = Math.floor(height / 2);
  const overlay = new Uint8ClampedArray(data);
  const counts = { red: 0, orange: 0, yellow: 0, pink: 0 };
  const satSums = { red: 0, orange: 0, yellow: 0, pink: 0 };

  for (let i = 0; i < skyHeight * width * 4; i += 4) {
    const [h, s] = rgbToHsv(data[i], data[i + 1], data[i + 2]);
    // Round like OpenCV's 8-bit HSV conversion (sunset_process.py) so pixels on a hue
    // boundary land in the same bucket; without this, scores drift up to ~1 point.
    const hue = Math.round(h * 180) % 180;
    const sat = Math.round(s * 255);

    const match = COLORS.find((color) => {
      const { hueMin, hueMax, satMin } = colorRanges[color];
      const belowMax = EXCLUSIVE_MAX.has(color) ? hue < hueMax : hue <= hueMax;
      return hue >= hueMin && belowMax && sat >= satMin;
    });
    if (!match) continue;

    counts[match]++;
    satSums[match] += sat;
    const rgb = OVERLAY_RGB[match];
    for (let c = 0; c < 3; c++) {
      overlay[i + c] = Math.round(OVERLAY_OPACITY * rgb[c] + (1 - OVERLAY_OPACITY) * data[i + c]);
    }
  }

  const { power, divisor } = formulaParams;
  const perColor = {};
  const coverage = {};
  const avgSaturation = {};
  for (const color of COLORS) {
    coverage[color] = counts[color] / totalPixels;
    avgSaturation[color] = counts[color] > 0 ? satSums[color] / counts[color] : 0;
    // calculate_saturation_weighted_score: pixel_ratio * avg_saturation^power / divisor
    perColor[color] = ((coverage[color] * Math.pow(avgSaturation[color], power)) / divisor) * multipliers[color];
  }
  const total = Math.min(100, COLORS.reduce((sum, color) => sum + perColor[color], 0));

  return { perColor, coverage, avgSaturation, total, overlay };
}
