/**
 * Payload-Boundary Coercers — P1 2026-05-19 reliability sweep
 * ==============================================================
 *
 * Drop-in guards for values about to leave the frontend on a network
 * request. Use whenever the value originated from a handler parameter,
 * a deep-linked URL fragment, or any other input that could legally
 * become a React SyntheticEvent or an object literal.
 *
 *   import { coerceString, coerceEnum } from '../utils/payloadCoercers';
 *
 *   const style_id = coerceEnum(maybeStyle, CANONICAL_STYLE_KEYS, {
 *     fallback: 'cartoon_fun',
 *     handler: 'PhotoToComic.handleGenerate',
 *   });
 *   formData.append('style', style_id);   // ← provably-safe string
 *
 * Every coercer routes failures through the existing
 * `frontend_event_trap_blocked_total` beacon so ops can see when a
 * shim is doing work.
 */

/* eslint-disable no-console */

// ─── React-event detector (mirrored from eventTrapGuard) ────────────
const REACT_EVENT_KEYS = [
  '_reactName',
  'nativeEvent',
  'isDefaultPrevented',
  'isPropagationStopped',
];

function _looksLikeReactEvent(v) {
  if (!v || typeof v !== 'object') return false;
  for (const k of REACT_EVENT_KEYS) {
    if (k in v) return true;
  }
  return false;
}

// ─── Beacon (debounced) ─────────────────────────────────────────────
let _queue = [];
let _scheduled = false;
function _flush() {
  _scheduled = false;
  if (_queue.length === 0) return;
  const batch = _queue;
  _queue = [];
  import('./api')
    .then(({ default: api }) => {
      api.post('/api/diagnostics/beacon', { events: batch }).catch(() => {});
    })
    .catch(() => {});
}
function _emit(metric, meta) {
  try {
    _queue.push({
      metric,
      ts: Date.now(),
      page: typeof window !== 'undefined' ? window.location.pathname : 'ssr',
      meta: meta || null,
    });
    if (!_scheduled) {
      _scheduled = true;
      setTimeout(_flush, 1500);
    }
  } catch (_) { /* noop */ }
}

// ─── Coercers ───────────────────────────────────────────────────────

/**
 * Guarantees the returned value is a non-empty trimmed string, or the
 * provided `fallback` (which itself must be a string or null).
 * @param {*} v
 * @param {{ fallback?: string|null, handler?: string, field?: string }} [opts]
 */
export function coerceString(v, opts = {}) {
  const { fallback = null, handler, field } = opts;
  if (typeof v === 'string') {
    const trimmed = v.trim();
    if (trimmed) return trimmed;
  }
  if (_looksLikeReactEvent(v)) {
    console.error('[payloadCoercers] BLOCKED React event reached payload boundary', { handler, field });
    _emit('frontend_event_trap_blocked_total', { handler, field, reason: 'payload_boundary_event' });
  } else if (v != null) {
    console.warn('[payloadCoercers] coerced non-string at payload boundary', { handler, field, type: typeof v });
    _emit('frontend_event_trap_blocked_total', { handler, field, reason: 'payload_boundary_nonstring', type: typeof v });
  }
  return fallback;
}

/**
 * Coerce to a finite number. Returns `fallback` (default `null`) when
 * the value isn't a number-like primitive.
 */
export function coerceNumber(v, opts = {}) {
  const { fallback = null, handler, field } = opts;
  if (typeof v === 'number' && Number.isFinite(v)) return v;
  if (typeof v === 'string' && v.trim() !== '') {
    const n = Number(v);
    if (Number.isFinite(n)) return n;
  }
  if (_looksLikeReactEvent(v)) {
    _emit('frontend_event_trap_blocked_total', { handler, field, reason: 'payload_boundary_event' });
  } else if (v != null) {
    _emit('frontend_event_trap_blocked_total', { handler, field, reason: 'payload_boundary_nonnumber', type: typeof v });
  }
  return fallback;
}

/**
 * Coerce to one of a fixed allow-list. The allow-list MAY be passed as
 * Array, Set, or any iterable of canonical string keys. Returns
 * `fallback` when the value isn't in the set.
 */
export function coerceEnum(v, allowed, opts = {}) {
  const { fallback = null, handler, field } = opts;
  const allowedSet = allowed instanceof Set ? allowed : new Set(allowed);
  const s = coerceString(v, { handler, field });
  if (s !== null && allowedSet.has(s)) return s;
  if (s !== null) {
    _emit('frontend_event_trap_blocked_total', { handler, field, reason: 'enum_miss', value_preview: String(s).slice(0, 32) });
  }
  return fallback;
}

// Slug: matches `lowercase_canonical_keys` / `uuid-style-ids`.
const SLUG_RE = /^[a-z0-9][a-z0-9_-]{1,127}$/i;

/**
 * Coerce to a canonical slug. Trims, lower-bounds length to 2, upper to
 * 128, and matches `^[a-z0-9][a-z0-9_-]{1,127}$/i`.
 */
export function coerceSlug(v, opts = {}) {
  const { fallback = null, handler, field } = opts;
  const s = coerceString(v, { handler, field });
  if (s !== null && SLUG_RE.test(s)) return s;
  if (s !== null) {
    _emit('frontend_event_trap_blocked_total', { handler, field, reason: 'slug_invalid' });
  }
  return fallback;
}

// IDs accept UUIDs, ObjectIds (24 hex), and short canonical handles.
const ID_RE = /^[a-zA-Z0-9_-]{6,128}$/;

/**
 * Coerce to an opaque ID. Strict allow-list of `[a-zA-Z0-9_-]{6,128}`.
 */
export function coerceId(v, opts = {}) {
  const { fallback = null, handler, field } = opts;
  const s = coerceString(v, { handler, field });
  if (s !== null && ID_RE.test(s)) return s;
  if (s !== null) {
    _emit('frontend_event_trap_blocked_total', { handler, field, reason: 'id_invalid' });
  }
  return fallback;
}

/**
 * `safeOr(primary, fallback)` — the safe form of `primary || fallback`
 * when the primary value might be a React event. Returns `primary`
 * ONLY when it's a non-empty trimmed string; otherwise returns
 * `fallback`. Never lets an event or plain object through.
 */
export function safeOr(primary, fallback, opts = {}) {
  const s = coerceString(primary, opts);
  if (s !== null) return s;
  return fallback;
}
