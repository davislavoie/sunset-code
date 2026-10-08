// Per-pixel HSV masking on canvas ImageData, mirrors sunset_code's cv2-based
// masking (apply_hsv_mask in streamlit_project/hsv_tuner.py). Uses OpenCV's
// HSV scale: H 0-179, S/V 0-255.

export function rgbToOpenCvHsv(r, g, b) {
  const rf = r / 255, gf = g / 255, bf = b / 255;
  const max = Math.max(rf, gf, bf);
  const min = Math.min(rf, gf, bf);
  const d = max - min;
  let h = 0;
  if (d !== 0) {
    if (max === rf) h = 60 * (((gf - bf) / d) % 6);
    else if (max === gf) h = 60 * ((bf - rf) / d + 2);
    else h = 60 * ((rf - gf) / d + 4);
  }
  if (h < 0) h += 360;
  const s = max === 0 ? 0 : d / max;
  const v = max;
  return [h / 2, s * 255, v * 255];
}

export function applyHsvMask(imageData, { h_min, h_max, s_min, s_max, v_min, v_max }) {
  const data = imageData.data;
  for (let i = 0; i < data.length; i += 4) {
    const [h, s, v] = rgbToOpenCvHsv(data[i], data[i + 1], data[i + 2]);
    const inRange = h >= h_min && h <= h_max && s >= s_min && s <= s_max && v >= v_min && v <= v_max;
    if (!inRange) {
      data[i] = 0;
      data[i + 1] = 0;
      data[i + 2] = 0;
    }
  }
  return imageData;
}

/** Draws `img` onto a new canvas, downscaling to maxWidth if wider (mirrors the
 * cv2.resize calls in hsv_tuner.py for gallery/uploaded images). */
export function toResizedCanvas(img, maxWidth) {
  let w = img.naturalWidth || img.width;
  let h = img.naturalHeight || img.height;
  if (maxWidth && w > maxWidth) {
    h = Math.round(maxWidth * (h / w));
    w = maxWidth;
  }
  const canvas = document.createElement("canvas");
  canvas.width = w;
  canvas.height = h;
  canvas.getContext("2d").drawImage(img, 0, 0, w, h);
  return canvas;
}

/** Reads pixels from `sourceCanvas`, masks them, draws result into `destCanvas`. */
export function maskCanvas(sourceCanvas, destCanvas, ranges) {
  destCanvas.width = sourceCanvas.width;
  destCanvas.height = sourceCanvas.height;
  const imageData = sourceCanvas.getContext("2d").getImageData(0, 0, sourceCanvas.width, sourceCanvas.height);
  destCanvas.getContext("2d").putImageData(applyHsvMask(imageData, ranges), 0, 0);
}

export function loadImage(src) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.crossOrigin = "anonymous";
    img.onload = () => resolve(img);
    img.onerror = () => reject(new Error("Failed to load image - check if the source is accessible"));
    img.src = src;
  });
}

/** Loads an image and returns its full-size pixels (ImageData). */
export async function loadImageData(src) {
  const img = await loadImage(src);
  const ctx = toResizedCanvas(img, null).getContext("2d");
  return ctx.getImageData(0, 0, ctx.canvas.width, ctx.canvas.height);
}
