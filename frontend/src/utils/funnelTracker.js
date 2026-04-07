/**
 * Funnel Tracker — fires conversion funnel events with rich context.
 * Every event includes: user_id, session_id, source_page, generation_count, device, plan_shown.
 */
import api from './api';

const SESSION_KEY = 'funnel_session_id';

function getSessionId() {
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
 * Fire a funnel event.
 * @param {string} step - One of the FUNNEL_STEPS
 * @param {object} extra - Additional context (source_page, plan_shown, plan_selected, meta)
 */
export function trackFunnel(step, extra = {}) {
  const payload = {
    step,
    session_id: getSessionId(),
    user_id: getUserId(),
    context: {
      source_page: extra.source_page || inferSourcePage(),
      generation_count: extra.generation_count ?? getGenerationCount(),
      device: getDevice(),
      plan_shown: extra.plan_shown || null,
      plan_selected: extra.plan_selected || null,
      meta: extra.meta || {},
    },
  };

  // Fire-and-forget, never block UI
  api.post('/api/funnel/track', payload).catch(() => {});
}

function inferSourcePage() {
  const path = window.location.pathname;
  if (path === '/' || path === '/landing') return 'landing';
  if (path.includes('/app/story-video-studio')) return 'studio';
  if (path.includes('/app/pricing') || path.includes('/app/billing')) return 'pricing';
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
