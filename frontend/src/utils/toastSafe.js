/**
 * Toast Safety Layer — P1 2026-05-19 reliability sweep
 * ======================================================
 *
 * Two guarantees:
 *   1. NEVER leak internal implementation jargon into a user-facing
 *      toast (e.g. "frontend rejected style=object", "[object Object]",
 *      "validator error", "stack trace", "unsupported enum").
 *   2. ALWAYS surface a Reference ID so support can correlate. When
 *      the backend provided an `X-Request-Id` (or `request_id` in the
 *      error envelope) we use that. Otherwise we mint a stable local
 *      reference and emit `error_toast_without_request_id_total` so
 *      ops can see when correlation is being lost.
 *
 * Usage:
 *   import { toastErrorSafe } from '../utils/toastSafe';
 *
 *   toastErrorSafe('Could not generate your comic. Please try again.', {
 *     requestId: error?.response?.data?.detail?.request_id,
 *     code: error?.response?.data?.detail?.code,
 *     page: 'photo-to-comic',
 *   });
 */

import { toast } from 'sonner';

/* eslint-disable no-console */

// Phrases that MUST NOT appear in user-facing toast text. If the caller
// accidentally passes a string containing one, we rewrite to a safe
// fallback and log the offender to the console.
const LEAKY_PHRASES = [
  'frontend rejected',
  'style=object',
  '[object Object]',
  'unsupported enum',
  'validator',
  'stack trace',
  'not-captured (frontend',
  'undefined is not',
  'cannot read property',
  'cannot read properties',
  'TypeError:',
  'ReferenceError:',
  'Traceback',
];

const SAFE_FALLBACK = 'Something went wrong. Please try again.';

function _scrubMessage(message) {
  if (typeof message !== 'string' || !message) {
    return { safe: SAFE_FALLBACK, scrubbed: true };
  }
  const lowered = message.toLowerCase();
  for (const phrase of LEAKY_PHRASES) {
    if (lowered.includes(phrase.toLowerCase())) {
      console.error('[toastSafe] SCRUBBED leaky message', { offender: phrase, original: message });
      return { safe: SAFE_FALLBACK, scrubbed: true };
    }
  }
  return { safe: message, scrubbed: false };
}

let _localRefCounter = 0;
function _mintLocalRefId(prefix = 'ui') {
  _localRefCounter += 1;
  return `${prefix}-${Date.now().toString(36)}-${_localRefCounter.toString(36)}`;
}

// Fire-and-forget metric beacon (mirrors eventTrapGuard's contract).
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
        .catch(() => { /* swallow */ });
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
      setTimeout(_flushBeacons, 1500);
    }
  } catch (_) { /* noop */ }
}

/**
 * Display a safe error toast. Strips internal jargon and always surfaces
 * a Reference ID.
 *
 * @param {string} message  User-safe message.
 * @param {object} [opts]
 * @param {string} [opts.requestId]  Backend X-Request-Id / request_id.
 * @param {string} [opts.code]       Structured error code (logged only).
 * @param {string} [opts.page]       Page slug for metrics (e.g. 'photo-to-comic').
 * @param {number} [opts.duration]   Toast duration in ms (default 5000).
 * @param {string} [opts.id]         Toast dedup id.
 * @param {string} [opts.refPrefix]  Reference ID prefix when minting locally.
 */
export function toastErrorSafe(message, opts = {}) {
  const { safe } = _scrubMessage(message);
  const requestId = (typeof opts.requestId === 'string' && opts.requestId.trim()) || null;
  let refId = requestId;
  if (!refId) {
    refId = _mintLocalRefId(opts.refPrefix || 'ui');
    _emit('error_toast_without_request_id_total', {
      page: opts.page || null,
      code: opts.code || null,
      mintedRefId: refId,
    });
  }
  const finalText = `${safe}\nReference ID: ${refId}`;
  // Log the structured form so support has full context.
  console.error('[toastSafe] error_toast', {
    message: safe,
    requestId,
    refId,
    code: opts.code || null,
    page: opts.page || null,
  });
  return toast.error(finalText, {
    duration: opts.duration ?? 5000,
    id: opts.id,
  });
}

/** Lightweight convenience: pull request_id out of an axios error envelope. */
export function extractRequestId(err) {
  try {
    const d = err?.response?.data?.detail;
    if (typeof d === 'object' && d && typeof d.request_id === 'string') {
      return d.request_id;
    }
    const data = err?.response?.data;
    if (typeof data?.request_id === 'string') return data.request_id;
    const hdrs = err?.response?.headers || {};
    return hdrs['x-request-id'] || hdrs['X-Request-Id'] || null;
  } catch (_) {
    return null;
  }
}
