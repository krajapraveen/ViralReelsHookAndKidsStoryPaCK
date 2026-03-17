/**
 * Lean A/B Testing — Client-side helper
 * Fetches all variant assignments in one call, caches in sessionStorage.
 */

const API = process.env.REACT_APP_BACKEND_URL;

function getSessionId() {
  let sid = sessionStorage.getItem('growth_session_id');
  if (!sid) {
    sid = `gs_${Date.now()}_${Math.random().toString(36).slice(2, 10)}`;
    sessionStorage.setItem('growth_session_id', sid);
  }
  return sid;
}

const CACHE_KEY = 'ab_assignments';

/**
 * Get all experiment assignments for this session.
 * Returns { experiment_id: { variant_id, variant_data } }
 * Fetches once per session, then caches.
 */
export async function getAssignments() {
  const cached = sessionStorage.getItem(CACHE_KEY);
  if (cached) {
    try {
      return JSON.parse(cached);
    } catch {
      sessionStorage.removeItem(CACHE_KEY);
    }
  }

  try {
    const res = await fetch(`${API}/api/ab/assign-all`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: getSessionId() }),
    });
    if (!res.ok) return {};
    const data = await res.json();
    const assignments = data.assignments || {};
    sessionStorage.setItem(CACHE_KEY, JSON.stringify(assignments));
    return assignments;
  } catch {
    return {};
  }
}

/**
 * Get variant data for a specific experiment.
 * Returns { variant_id, variant_data } or null.
 */
export async function getVariant(experimentId) {
  const all = await getAssignments();
  return all[experimentId] || null;
}

/**
 * Track a conversion event for an experiment.
 */
export async function trackConversion(experimentId, event) {
  const sessionId = getSessionId();
  try {
    await fetch(`${API}/api/ab/convert`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionId,
        experiment_id: experimentId,
        event,
      }),
    });
  } catch {
    // Silent — never break UX for analytics
  }
}
