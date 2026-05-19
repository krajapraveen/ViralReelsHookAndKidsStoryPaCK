/**
 * Google Ads conversion firing helper — P0 2026-05-22 Phase A.
 *
 * Single chokepoint for firing Google Ads conversions. Every fire:
 *   • Reads the Conversion ID + label from process.env (graceful
 *     no-op when env vars are unset — the wiring ships without
 *     leaking your AW-IDs into source control).
 *   • Dedupes per (label, transaction_id) via localStorage so a
 *     refresh, multi-tab session, or redirect replay cannot
 *     double-fire.
 *   • Carries `send_to`, `transaction_id`, `value`, `currency` —
 *     the canonical Google Ads enhanced-conversion fields.
 *
 * Restraint: this is the entire Google Ads tag-firing surface. No
 * GTM migration, no analytics dashboards, no experimentation
 * framework. Minimal, surgical instrumentation.
 *
 * Setup (post-deploy): set these 4 env vars in frontend/.env, then
 * rebuild. Until they are set, the helpers no-op safely.
 *
 *   REACT_APP_GOOGLE_ADS_CONVERSION_ID=AW-XXXXXXXXX
 *   REACT_APP_GOOGLE_ADS_LABEL_SIGNUP=AW-XXXXXXXXX/aaa_bbb
 *   REACT_APP_GOOGLE_ADS_LABEL_FIRST_PROJECT=AW-XXXXXXXXX/ccc_ddd
 *   REACT_APP_GOOGLE_ADS_LABEL_PURCHASE=AW-XXXXXXXXX/eee_fff
 */

const DEDUPE_PREFIX = 'gads_conv:';
const DEDUPE_TTL_MS = 90 * 24 * 60 * 60 * 1000; // 90 days

function _env(name) {
  if (typeof process !== 'undefined' && process.env && process.env[name]) {
    return process.env[name];
  }
  return '';
}

export const GOOGLE_ADS_CONVERSION_ID = _env('REACT_APP_GOOGLE_ADS_CONVERSION_ID');
export const GOOGLE_ADS_LABELS = {
  signup: _env('REACT_APP_GOOGLE_ADS_LABEL_SIGNUP'),
  first_project: _env('REACT_APP_GOOGLE_ADS_LABEL_FIRST_PROJECT'),
  purchase: _env('REACT_APP_GOOGLE_ADS_LABEL_PURCHASE'),
};

export function isGoogleAdsConfigured() {
  return Boolean(GOOGLE_ADS_CONVERSION_ID);
}

/**
 * Boot-time installation of the Google Ads tag.
 *
 * Called once from App.js on mount. Idempotent: a second call after
 * a hot-reload is a safe no-op. When the env var is unset, we never
 * call gtag at all — keeping the wiring inert until you paste in
 * the AW-ID.
 */
let _googleAdsConfigured = false;
export function configureGoogleAdsTag() {
  if (_googleAdsConfigured) return false;
  if (!GOOGLE_ADS_CONVERSION_ID) return false;
  if (typeof window === 'undefined' || typeof window.gtag !== 'function') return false;
  try {
    window.gtag('config', GOOGLE_ADS_CONVERSION_ID);
    _googleAdsConfigured = true;
    return true;
  } catch (_) {
    return false;
  }
}

function _safeStorage() {
  try {
    if (typeof window === 'undefined') return null;
    return window.localStorage;
  } catch (_) {
    return null;
  }
}

function _dedupeKey(label, transactionId) {
  return `${DEDUPE_PREFIX}${label}:${transactionId}`;
}

function _alreadyFired(label, transactionId) {
  const ls = _safeStorage();
  if (!ls) return false;
  try {
    const raw = ls.getItem(_dedupeKey(label, transactionId));
    if (!raw) return false;
    const parsed = JSON.parse(raw);
    if (parsed && parsed.expires_at && parsed.expires_at < Date.now()) {
      return false;
    }
    return Boolean(parsed && parsed.fired_at);
  } catch (_) {
    return false;
  }
}

function _markFired(label, transactionId, meta = {}) {
  const ls = _safeStorage();
  if (!ls) return;
  try {
    ls.setItem(_dedupeKey(label, transactionId), JSON.stringify({
      fired_at: Date.now(),
      expires_at: Date.now() + DEDUPE_TTL_MS,
      ...meta,
    }));
  } catch (_) { /* quota */ }
}

/**
 * Fire a Google Ads conversion event.
 *
 * @param {string} label     One of GOOGLE_ADS_LABELS values (full
 *                            "AW-XXX/LABEL" form).
 * @param {string} transactionId Used for Google Ads de-duplication
 *                            (user_id for signup, project_id for
 *                            first project, order_id for purchase).
 * @param {number} value     Conversion value in `currency`. Use 0 for
 *                            signup / first-project.
 * @param {string} currency  ISO currency code; defaults to INR.
 *
 * @returns {boolean} true if gtag was actually invoked; false on any
 *                    no-op path (env unset, gtag missing, deduped).
 */
export function fireConversion(label, transactionId, value = 0, currency = 'INR') {
  if (!label) return false;
  if (!transactionId) return false;
  if (typeof window === 'undefined' || typeof window.gtag !== 'function') return false;
  if (_alreadyFired(label, transactionId)) return false;

  try {
    window.gtag('event', 'conversion', {
      send_to: label,
      transaction_id: String(transactionId),
      value: Number(value) || 0,
      currency,
    });
  } catch (_) {
    return false;
  }

  _markFired(label, transactionId, { value, currency });
  return true;
}

export function fireSignupConversion(userId) {
  return fireConversion(GOOGLE_ADS_LABELS.signup, userId, 0, 'INR');
}

export function fireFirstProjectConversion(userId) {
  // user_id is the natural dedupe key here — first-project is a
  // one-per-lifetime event, and the server-side activation endpoint
  // already guarantees `fire_now: true` triggers only once.
  return fireConversion(GOOGLE_ADS_LABELS.first_project, userId, 0, 'INR');
}

export function firePurchaseConversion(orderId, value, currency = 'INR') {
  return fireConversion(GOOGLE_ADS_LABELS.purchase, orderId, value, currency);
}

/**
 * Diagnostic helper — returns the current configuration state so
 * the audit suite + a hidden /__debug page can verify wiring without
 * actually firing a conversion.
 */
export function getGoogleAdsConfigStatus() {
  return {
    configured: isGoogleAdsConfigured(),
    conversion_id_present: Boolean(GOOGLE_ADS_CONVERSION_ID),
    label_signup_present: Boolean(GOOGLE_ADS_LABELS.signup),
    label_first_project_present: Boolean(GOOGLE_ADS_LABELS.first_project),
    label_purchase_present: Boolean(GOOGLE_ADS_LABELS.purchase),
  };
}
