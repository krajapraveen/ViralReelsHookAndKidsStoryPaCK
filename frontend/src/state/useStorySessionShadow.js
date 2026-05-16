/**
 * useStorySessionShadow — read-only shadow observer (2026-05-17, Phase 3a)
 * ==========================================================================
 * Mounts `useStorySession` alongside an existing legacy editor and compares
 * the two state shapes field-by-field. Emits a single structured console
 * log line per divergence, suitable for production-grade observability.
 *
 * READ-ONLY guarantee
 * -------------------
 * This module imports `useStorySession` but NEVER calls its mutator API
 * (`commit`, `transition`, `startFresh`). The only operation the hook
 * performs is the canonical hydration call (`GET /api/drafts/{id}/state`)
 * fired automatically inside `useStorySession` on mount + draftId change.
 * No PATCH, no POST /transition, no POST /session, ever.
 *
 * Why a separate wrapper instead of using the hook directly?
 * ---------------------------------------------------------
 * Two reasons:
 *   1. We want the divergence-detection logic tested in isolation from
 *      the (3,467-line) StoryVideoPipeline.js page.
 *   2. We want a STATIC guarantee — readable by a regex test — that no
 *      mutator from the hook is called inside the live editor file.
 *      Centralizing the mount here makes that test reliable.
 *
 * Output shape
 * ------------
 * For each divergent field detected on a re-render, exactly ONE line of:
 *
 *   [story-session/divergence] request_id=<rid> draft_id=<did> field=<name>
 *     legacy_value=<repr> canonical_value=<repr>
 *
 * The line is emitted via console.info so it never blocks the user. In
 * production it pipes through the existing browser-console-to-server log
 * channel; here it's local-only by design.
 *
 * Fields tracked
 * --------------
 *   title, storyText, animationStyle, ageGroup, voicePreset, lifecycle
 *
 * Not tracked (intentional):
 *   version          — server-authoritative; can't diverge by design
 *   draftId          — used as the comparison anchor
 *   attachedJobId    — only set by the pipeline, not by the editor
 *   createdAt/updatedAt — timestamps, not user-facing state
 */
import { useEffect, useRef } from 'react';
import { useStorySession } from './useStorySession';

// Whitelist of fields whose divergence we surface. The order is the order
// log lines appear in console — alphabetical for grep friendliness.
const TRACKED_FIELDS = Object.freeze([
  'ageGroup',
  'animationStyle',
  'lifecycle',
  'storyText',
  'title',
  'voicePreset',
]);

function _repr(v) {
  if (v === null || v === undefined) return String(v);
  if (typeof v === 'string') {
    // Truncate so giant story text doesn't blow up log lines
    return v.length > 80 ? JSON.stringify(v.slice(0, 77) + '...') : JSON.stringify(v);
  }
  return JSON.stringify(v);
}

/**
 * @param {{ draftId: string|null, legacy: object, enabled?: boolean }} params
 *   draftId — canonical id of the draft (drives the canonical fetch)
 *   legacy  — current legacy state values:
 *     {
 *       title, storyText, animationStyle, ageGroup, voicePreset, lifecycle?
 *     }
 *   enabled — feature flag; defaults true. When false, no fetch + no logs.
 *
 * @returns {{ canonical: object|null, lastRequestId: string|null }}
 *   Returned for tests + ops UI — NEVER pass `canonical` into React state.
 */
export function useStorySessionShadow({ draftId, legacy, enabled = true }) {
  // useStorySession is the canonical hook. We use it for HYDRATION ONLY.
  // We deliberately do NOT destructure `api` to keep linters/reviewers
  // confident that no mutator (commit/transition/startFresh) is reachable
  // from this module.
  const { state, status } = useStorySession({ draftId: enabled ? draftId : null });

  // Track which fields we've already logged on the current canonical
  // version, so a steady-state divergence doesn't spam the console.
  const loggedRef = useRef({ version: -1, fields: new Set() });

  useEffect(() => {
    if (!enabled) return;
    if (!state || !state.draftId) return;
    // Reset the per-version dedupe ring when canonical advances.
    if (loggedRef.current.version !== state.version) {
      loggedRef.current = { version: state.version, fields: new Set() };
    }

    for (const f of TRACKED_FIELDS) {
      const canonical = state[f];
      const legacyVal = legacy ? legacy[f] : undefined;
      // Treat null/undefined/empty-string symmetrically — the editor and the
      // server use slightly different conventions ("" vs null) and we don't
      // want to flag that as a meaningful divergence.
      const norm = (x) => (x === null || x === undefined || x === '' ? null : x);
      if (norm(canonical) === norm(legacyVal)) continue;

      if (loggedRef.current.fields.has(f)) continue;
      loggedRef.current.fields.add(f);

      // eslint-disable-next-line no-console
      console.info(
        `[story-session/divergence] request_id=${state.meta?.lastRequestId || 'n/a'} ` +
          `draft_id=${state.draftId} field=${f} legacy_value=${_repr(legacyVal)} ` +
          `canonical_value=${_repr(canonical)}`
      );
    }
    // We intentionally omit `legacy` from the dep list — it's an object that
    // changes identity every render. Comparing inside the loop on the next
    // render is the design.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    enabled,
    state?.version,
    state?.title,
    state?.storyText,
    state?.animationStyle,
    state?.ageGroup,
    state?.voicePreset,
    state?.lifecycle,
    legacy?.title,
    legacy?.storyText,
    legacy?.animationStyle,
    legacy?.ageGroup,
    legacy?.voicePreset,
    legacy?.lifecycle,
  ]);

  return {
    canonical: enabled ? state : null,
    lastRequestId: status?.lastRequestId || null,
  };
}

export default useStorySessionShadow;
