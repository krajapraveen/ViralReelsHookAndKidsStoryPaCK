/**
 * Safe URL/path/query builders — P1 2026-05-19 reliability sweep
 * =================================================================
 *
 * These builders are the canonical way to assemble URLs that contain
 * any value derived from handler arguments, deep-linked URL params,
 * or user-controlled state. They REFUSE to encode React events,
 * objects, arrays, nulls into URL path segments or query strings.
 *
 * Use these whenever the value going into a URL might originate from:
 *   • a default-arg handler parameter
 *   • a deep-link useSearchParams() value
 *   • a remote API response field
 *
 * `encodeURIComponent` is NOT validation. It will happily encode
 * `[object Object]` and `'undefined'` and ship them to the backend.
 * These builders validate FIRST, then encode.
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

// ─── Beacon (debounced, shared shape with peer guards) ──────────────
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
function _emit(meta) {
  try {
    _queue.push({
      metric: 'frontend_event_trap_blocked_total',
      ts: Date.now(),
      page: typeof window !== 'undefined' ? window.location.pathname : 'ssr',
      meta,
    });
    if (!_scheduled) {
      _scheduled = true;
      setTimeout(_flush, 1500);
    }
  } catch (_) { /* noop */ }
}

// ─── Constants ──────────────────────────────────────────────────────
const PATH_ID_RE = /^[A-Za-z0-9_-]{1,128}$/;
const QUERY_VALUE_MAX_LEN = 512;

/**
 * Throws (in dev) or returns null (in prod) when an ID destined for a
 * URL path segment isn't a safe string. NEVER returns an
 * encoded-but-broken value.
 *
 * @param {*} value         Candidate path-segment value.
 * @param {string} fieldName  For diagnostics only.
 * @returns {string|null} A validated, encoded path segment (or null).
 */
export function safePathId(value, fieldName = 'id') {
  if (_looksLikeReactEvent(value)) {
    console.error('[safeUrl] BLOCKED React event in path segment', { fieldName });
    _emit({ reason: 'url_path_event', field: fieldName });
    return null;
  }
  if (typeof value !== 'string') {
    if (value != null) {
      console.warn('[safeUrl] non-string in path segment dropped', { fieldName, type: typeof value });
      _emit({ reason: 'url_path_nonstring', field: fieldName, type: typeof value });
    }
    return null;
  }
  const trimmed = value.trim();
  if (!PATH_ID_RE.test(trimmed)) {
    console.warn('[safeUrl] path segment failed validation', { fieldName });
    _emit({ reason: 'url_path_invalid', field: fieldName });
    return null;
  }
  return encodeURIComponent(trimmed);
}

/**
 * Coerce a single query-string value. Accepts strings, finite numbers,
 * and booleans. Rejects everything else.
 */
export function safeQueryParam(value, fieldName = 'param') {
  if (_looksLikeReactEvent(value)) {
    console.error('[safeUrl] BLOCKED React event in query value', { fieldName });
    _emit({ reason: 'url_query_event', field: fieldName });
    return null;
  }
  if (typeof value === 'string') {
    const trimmed = value.trim();
    if (!trimmed || trimmed.length > QUERY_VALUE_MAX_LEN) return null;
    return trimmed;
  }
  if (typeof value === 'number' && Number.isFinite(value)) {
    return String(value);
  }
  if (typeof value === 'boolean') {
    return value ? 'true' : 'false';
  }
  if (value != null) {
    console.warn('[safeUrl] non-primitive in query value dropped', { fieldName, type: typeof value });
    _emit({ reason: 'url_query_nonprimitive', field: fieldName, type: typeof value });
  }
  return null;
}

/**
 * Build a query-string from an object of primitives. Keys are restricted
 * to an `allowlist` (an Array or Set of allowed key strings) so a
 * misspelling can't leak unintended params. Values are routed through
 * `safeQueryParam`. Drops null/undefined/invalid entries.
 *
 * @param {object} obj        Raw param object.
 * @param {Iterable<string>} allowlist  Allowed keys.
 * @returns {URLSearchParams}
 */
export function safeUrlParams(obj, allowlist) {
  const allowed = allowlist instanceof Set ? allowlist : new Set(allowlist || []);
  const out = new URLSearchParams();
  if (!obj || typeof obj !== 'object') return out;
  for (const [k, v] of Object.entries(obj)) {
    if (!allowed.has(k)) {
      console.warn('[safeUrl] dropping non-allowlisted query key', { key: k });
      continue;
    }
    const safe = safeQueryParam(v, k);
    if (safe != null) out.set(k, safe);
  }
  return out;
}

/**
 * Build a download/share URL safely. `base` is a trusted prefix
 * (no template-literal interpolation), `pathParts` is an array of
 * raw ID values that get validated + encoded, and `query` is routed
 * through `safeUrlParams` with the supplied allowlist.
 *
 * @returns {string|null} The composed URL, or null if any segment is unsafe.
 */
export function safeDownloadUrl(base, pathParts = [], query = null, queryAllowlist = []) {
  if (typeof base !== 'string' || !base) return null;
  const parts = [];
  for (let i = 0; i < pathParts.length; i++) {
    const part = pathParts[i];
    const safe = safePathId(part, `segment_${i}`);
    if (safe === null) return null;
    parts.push(safe);
  }
  let url = base.endsWith('/') ? base : `${base}/`;
  if (parts.length > 0) url = base + (base.endsWith('/') ? '' : '/') + parts.join('/');
  if (query && typeof query === 'object') {
    const params = safeUrlParams(query, queryAllowlist);
    const qs = params.toString();
    if (qs) url = `${url}?${qs}`;
  }
  return url;
}
