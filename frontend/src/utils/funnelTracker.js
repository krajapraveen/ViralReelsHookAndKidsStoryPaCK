/**
 * Funnel Tracker v2 — fires conversion funnel events with rich segmentation.
 * Every event includes: user_id, session_id, source_page, device_type, traffic_source,
 * story_id, battle_id, has_preview, generation_count.
 *
 * EVENTS TRACKED:
 * - feed_card_impression
 * - preview_started (autoplay began)
 * - preview_completed (2s preview finished)
 * - preview_failed (play() rejected or error)
 * - cta_clicked (type: enter_battle, quick_shot, share, etc.)
 * - entered_battle (user enters competition)
 * - creation_started
 * - creation_abandoned
 * - battle_paywall_viewed
 * - battle_pack_selected
 * - battle_payment_success
 * - battle_payment_abandoned
 * - win_share_triggered
 * - spectator_quick_shot
 * - return_trigger_sent
 * - return_trigger_clicked
 */
import api from './api';

const SESSION_KEY = 'funnel_session_id';
const TRAFFIC_SOURCE_KEY = 'funnel_traffic_source';

export function getSessionId() {
  let sid = sessionStorage.getItem(SESSION_KEY);
  if (!sid) {
    sid = crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random().toString(36).slice(2)}`;
    sessionStorage.setItem(SESSION_KEY, sid);
  }
  return sid;
}

function getDevice() {
  const w = window.innerWidth;
  if (w < 768) return 'mobile';
  if (w < 1024) return 'tablet';
  return 'desktop';
}

function getUserId() {
  try {
    const token = localStorage.getItem('token');
    if (!token) return null;
    const payload = JSON.parse(atob(token.split('.')[1]));
    return payload.sub || payload.user_id || null;
  } catch { return null; }
}

function getGenerationCount() {
  return parseInt(sessionStorage.getItem('generation_count') || '0', 10);
}

export function incrementGenerationCount() {
  const c = getGenerationCount() + 1;
  sessionStorage.setItem('generation_count', String(c));
  return c;
}

/**
 * Detect traffic source from URL params or referrer.
 * Caches in sessionStorage so it persists across page navigations.
 */
function getTrafficSource() {
  let src = sessionStorage.getItem(TRAFFIC_SOURCE_KEY);
  if (src) return src;

  const params = new URLSearchParams(window.location.search);
  const utm = params.get('utm_source') || params.get('ref') || params.get('source');
  if (utm) {
    src = utm.toLowerCase();
  } else {
    const ref = document.referrer || '';
    if (ref.includes('instagram')) src = 'instagram';
    else if (ref.includes('facebook') || ref.includes('fb.')) src = 'facebook';
    else if (ref.includes('twitter') || ref.includes('x.com')) src = 'twitter';
    else if (ref.includes('youtube')) src = 'youtube';
    else if (ref.includes('whatsapp')) src = 'whatsapp';
    else if (ref.includes('google')) src = 'google';
    else if (ref === '') src = 'direct';
    else src = 'unknown';
  }

  sessionStorage.setItem(TRAFFIC_SOURCE_KEY, src);
  return src;
}

// Cache the landing arrival time so every subsequent event carries time_since_landing_ms
const LANDING_TS_KEY = 'landing_ts_ms';
function getLandingTs() {
  let ts = sessionStorage.getItem(LANDING_TS_KEY);
  if (!ts) {
    ts = String(Date.now());
    sessionStorage.setItem(LANDING_TS_KEY, ts);
  }
  return Number(ts);
}

// Cache UTM params on first hit so they're attached to every event in the session
const UTM_KEY = 'utm_cache_v1';
function getUtm() {
  const cached = sessionStorage.getItem(UTM_KEY);
  if (cached) {
    try { return JSON.parse(cached); } catch (_) { /* fallthrough */ }
  }
  const params = new URLSearchParams(window.location.search);
  const utm = {
    utm_source: params.get('utm_source'),
    utm_campaign: params.get('utm_campaign'),
    utm_medium: params.get('utm_medium'),
  };
  sessionStorage.setItem(UTM_KEY, JSON.stringify(utm));
  return utm;
}

// Lightweight browser detection (server also detects from UA — this is a hint)
function getBrowser() {
  const ua = navigator.userAgent.toLowerCase();
  if (ua.includes('edg/')) return 'edge';
  if (ua.includes('chrome/') && ua.includes('safari/')) return 'chrome';
  if (ua.includes('firefox/')) return 'firefox';
  if (ua.includes('safari/') && ua.includes('version/')) return 'safari';
  if (ua.includes('opera') || ua.includes('opr/')) return 'opera';
  return 'other';
}

/**
 * Fire a funnel event with full segmentation.
 * @param {string} step - Event name
 * @param {object} extra - { story_id, battle_id, has_preview, source_page, meta, ... }
 */
export function trackFunnel(step, extra = {}) {
  const utm = getUtm();
  const payload = {
    step,
    session_id: getSessionId(),
    user_id: getUserId(),
    context: {
      source_page: extra.source_page || inferSourcePage(),
      page: extra.page || (typeof window !== 'undefined' ? window.location.pathname : null),
      generation_count: extra.generation_count ?? getGenerationCount(),
      device_type: getDevice(),
      browser: getBrowser(),
      traffic_source: getTrafficSource(),
      utm_source: extra.utm_source || utm.utm_source,
      utm_campaign: extra.utm_campaign || utm.utm_campaign,
      utm_medium: extra.utm_medium || utm.utm_medium,
      time_since_landing_ms: Date.now() - getLandingTs(),
      variant_seen: extra.variant_seen || null,
      story_id: extra.story_id || extra.data?.story_id || extra.meta?.story_id || null,
      battle_id: extra.battle_id || extra.data?.root_id || extra.meta?.battle_id || null,
      has_preview: extra.has_preview ?? null,
      plan_shown: extra.plan_shown || null,
      plan_selected: extra.plan_selected || null,
      meta: extra.meta || extra.data || {},
    },
  };

  // Fire-and-forget, never block UI
  api.post('/api/funnel/track', payload).catch(() => {});
}

function inferSourcePage() {
  const path = window.location.pathname;
  if (path === '/' || path === '/landing') return 'landing';
  if (path.includes('/app/story-video-studio')) return 'studio';
  if (path.includes('/app/story-battle')) return 'battle_page';
  if (path.includes('/app/story-viewer')) return 'viewer';
  if (path.includes('/app/pricing') || path.includes('/app/billing')) return 'pricing';
  if (path.includes('/app/explore')) return 'explore';
  if (path.includes('/app')) return 'dashboard';
  if (path.includes('/v/') || path.includes('/character/')) return 'public_page';
  return 'other';
}

export default {
  trackFunnel,
  incrementGenerationCount,
  getGenerationCount,
  getSessionId,
};
