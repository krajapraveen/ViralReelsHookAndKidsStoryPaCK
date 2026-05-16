/**
 * In-flight generation guard — P0 2026-05-16 (reward-loop reliability).
 *
 * Purpose
 * -------
 * Some flows (Reel Engine, Story-to-Video, Photo Trailer) make a synchronous
 * generation request that can take 30–60 seconds. If the user's token quietly
 * expires DURING that window, the next 401 in our axios interceptor would
 * yank them to /login the instant their reward result was about to render —
 * destroying the activation moment.
 *
 * This module is a tiny, dependency-free state holder that the page imports
 * to mark a generation as in-flight, and the api.js interceptor consults to
 * decide whether to hard-redirect on 401 or defer the redirect (toast +
 * pending-login flag) until the result has been displayed or the generation
 * has definitively failed.
 *
 * NEVER imports anything else (must be cheap + circular-safe with api.js).
 */

let activeCount = 0;
let pendingLoginReason = null;

/**
 * Mark a generation as in-flight. Returns an `end()` finalizer the caller
 * should ALWAYS invoke (success or failure) in a `finally`.
 *
 * Stays count-based so concurrent generations (e.g. variation + reel)
 * cannot race the counter to zero.
 */
export function beginGeneration() {
  activeCount += 1;
  let ended = false;
  return function end() {
    if (ended) return;
    ended = true;
    activeCount = Math.max(0, activeCount - 1);
  };
}

/** Truthy while at least one generation is still in-flight. */
export function isGenerationInFlight() {
  return activeCount > 0;
}

/**
 * Defer a 401 forced-logout. api.js calls this when an in-flight generation
 * is active; the redirect will be honored AFTER the active generation
 * completes (whoever calls `flushPendingLogin()` will trigger it).
 */
export function deferLogin(returnPath) {
  pendingLoginReason = returnPath || (typeof window !== 'undefined'
    ? window.location.pathname + window.location.search : '/');
}

/** True when a 401 was deferred and is waiting to fire. */
export function hasPendingLogin() {
  return pendingLoginReason !== null;
}

/**
 * Consume the pending login (if any) and return the path that should be
 * navigated to. Caller is responsible for the actual location change so
 * we can keep this module synchronous + side-effect-free except for state.
 */
export function consumePendingLogin() {
  if (pendingLoginReason === null) return null;
  const returnPath = pendingLoginReason;
  pendingLoginReason = null;
  return returnPath && returnPath !== '/' && returnPath !== '/login'
    ? `/login?return=${encodeURIComponent(returnPath)}`
    : '/login';
}

/** Test-only: hard reset between unit tests. */
export function __reset_for_tests() {
  activeCount = 0;
  pendingLoginReason = null;
}
