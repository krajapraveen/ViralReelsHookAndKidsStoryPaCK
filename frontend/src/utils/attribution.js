/**
 * Attribution capture — P0 2026-05-22 Phase A.
 *
 * Captures Google Ads / Meta Ads click-IDs and utm_* parameters on
 * the FIRST page load so they survive every downstream redirect
 * (Cashfree hosted-page, OAuth, etc.). Without this, every paid
 * signup and every paid payment loses its attribution at the
 * redirect boundary.
 *
 * Hard requirements (founder mandate 2026-05-22):
 *   • Capture on first page load — not waiting for signup.
 *   • Persist for 90 days (Google Ads click-ID window).
 *   • Send to backend so the cashfree webhook can stamp it on the
 *     order at payment time.
 *   • Source platform classification carried alongside click-IDs.
 *
 * Restraint: this is the entire attribution module. No session
 * replay, no heatmaps, no behavioral scoring. Minimal truth.
 */

const STORAGE_KEY = 'vs_attribution_v1';
const ANON_KEY = 'vs_anonymous_id';
const TTL_MS = 90 * 24 * 60 * 60 * 1000; // 90 days
const POST_TTL_MS = 24 * 60 * 60 * 1000;  // re-POST at most once per day

const CLICK_ID_PARAMS = ['gclid', 'gbraid', 'wbraid', 'fbclid'];
const UTM_PARAMS = ['utm_source', 'utm_medium', 'utm_campaign', 'utm_content', 'utm_term'];

function _safeStorage() {
  try {
    if (typeof window === 'undefined') return null;
    return window.localStorage;
  } catch (_) {
    return null;
  }
}

function _readJson(key) {
  const ls = _safeStorage();
  if (!ls) return null;
  try {
    const raw = ls.getItem(key);
    return raw ? JSON.parse(raw) : null;
  } catch (_) {
    return null;
  }
}

function _writeJson(key, value) {
  const ls = _safeStorage();
  if (!ls) return;
  try {
    ls.setItem(key, JSON.stringify(value));
  } catch (_) { /* quota */ }
}

function _generateAnonymousId() {
  if (typeof window !== 'undefined' && window.crypto && window.crypto.randomUUID) {
    return window.crypto.randomUUID();
  }
  // Fallback: 32-hex random ID.
  let s = '';
  for (let i = 0; i < 32; i++) s += Math.floor(Math.random() * 16).toString(16);
  return s;
}

export function getAnonymousId() {
  const ls = _safeStorage();
  if (!ls) return _generateAnonymousId();
  let id = ls.getItem(ANON_KEY);
  if (!id) {
    id = _generateAnonymousId();
    try { ls.setItem(ANON_KEY, id); } catch (_) { /* quota */ }
  }
  return id;
}

function _classifySourcePlatform(params, referrer) {
  if (params.gclid || params.gbraid || params.wbraid) return 'google_ads';
  if (params.fbclid) return 'meta_ads';
  const utm = (params.utm_source || '').toLowerCase();
  if (utm.includes('google')) return 'google_ads';
  if (['facebook', 'instagram', 'meta'].includes(utm)) return 'meta_ads';
  if (utm) return 'referral';
  if (referrer && referrer.length > 0) return 'referral';
  return 'direct';
}

function _parseUrlAttribution() {
  if (typeof window === 'undefined') return null;
  try {
    const url = new URL(window.location.href);
    const out = {};
    [...CLICK_ID_PARAMS, ...UTM_PARAMS].forEach((p) => {
      const v = url.searchParams.get(p);
      if (v) out[p] = v;
    });
    return out;
  } catch (_) {
    return {};
  }
}

/**
 * Capture attribution from the current page URL and persist it.
 *
 * Idempotency: never overwrites a stronger signal with a weaker one.
 * If localStorage already has a gclid and the current URL has none,
 * we keep the stored gclid (the click-ID window is up to 90 days).
 *
 * Returns the merged stored attribution object (or null if not
 * available, e.g., during SSR).
 */
export function captureAttribution() {
  const ls = _safeStorage();
  if (!ls || typeof window === 'undefined') return null;

  const now = Date.now();
  const urlAttr = _parseUrlAttribution() || {};
  const stored = _readJson(STORAGE_KEY) || {};
  const isExpired = stored.expires_at && stored.expires_at < now;
  const base = isExpired ? {} : (stored.data || {});

  // Merge: URL params win when present; otherwise keep stored.
  const merged = { ...base };
  [...CLICK_ID_PARAMS, ...UTM_PARAMS].forEach((p) => {
    if (urlAttr[p]) merged[p] = urlAttr[p];
  });

  // Stamp landing context only on the FIRST capture (don't overwrite).
  if (!merged.landing_path) merged.landing_path = window.location.pathname;
  if (!merged.referrer && typeof document !== 'undefined') {
    merged.referrer = document.referrer || '';
  }
  merged.source_platform = _classifySourcePlatform(merged, merged.referrer);

  _writeJson(STORAGE_KEY, {
    data: merged,
    expires_at: now + TTL_MS,
    last_captured_at: now,
  });

  return merged;
}

/**
 * Returns the current stored attribution (or null if absent/expired).
 * Pure read — never writes.
 */
export function getStoredAttribution() {
  const stored = _readJson(STORAGE_KEY);
  if (!stored || !stored.data) return null;
  if (stored.expires_at && stored.expires_at < Date.now()) return null;
  return stored.data;
}

/**
 * Send attribution to the backend (best-effort; never throws).
 * Idempotent: re-POSTs at most once per POST_TTL_MS so we don't
 * spam the server on every navigation.
 */
export async function syncAttributionToBackend(apiClient) {
  try {
    const stored = _readJson(STORAGE_KEY);
    if (!stored || !stored.data) return;

    const lastPosted = stored.last_posted_at || 0;
    if (Date.now() - lastPosted < POST_TTL_MS) return;

    const body = {
      anonymous_id: getAnonymousId(),
      ...stored.data,
    };
    await apiClient.post('/api/attribution/capture', body);

    _writeJson(STORAGE_KEY, {
      ...stored,
      last_posted_at: Date.now(),
    });
  } catch (_) {
    // Network errors must never break the app. The next page load
    // will re-attempt.
  }
}
