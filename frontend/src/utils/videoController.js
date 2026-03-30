/**
 * Singleton Video Controller — Netflix-grade autoplay management.
 *
 * Rules:
 * - Only 1 video plays at a time
 * - Max 2 plays per 5 seconds (bandwidth protection)
 * - Tracks analytics (impression, play, watch_time, conversion)
 * - Debounced visibility (150ms) prevents scroll chaos
 */

const API = process.env.REACT_APP_BACKEND_URL;

let _activeVideo = null;
let _playTimestamps = []; // rate limiter: timestamps of recent plays

/** Pause any currently playing video and register the new one. */
export function requestPlay(videoEl) {
  if (!videoEl) return false;

  // Rate limit: max 2 plays per 5 seconds
  const now = Date.now();
  _playTimestamps = _playTimestamps.filter(t => now - t < 5000);
  if (_playTimestamps.length >= 2) return false;

  // Pause current active video
  if (_activeVideo && _activeVideo !== videoEl) {
    try { _activeVideo.pause(); } catch (e) { /* noop */ }
  }

  _activeVideo = videoEl;
  _playTimestamps.push(now);

  try {
    const p = videoEl.play();
    if (p && typeof p.catch === 'function') {
      p.catch(() => { /* browser blocked autoplay — noop */ });
    }
    return true;
  } catch (e) {
    return false;
  }
}

/** Release/pause a video if it's the active one. */
export function requestPause(videoEl) {
  if (!videoEl) return;
  try { videoEl.pause(); } catch (e) { /* noop */ }
  if (_activeVideo === videoEl) _activeVideo = null;
}

/** Check if a video element is warm enough to play. readyState >= 2 = HAVE_CURRENT_DATA */
export function isVideoReady(videoEl) {
  return videoEl && videoEl.readyState >= 2;
}

/**
 * Track preview analytics event.
 * Events: preview_impression, preview_play, preview_watch_complete, preview_click
 */
export function trackPreviewEvent(jobId, eventType, extra = {}) {
  if (!jobId || !eventType) return;
  const payload = {
    job_id: jobId,
    event_type: eventType,
    timestamp: new Date().toISOString(),
    ...extra,
  };
  // Fire-and-forget
  fetch(`${API}/api/engagement/preview-event`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${localStorage.getItem('token') || ''}`,
    },
    body: JSON.stringify(payload),
  }).catch(() => {});
}
