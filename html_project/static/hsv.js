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

export function applyHsvMask(imageData, hMin, hMax, sMin, sMax, vMin, vMax) {
  const data = imageData.data;
  for (let i = 0; i < data.length; i += 4) {
    const [h, s, v] = rgbToOpenCvHsv(data[i], data[i + 1], data[i + 2]);
    const inRange = h >= hMin && h <= hMax && s >= sMin && s <= sMax && v >= vMin && v <= vMax;
    if (!inRange) {
      data[i] = 0;
      data[i + 1] = 0;
      data[i + 2] = 0;
    }
  }
  return imageData;
}

/** Draws `img` onto `canvas`, downscaling to maxWidth if wider (mirrors the
 * cv2.resize calls in hsv_tuner.py for gallery/uploaded images). */
export function drawResized(img, canvas, maxWidth) {
  let w = img.naturalWidth || img.width;
  let h = img.naturalHeight || img.height;
  if (maxWidth && w > maxWidth) {
    const ratio = h / w;
    w = maxWidth;
    h = Math.round(maxWidth * ratio);
  }
  canvas.width = w;
  canvas.height = h;
  canvas.getContext("2d").drawImage(img, 0, 0, w, h);
}

/** Reads pixels from `sourceCanvas`, masks them, draws result into `destCanvas`. */
export function maskCanvas(sourceCanvas, destCanvas, hMin, hMax, sMin, sMax, vMin, vMax) {
  destCanvas.width = sourceCanvas.width;
  destCanvas.height = sourceCanvas.height;
  const srcCtx = sourceCanvas.getContext("2d");
  const imageData = srcCtx.getImageData(0, 0, sourceCanvas.width, sourceCanvas.height);
  const masked = new ImageData(new Uint8ClampedArray(imageData.data), imageData.width, imageData.height);
  applyHsvMask(masked, hMin, hMax, sMin, sMax, vMin, vMax);
  destCanvas.getContext("2d").putImageData(masked, 0, 0);
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
