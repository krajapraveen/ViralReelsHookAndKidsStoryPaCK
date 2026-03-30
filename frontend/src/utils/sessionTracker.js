/**
 * Session Tracker — Lightweight session lifecycle management.
 * Sends: session_start (mount), heartbeat (every 30s), session_end (unmount/tab close).
 * Tracks: session duration, scroll depth, action count.
 */

const API = process.env.REACT_APP_BACKEND_URL;

let _sessionId = null;
let _heartbeatInterval = null;
let _scrollDepth = 0;
let _actionCount = 0;
let _device = 'unknown';

function generateSessionId() {
  return `s_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
}

function detectDevice() {
  if (typeof window === 'undefined') return 'unknown';
  return /Mobi|Android|iPhone|iPad/i.test(navigator.userAgent) ? 'mobile' : 'desktop';
}

function sendSessionEvent(event, extra = {}) {
  if (!_sessionId) return;
  const payload = {
    session_id: _sessionId,
    event,
    device: _device,
    scroll_depth: _scrollDepth,
    actions: _actionCount,
    ...extra,
  };
  // Use sendBeacon for end events (reliable on tab close)
  if (event === 'end' && navigator.sendBeacon) {
    navigator.sendBeacon(
      `${API}/api/admin/retention/session`,
      new Blob([JSON.stringify(payload)], { type: 'application/json' })
    );
    return;
  }
  fetch(`${API}/api/admin/retention/session`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
    keepalive: true,
  }).catch(() => {});
}

/** Call on Dashboard mount. Starts session tracking. */
export function startSession() {
  _sessionId = generateSessionId();
  _device = detectDevice();
  _scrollDepth = 0;
  _actionCount = 0;

  sendSessionEvent('start');

  // Heartbeat every 30s
  _heartbeatInterval = setInterval(() => {
    sendSessionEvent('heartbeat');
  }, 30000);

  // Track scroll depth
  const onScroll = () => {
    const depth = Math.floor(window.scrollY / window.innerHeight);
    if (depth > _scrollDepth) _scrollDepth = depth;
  };
  window.addEventListener('scroll', onScroll, { passive: true });

  // End session on tab close / visibility change
  const onEnd = () => {
    sendSessionEvent('end');
    cleanup();
  };
  const onVisChange = () => {
    if (document.visibilityState === 'hidden') {
      sendSessionEvent('heartbeat'); // save progress
    }
  };

  window.addEventListener('beforeunload', onEnd);
  document.addEventListener('visibilitychange', onVisChange);

  // Store cleanup refs
  window.__sessionCleanup = () => {
    window.removeEventListener('scroll', onScroll);
    window.removeEventListener('beforeunload', onEnd);
    document.removeEventListener('visibilitychange', onVisChange);
    cleanup();
  };

  return _sessionId;
}

function cleanup() {
  if (_heartbeatInterval) {
    clearInterval(_heartbeatInterval);
    _heartbeatInterval = null;
  }
}

/** Call on Dashboard unmount. */
export function endSession() {
  sendSessionEvent('end');
  if (window.__sessionCleanup) {
    window.__sessionCleanup();
    window.__sessionCleanup = null;
  }
  _sessionId = null;
}

/** Increment action counter (call on any user interaction). */
export function trackAction() {
  _actionCount++;
}

/** Update scroll depth externally. */
export function updateScrollDepth(depth) {
  if (depth > _scrollDepth) _scrollDepth = depth;
}
