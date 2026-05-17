/**
 * Event-Trap Guard — P1 2026-05-19 reliability sweep
 * ====================================================
 *
 * React passes a SyntheticEvent as the first arg when a handler is wired
 * as `onClick={handlerName}` (no arrow). If the handler signature is
 * `(maybeArg = someDefault) => ...`, the truthy event silently overwrites
 * the default and downstream logic explodes. Photo-to-Comic's
 * "frontend rejected style=object" toast was caused by exactly this trap.
 *
 * `dropEventArg(arg)` is a one-liner defense-in-depth shim every handler
 * with a non-event default arg should run as the first statement.
 *
 *   const handleX = async (overrideId = null) => {
 *     overrideId = dropEventArg(overrideId, 'string');
 *     // ... use overrideId normally; it's now null if it was an event ...
 *   };
 *
 * Returns `arg` unchanged when it matches the expected type, or `null`
 * for any non-matching input (React event, plain object, function, etc.).
 *
 * Also emits a beacon to the backend `frontend_event_trap_blocked_total`
 * counter so we can prove this guard is doing work in production.
 */

/* eslint-disable no-console */

const REACT_EVENT_KEYS = [
  '_reactName',
  'nativeEvent',
  'isDefaultPrevented',
  'isPropagationStopped',
];

function looksLikeReactEvent(v) {
  if (!v || typeof v !== 'object') return false;
  for (const k of REACT_EVENT_KEYS) {
    if (k in v) return true;
  }
  return false;
}

// Fire-and-forget beacon. Imported lazily to avoid circular deps with api.js.
let _beaconQueue = [];
let _beaconScheduled = false;
function _flushBeacons() {
  _beaconScheduled = false;
  if (_beaconQueue.length === 0) return;
  const batch = _beaconQueue;
  _beaconQueue = [];
  import('./api')
    .then(({ default: api }) => {
      api
        .post('/api/diagnostics/beacon', { events: batch })
        .catch(() => { /* swallow — beacons must never break UX */ });
    })
    .catch(() => { /* swallow */ });
}
function _emit(metric, meta) {
  try {
    _beaconQueue.push({
      metric,
      ts: Date.now(),
      page: typeof window !== 'undefined' ? window.location.pathname : 'ssr',
      meta: meta || null,
    });
    if (!_beaconScheduled) {
      _beaconScheduled = true;
      // Debounce so a flurry of clicks doesn't spam the backend.
      setTimeout(_flushBeacons, 1500);
    }
  } catch (_) { /* noop */ }
}

/**
 * Drop a React SyntheticEvent (or any non-matching value) from a handler
 * arg slot. Returns `null` when the arg is unsafe.
 *
 * @param {*} arg
 * @param {('string'|'number'|'object'|'any')} expectType
 * @param {{ handler?: string, callSite?: string }} [meta]
 */
export function dropEventArg(arg, expectType = 'string', meta = {}) {
  if (looksLikeReactEvent(arg)) {
    console.error('[event-trap-guard] BLOCKED React SyntheticEvent reached handler', meta);
    _emit('frontend_event_trap_blocked_total', { ...meta, reason: 'react_event' });
    return null;
  }
  if (expectType === 'any') return arg;
  if (expectType === 'string') {
    if (typeof arg === 'string' && arg.trim().length > 0) return arg;
    if (arg == null) return null;
    console.warn('[event-trap-guard] non-string arg dropped', { ...meta, type: typeof arg });
    _emit('frontend_event_trap_blocked_total', { ...meta, reason: 'wrong_type', type: typeof arg });
    return null;
  }
  if (expectType === 'number') {
    if (typeof arg === 'number' && Number.isFinite(arg)) return arg;
    if (arg == null) return null;
    _emit('frontend_event_trap_blocked_total', { ...meta, reason: 'wrong_type', type: typeof arg });
    return null;
  }
  if (expectType === 'object') {
    if (arg && typeof arg === 'object' && !looksLikeReactEvent(arg)) return arg;
    return null;
  }
  return null;
}
