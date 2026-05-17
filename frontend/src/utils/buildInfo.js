/**
 * Build Info — P1 2026-05-19 reliability sweep.
 *
 * Single source of truth for the running frontend bundle identity.
 * Surfaced in:
 *   • Diagnostic console logs on every error toast.
 *   • The `X-Frontend-Build` request header on every API call.
 *   • The visible build marker in tools like Photo-to-Comic.
 *
 * `BUILD_HASH` resolves at build time from CRA env vars when set,
 * otherwise falls back to a static fingerprint that ops can grep for.
 */
const env = (typeof process !== 'undefined' && process.env) ? process.env : {};

export const BUILD_HASH =
  env.REACT_APP_BUILD_HASH ||
  env.REACT_APP_GIT_SHA ||
  '2026-05-22-reaction-gif-connection-loss-fix';

export const BUILD_TIMESTAMP =
  env.REACT_APP_BUILD_TIMESTAMP || '2026-05-22T00:00:00Z';

export const BUILD_INFO = Object.freeze({
  hash: BUILD_HASH,
  timestamp: BUILD_TIMESTAMP,
});

export default BUILD_INFO;
