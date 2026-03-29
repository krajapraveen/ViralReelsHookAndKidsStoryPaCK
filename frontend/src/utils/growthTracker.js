/**
 * Growth Loop Event Tracker
 * Tracks ONLY: impression, click, watch_start, watch_complete, continue, share, signup_from_share
 */
const API = process.env.REACT_APP_BACKEND_URL;

let sessionId = sessionStorage.getItem('growth_session');
if (!sessionId) {
  sessionId = crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random().toString(36).slice(2)}`;
  sessionStorage.setItem('growth_session', sessionId);
}

const queue = [];
let flushTimer = null;

function flush() {
  if (!queue.length) return;
  const batch = queue.splice(0, 50);
  const token = localStorage.getItem('token');
  fetch(`${API}/api/growth/events/batch`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    body: JSON.stringify({ events: batch }),
    keepalive: true,
  }).catch(() => {});
}

/**
 * Track a growth loop event.
 * @param {'impression'|'click'|'watch_start'|'watch_complete'|'continue'|'share'|'signup_from_share'} event
 * @param {Object} meta - { story_id, story_title, hook_variant, category, location, source_surface }
 */
export function trackLoop(event, meta = {}) {
  const userId = localStorage.getItem('userId') || null;
  queue.push({
    event,
    session_id: sessionId,
    user_id: userId,
    source_page: window.location.pathname,
    meta,
  });
  clearTimeout(flushTimer);
  if (queue.length >= 10) {
    flush();
  } else {
    flushTimer = setTimeout(flush, 3000);
  }
}

// Flush on page unload
if (typeof window !== 'undefined') {
  window.addEventListener('beforeunload', flush);
  window.addEventListener('visibilitychange', () => { if (document.visibilityState === 'hidden') flush(); });
}
