/**
 * Feed Engagement Tracker — Real-time behavior tracking for the addiction loop.
 *
 * Tracks: card visibility, scroll speed, skip detection, click events.
 * Sends batch events to backend for session momentum + profile updates.
 * Returns session hints (should_rerank, recovery_needed, intensity).
 */

const API = process.env.REACT_APP_BACKEND_URL;

// Scroll speed tracking for dynamic hook timing
let _lastScrollY = 0;
let _lastScrollTime = Date.now();
let _scrollSpeed = 0; // px/ms

export function getScrollSpeed() {
  return _scrollSpeed;
}

/** Call this from a scroll listener to update speed. */
export function updateScrollSpeed() {
  const now = Date.now();
  const dt = now - _lastScrollTime;
  if (dt > 50) { // only measure if 50ms+ gap
    const dy = Math.abs(window.scrollY - _lastScrollY);
    _scrollSpeed = dy / dt; // px/ms
    _lastScrollY = window.scrollY;
    _lastScrollTime = now;
  }
}

/**
 * Get dynamic hook delay based on scroll speed.
 * Fast scroller → show hook instantly (0ms)
 * Slow viewer → delay hook (300-700ms)
 */
export function getDynamicHookDelay() {
  if (_scrollSpeed > 2.0) return 0;      // fast scroller
  if (_scrollSpeed > 0.5) return 200;    // moderate
  return 500;                            // slow/stationary viewer
}

/**
 * Send a feed engagement event to the backend.
 * Returns session state: { momentum, actions, should_rerank, recovery_needed, intensity }
 */
export async function sendFeedEvent(eventType, meta = {}) {
  const token = localStorage.getItem('token') || '';
  try {
    const resp = await fetch(`${API}/api/engagement/feed-event`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({
        event_type: eventType,
        job_id: meta.jobId || null,
        category: meta.category || null,
        hook_text: meta.hookText || null,
        watch_time: meta.watchTime || null,
        scroll_depth: meta.scrollDepth || null,
      }),
    });
    if (resp.ok) {
      const data = await resp.json();
      return data.session || null;
    }
  } catch (e) {
    // Fire-and-forget — don't block UI
  }
  return null;
}

/**
 * Fetch more stories for infinite scroll.
 */
export async function fetchMoreStories(offset = 0, limit = 12) {
  const token = localStorage.getItem('token') || '';
  try {
    const resp = await fetch(`${API}/api/engagement/story-feed/more?offset=${offset}&limit=${limit}`, {
      headers: {
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
    });
    if (resp.ok) {
      return await resp.json();
    }
  } catch (e) {
    // Fail silently — user just won't see more content
  }
  return null;
}

/**
 * Detect if a card was "skipped" based on visibility time.
 * If visible < 1.5s and user scrolled past, it's a skip_fast.
 */
export function wasSkippedFast(visibleMs) {
  return visibleMs < 1500 && visibleMs > 100; // 100ms min to avoid false positives
}
