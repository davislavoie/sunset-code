// Fetch helpers shared by the app shell and pages that load other cameras' data.

import { useEffect, useState } from "react";

export async function getJson(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${url} returned ${res.status} (is the Flask backend running on :8502?)`);
  return res.json();
}

// One request per camera per page load; Flask already caches InfluxDB for 5 minutes.
const cameraData = new Map();
export function fetchCameraData(camera) {
  if (!cameraData.has(camera)) {
    const request = getJson(`/api/data?camera=${encodeURIComponent(camera)}`);
    request.catch(() => cameraData.delete(camera)); // let a failed load be retried
    cameraData.set(camera, request);
  }
  return cameraData.get(camera);
}

let scoringConfig = null;
export function fetchScoringConfig() {
  scoringConfig ??= getJson("/api/scoring-config").catch((e) => {
    scoringConfig = null;
    throw e;
  });
  return scoringConfig;
}

/** Shareable permalink; Flask adds link-preview tags, then it opens the calendar's Day tab. */
export const sunsetPath = (camera, date) => `/sunset/${encodeURIComponent(camera)}/${date}`;
/** The calendar's Day tab for a date (current camera). */
export const dayPath = (date) => `/calendar?view=day&date=${date}`;

/** Gallery images go through the same-origin proxy so canvas code can read their pixels. */
export const proxied = (url) => `/api/image-proxy?url=${encodeURIComponent(url)}`;

/** { data, error } for any camera, independent of the sidebar's selection. */
export function useCameraData(camera) {
  const [state, setState] = useState({ camera: null, data: null, error: null });
  useEffect(() => {
    if (!camera) return;
    let live = true;
    fetchCameraData(camera).then(
      (data) => live && setState({ camera, data, error: null }),
      (e) => live && setState({ camera, data: null, error: e.message }),
    );
    return () => {
      live = false;
    };
  }, [camera]);
  return state.camera === camera ? state : { data: null, error: null };
}

export function useDocumentTitle(title) {
  useEffect(() => {
    if (!title) return;
    const previous = document.title;
    document.title = title;
    return () => {
      document.title = previous;
    };
  }, [title]);
}

