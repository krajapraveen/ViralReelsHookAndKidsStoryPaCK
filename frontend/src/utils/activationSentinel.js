/**
 * Activation Sentinel — global frontend error & UX failure detector.
 * Wires up:
 *  - Uncaught JS errors → uncaught_js_error
 *  - Unhandled promise rejections → uncaught_js_error (kind=promise)
 *  - Slow API responses (>8s) and 4xx/5xx → spinner_over_8_seconds, api_4xx, api_5xx
 *  - Rage clicks (≥4 clicks within 800ms on same target) → rage_click_detected
 *  - Double clicks on the same primary CTA → double_click_detected
 *  - beforeunload while on auth/loading screen → session_abandoned
 *
 * Initialized once at app boot. Idempotent.
 */
import { trackFunnel } from './funnelTracker';

let initialized = false;

export function initActivationSentinel() {
  if (initialized) return;
  initialized = true;

  // ─── 1. Uncaught JS errors ──────────────────────────────────────────────
  window.addEventListener('error', (e) => {
    try {
      trackFunnel('uncaught_js_error', {
        meta: {
          message: (e.message || 'unknown').slice(0, 200),
          source: (e.filename || '').slice(0, 200),
          line: e.lineno,
          col: e.colno,
          kind: 'window.error',
        },
      });
    } catch (_) { /* never throw inside error handler */ }
  });

  window.addEventListener('unhandledrejection', (e) => {
    try {
      const msg = (e.reason && (e.reason.message || String(e.reason))) || 'rejection';
      trackFunnel('uncaught_js_error', {
        meta: { message: String(msg).slice(0, 200), kind: 'promise_rejection' },
      });
    } catch (_) { /* noop */ }
  });

  // ─── 2. Rage clicks + double clicks ─────────────────────────────────────
  const recent = [];
  const RAGE_WINDOW_MS = 800;
  const RAGE_THRESHOLD = 4;

  document.addEventListener('click', (e) => {
    const now = Date.now();
    const target = e.target && e.target.closest ? e.target.closest('button,a,[role="button"]') : null;
    if (!target) return;
    const id = target.getAttribute('data-testid') || target.id || target.tagName;
    recent.push({ id, t: now });
    while (recent.length && now - recent[0].t > RAGE_WINDOW_MS) recent.shift();

    const sameTargetCount = recent.filter((r) => r.id === id).length;
    if (sameTargetCount >= RAGE_THRESHOLD) {
      try {
        trackFunnel('rage_click_detected', {
          meta: { target: id, count: sameTargetCount, page: window.location.pathname },
        });
      } catch (_) { /* noop */ }
      // Drain so we don't spam
      recent.length = 0;
    } else if (sameTargetCount === 2 && (now - (recent[recent.length - 2].t || 0)) < 350) {
      try {
        trackFunnel('double_click_detected', {
          meta: { target: id, page: window.location.pathname },
        });
      } catch (_) { /* noop */ }
    }
  }, true);

  // ─── 3. session_abandoned on hard exit ──────────────────────────────────
  // Only fire if we never reached "story_generation_completed" or "checkout_started"
  // for this session — these are the activation milestones.
  let activated = false;
  const origTrack = trackFunnel;
  // Hook trackFunnel to detect activation milestones
  const ACTIVATION_MILESTONES = new Set([
    'story_generation_completed',
    'checkout_started',
    'payment_success',
  ]);
  // We can't monkeypatch the imported function reliably; instead listen to fetch events.
  // Simple proxy: a global flag set via `window.__activated__ = true` from caller.
  window.__markActivated__ = () => { activated = true; };

  window.addEventListener('beforeunload', () => {
    if (!activated) {
      // sendBeacon for reliable delivery during unload
      try {
        const sessionId = sessionStorage.getItem('vs_funnel_session') || 'anon';
        const userId = (() => {
          try {
            const t = localStorage.getItem('token');
            if (!t) return null;
            const payload = JSON.parse(atob(t.split('.')[1]));
            return payload?.user_id || null;
          } catch (_) { return null; }
        })();
        const body = JSON.stringify({
          step: 'session_abandoned',
          session_id: sessionId,
          user_id: userId,
          context: {
            source_page: window.location.pathname,
            page: window.location.pathname,
            time_on_page_ms: Date.now() - (Number(sessionStorage.getItem('landing_ts_ms')) || Date.now()),
          },
        });
        navigator.sendBeacon &&
          navigator.sendBeacon(
            (process.env.REACT_APP_BACKEND_URL || '') + '/api/funnel/track',
            new Blob([body], { type: 'application/json' })
          );
      } catch (_) { /* noop */ }
    }
  });

  // ─── 4. Spinner watchdog (>8s on same screen with no progress) ──────────
  // Lightweight implementation: any data-testid="loading-*" present continuously
  // for >8s fires the event.
  let spinnerStart = null;
  let spinnerFired = false;
  setInterval(() => {
    const spinner = document.querySelector('[data-testid^="loading-"], [aria-busy="true"]');
    if (spinner) {
      if (!spinnerStart) spinnerStart = Date.now();
      if (!spinnerFired && Date.now() - spinnerStart > 8000) {
        spinnerFired = true;
        try {
          trackFunnel('spinner_over_8_seconds', {
            meta: { page: window.location.pathname, elapsed_ms: Date.now() - spinnerStart },
          });
        } catch (_) { /* noop */ }
      }
    } else {
      spinnerStart = null;
      spinnerFired = false;
    }
  }, 2000);
}

// Helpers for callers that wrap fetch/axios
export function reportApiResponse({ status, url, durationMs }) {
  try {
    if (status >= 400 && status < 500) {
      trackFunnel('api_4xx', { meta: { status, url: String(url).slice(0, 200), duration_ms: durationMs } });
    } else if (status >= 500) {
      trackFunnel('api_5xx', { meta: { status, url: String(url).slice(0, 200), duration_ms: durationMs } });
    } else if (status === 0) {
      trackFunnel('api_5xx', { meta: { status: 'network_error', url: String(url).slice(0, 200), duration_ms: durationMs } });
    }
    if (durationMs > 8000) {
      trackFunnel('spinner_over_8_seconds', { meta: { url: String(url).slice(0, 200), duration_ms: durationMs } });
    }
  } catch (_) { /* never break UI on tracking */ }
}

export function markActivated() {
  if (typeof window !== 'undefined' && typeof window.__markActivated__ === 'function') {
    window.__markActivated__();
  }
}

export default { initActivationSentinel, reportApiResponse, markActivated };
