// Paints the pixels the HSV score counts over a photo's sky. The score itself is only computed in
// sunset_code/helpers/sunset_process.py (stored with each capture); this only needs the band limits,
// which come from the same file the Python reads (hsv_score.json, served at /api/scoring-config).

export const COLORS = ["red", "orange", "yellow", "pink"];

const OVERLAY_RGB = {
  red: [255, 0, 0],
  orange: [140, 45, 0], // darker than the sky it marks, or it vanishes into an orange sunset
  yellow: [255, 255, 0],
  pink: [255, 0, 255],
};
const OVERLAY_OPACITY = { red: 0.5, orange: 0.85, yellow: 0.5, pink: 0.5 };

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
 * Paints the counted pixels of the sky (above the camera's horizon, hsv_score.json "sky") of an image.
 * @param {{data: Uint8ClampedArray, width: number, height: number}} image
 * @param {{bands: Record<string, {hue: [number, number], sat_min: number, val_min: number}>}} config hsv_score.json
 * @param {string} [camera] picks the camera's horizon from config.sky
 * @param {Iterable<string>} [show] the bands to paint (default all); coverage always counts every band
 * @returns {{overlay: Uint8ClampedArray, coverage: Record<string, number>}} overlay is RGBA pixels with the
 *   bands blended in; coverage is each band's share of the whole image (0-1), as sunset_process.py stores it.
 */
/** Share of the frame, from the top, that the score counts as sky (same as sunset_process.sky_height). */
export function skyShare(config, camera) {
  const sky = config.sky ?? { default: 0.5 };
  return sky[camera] ?? sky.default;
}

export function paintMasks({ data, width, height }, config, camera, show = COLORS) {
  const { bands } = config;
  const paint = new Set(show);
  const skyHeight = Math.floor(height * skyShare(config, camera));
  const overlay = new Uint8ClampedArray(data);
  const counts = Object.fromEntries(COLORS.map((c) => [c, 0]));

  for (let i = 0; i < skyHeight * width * 4; i += 4) {
    const [h, s, v] = rgbToHsv(data[i], data[i + 1], data[i + 2]);
    // Round like OpenCV's 8-bit HSV conversion so boundary pixels land in the same band as in Python.
    const hue = Math.round(h * 180) % 180;
    const sat = Math.round(s * 255);
    const val = Math.round(v * 255);
    const match = COLORS.find((c) => {
      const b = bands[c];
      return hue >= b.hue[0] && hue <= b.hue[1] && sat >= b.sat_min && val >= b.val_min;
    });
    if (!match) continue;
    counts[match]++;
    if (!paint.has(match)) continue;
    const rgb = OVERLAY_RGB[match], a = OVERLAY_OPACITY[match];
    for (let c = 0; c < 3; c++) {
      overlay[i + c] = Math.round(a * rgb[c] + (1 - a) * data[i + c]);
    }
  }
  const total = width * height;
  return { overlay, coverage: Object.fromEntries(COLORS.map((c) => [c, counts[c] / total])) };
}
