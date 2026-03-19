/**
 * Growth Analytics — Client-side event tracking
 * Strict event contract with attribution lineage.
 * 
 * 6 core events:
 * 1. page_view (public pages)
 * 2. remix_click (CTA on public pages)
 * 3. tool_open_prefilled (tool opened with remix data)
 * 4. generate_click (user clicks generate)
 * 5. signup_completed (user finishes signup)
 * 6. creation_completed (generation finishes successfully)
 * 7. share_click (user shares content)
 */

const API = process.env.REACT_APP_BACKEND_URL;

// ─── Session Management ──────────────────────────────────────────────────────

function getSessionId() {
  let sid = sessionStorage.getItem('growth_session_id');
  if (!sid) {
    sid = `gs_${Date.now()}_${Math.random().toString(36).slice(2, 10)}`;
    sessionStorage.setItem('growth_session_id', sid);
  }
  return sid;
}

function getAnonymousId() {
  let aid = localStorage.getItem('growth_anonymous_id');
  if (!aid) {
    aid = `anon_${Date.now()}_${Math.random().toString(36).slice(2, 10)}`;
    localStorage.setItem('growth_anonymous_id', aid);
  }
  return aid;
}

function getUserId() {
  return localStorage.getItem('user_id') || null;
}

// ─── Origin Tracking ─────────────────────────────────────────────────────────
// Persists across page navigations within the session

function setOrigin(origin, data = {}) {
  sessionStorage.setItem('growth_origin', JSON.stringify({
    origin,
    origin_slug: data.slug || null,
    origin_character_id: data.character_id || null,
    origin_series_id: data.series_id || null,
  }));
}

function getOrigin() {
  try {
    return JSON.parse(sessionStorage.getItem('growth_origin') || '{}');
  } catch {
    return {};
  }
}

// ─── Idempotency ─────────────────────────────────────────────────────────────

const recentEvents = new Set();

function makeIdempotencyKey(event, extra = '') {
  // Debounce: same event + same extra within 2 seconds = duplicate
  const key = `${event}_${extra}_${Math.floor(Date.now() / 2000)}`;
  if (recentEvents.has(key)) return null; // duplicate
  recentEvents.add(key);
  // Clean up old keys
  if (recentEvents.size > 100) {
    const arr = Array.from(recentEvents);
    arr.slice(0, 50).forEach(k => recentEvents.delete(k));
  }
  return key;
}

// ─── Event Queue with Batching ───────────────────────────────────────────────

let eventQueue = [];
let flushTimer = null;

async function flushEvents() {
  if (eventQueue.length === 0) return;
  const batch = [...eventQueue];
  eventQueue = [];

  try {
    await fetch(`${API}/api/growth/events/batch`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ events: batch }),
    });
  } catch {
    // Re-queue on failure (silent — never break UX)
    eventQueue.push(...batch);
  }
}

function scheduleFlush() {
  if (flushTimer) return;
  flushTimer = setTimeout(() => {
    flushTimer = null;
    flushEvents();
  }, 5000);
}

if (typeof window !== 'undefined') {
  window.addEventListener('beforeunload', () => flushEvents());
}

// ─── Core Track Function ─────────────────────────────────────────────────────

function trackGrowthEvent(event, data = {}) {
  const idempotencyKey = makeIdempotencyKey(event, data.source_page || data.tool_type || '');
  if (!idempotencyKey) return; // deduplicated

  const origin = getOrigin();

  eventQueue.push({
    event,
    session_id: getSessionId(),
    user_id: getUserId(),
    anonymous_id: getAnonymousId(),
    source_page: data.source_page || window.location.pathname,
    source_slug: data.source_slug || null,
    tool_type: data.tool_type || null,
    creation_type: data.creation_type || null,
    series_id: data.series_id || null,
    character_id: data.character_id || null,
    origin: data.origin || origin.origin || 'direct',
    origin_slug: data.origin_slug || origin.origin_slug || null,
    origin_character_id: data.origin_character_id || origin.origin_character_id || null,
    origin_series_id: data.origin_series_id || origin.origin_series_id || null,
    referrer_slug: data.referrer_slug || null,
    ab_variant: null,
    idempotency_key: idempotencyKey,
    meta: data.meta || null,
  });

  // Critical events flush immediately
  if (['signup_completed', 'creation_completed', 'share_click'].includes(event)) {
    flushEvents();
  } else if (eventQueue.length >= 10) {
    flushEvents();
  } else {
    scheduleFlush();
  }
}

// ─── 6 Core Event Functions ──────────────────────────────────────────────────

/** 1. Public page view (explore, character page, series page) */
export function trackPageView(data = {}) {
  trackGrowthEvent('page_view', data);
}

/** 2. Remix/CTA click on public pages */
export function trackRemixClick(data = {}) {
  trackGrowthEvent('remix_click', data);
}

/** 3. Tool opened with prefilled remix data */
export function trackToolOpenPrefilled(data = {}) {
  trackGrowthEvent('tool_open_prefilled', data);
}

/** 4. User clicks Generate button */
export function trackGenerateClick(data = {}) {
  trackGrowthEvent('generate_click', data);
}

/** 5. User completes signup */
export function trackSignupCompleted(data = {}) {
  trackGrowthEvent('signup_completed', data);
}

/** 6. Generation completes successfully */
export function trackCreationCompleted(data = {}) {
  trackGrowthEvent('creation_completed', data);
}

/** 7. Share click (optional) */
export function trackShareClick(data = {}) {
  trackGrowthEvent('share_click', data);
}

// ─── Session Linkage ─────────────────────────────────────────────────────────

/** Call after login/signup to link anonymous session events to the user */
export async function linkSessionToUser(userId) {
  const sessionId = getSessionId();
  try {
    await fetch(`${API}/api/growth/link-session`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId, user_id: userId }),
    });
  } catch {
    // Silent fail
  }
}

// ─── Origin Helpers ──────────────────────────────────────────────────────────

export { setOrigin, getOrigin, getSessionId, getAnonymousId };
