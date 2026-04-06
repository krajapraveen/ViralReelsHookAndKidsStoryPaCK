/**
 * feedbackSession.js — Session-scoped feedback tracking utilities
 */
const SESSION_KEYS = {
  SESSION_ID: 'vs_session_id',
  HAS_USED_FEATURE: 'vs_has_used_feature',
  USED_FEATURES: 'vs_used_features',
  FEEDBACK_PROMPT_SHOWN: 'vs_feedback_prompt_shown',
  FEEDBACK_SUBMITTED: 'vs_feedback_submitted',
};

export function ensureSessionId() {
  let sessionId = sessionStorage.getItem(SESSION_KEYS.SESSION_ID);
  if (!sessionId) {
    sessionId = `sess_${Date.now()}_${Math.random().toString(36).slice(2)}`;
    sessionStorage.setItem(SESSION_KEYS.SESSION_ID, sessionId);
  }
  return sessionId;
}

export function markFeatureUsed(featureName) {
  sessionStorage.setItem(SESSION_KEYS.HAS_USED_FEATURE, 'true');
  const raw = sessionStorage.getItem(SESSION_KEYS.USED_FEATURES);
  const arr = raw ? JSON.parse(raw) : [];
  if (!arr.includes(featureName)) {
    arr.push(featureName);
    sessionStorage.setItem(SESSION_KEYS.USED_FEATURES, JSON.stringify(arr));
  }
}

export function getUsedFeatures() {
  const raw = sessionStorage.getItem(SESSION_KEYS.USED_FEATURES);
  return raw ? JSON.parse(raw) : [];
}

export function getFeedbackEligibility() {
  const hasUsedFeature = sessionStorage.getItem(SESSION_KEYS.HAS_USED_FEATURE) === 'true';
  const promptShown = sessionStorage.getItem(SESSION_KEYS.FEEDBACK_PROMPT_SHOWN) === 'true';
  const submitted = sessionStorage.getItem(SESSION_KEYS.FEEDBACK_SUBMITTED) === 'true';
  return {
    eligible: hasUsedFeature && !promptShown && !submitted,
    hasUsedFeature,
    promptShown,
    submitted,
  };
}

export function markFeedbackPromptShown() {
  sessionStorage.setItem(SESSION_KEYS.FEEDBACK_PROMPT_SHOWN, 'true');
}

export function markFeedbackSubmitted() {
  sessionStorage.setItem(SESSION_KEYS.FEEDBACK_SUBMITTED, 'true');
}

export function clearFeedbackSession() {
  Object.values(SESSION_KEYS).forEach((k) => sessionStorage.removeItem(k));
}
