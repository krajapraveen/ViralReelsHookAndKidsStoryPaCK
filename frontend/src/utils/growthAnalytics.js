/**
 * Growth Analytics — Client-side event tracking
 * Tracks funnel: page_view → remix_click → tool_open_prefilled → generate_click → signup → creation_completed
 */

const API = process.env.REACT_APP_BACKEND_URL;

// Persistent session ID (survives page refreshes within a session)
function getSessionId() {
  let sid = sessionStorage.getItem('growth_session_id');
  if (!sid) {
    sid = `gs_${Date.now()}_${Math.random().toString(36).slice(2, 10)}`;
    sessionStorage.setItem('growth_session_id', sid);
  }
  return sid;
}

// Queue for batching events (sends every 5s or on 10 events)
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
    // Silent fail — analytics should never break UX
    eventQueue.push(...batch); // Re-queue on failure
  }
}

function scheduleFlush() {
  if (flushTimer) return;
  flushTimer = setTimeout(() => {
    flushTimer = null;
    flushEvents();
  }, 5000);
}

// Flush on page unload
if (typeof window !== 'undefined') {
  window.addEventListener('beforeunload', () => flushEvents());
}

/**
 * Track a growth event
 * @param {string} event - Event name
 * @param {object} data - Additional data (source_slug, tool, meta)
 */
export function trackGrowthEvent(event, data = {}) {
  const sessionId = getSessionId();
  const userId = localStorage.getItem('user_id') || null;

  eventQueue.push({
    event,
    session_id: sessionId,
    source_slug: data.source_slug || null,
    tool: data.tool || null,
    user_id: userId,
    meta: data.meta || null,
  });

  // Flush immediately for critical events, batch for others
  if (['signup_completed', 'creation_completed'].includes(event)) {
    flushEvents();
  } else if (eventQueue.length >= 10) {
    flushEvents();
  } else {
    scheduleFlush();
  }
}

// ─── Convenience functions for each funnel stage ─────────────────────────────

export function trackPageView(slug) {
  trackGrowthEvent('page_view', { source_slug: slug });
}

export function trackRemixClick(slug, tool) {
  trackGrowthEvent('remix_click', { source_slug: slug, tool });
}

export function trackToolOpenPrefilled(tool, sourceSlug) {
  trackGrowthEvent('tool_open_prefilled', { tool, source_slug: sourceSlug });
}

export function trackGenerateClick(tool) {
  trackGrowthEvent('generate_click', { tool });
}

export function trackSignupTriggered() {
  trackGrowthEvent('signup_triggered');
}

export function trackSignupCompleted() {
  trackGrowthEvent('signup_completed');
}

export function trackCreationCompleted(tool) {
  trackGrowthEvent('creation_completed', { tool });
}

export function trackShareClick(slug, platform) {
  trackGrowthEvent('share_click', { source_slug: slug, meta: { platform } });
}
