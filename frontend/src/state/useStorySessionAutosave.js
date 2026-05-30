/**
 * useStorySessionAutosave — Phase 3b (2026-05-17)
 * ==================================================
 *
 * Replaces the legacy `POST /api/drafts/save` last-write-wins autosave with
 * a version-locked write through the canonical Session-2 contract.
 *
 * Responsibilities
 * ----------------
 *   1. Auto-creates a canonical session the first time the user types
 *      (legacy `/save` was upsert-based; the new contract requires an
 *      explicit draft_id).
 *   2. Debounces writes by 3,000 ms (preserves prior autosave UX).
 *   3. Sends version-locked PATCH via `client.patchSession({ expected_version, … })`
 *      with `next_lifecycle = 'EDITING'`. Every accepted write bumps the
 *      server-authoritative `version` counter monotonically.
 *   4. Recovers from STALE_WRITE non-destructively: refetches canonical
 *      state, syncs the local version reference, surfaces a polite toast,
 *      and lets the next debounce tick replay the patch. NEVER wipes
 *      local text — the user's edits stay on screen.
 *   5. Keeps shadow divergence logging active (Phase 3a contract).
 *
 * READ this before changing
 * -------------------------
 *   • The hook OWNS the `version` counter via an internal ref. The legacy
 *     `useState` in StoryVideoPipeline.js continues to own the live text
 *     fields. This is the intentional split for Phase 3b — read it twice.
 *   • The hook NEVER touches `commit`'s second argument `nextLifecycle`
 *     with anything other than 'EDITING'. Lifecycle progression beyond
 *     EDITING (READY_TO_GENERATE, GENERATING, …) is Phase 3c work.
 *   • The hook NEVER calls `transition` or `startFresh`. Start Fresh
 *     remains a page-owned legacy flow (`/api/drafts/archive` +
 *     `/api/drafts/create`).
 */
import { useCallback, useEffect, useRef } from 'react';
import { toast } from 'sonner';
import client from './storySessionClient';
import { ErrorCode, Lifecycle } from './storySession';

// Founder-spec: preserve the prior 3-second debounce so autosave UX is
// indistinguishable from the legacy implementation.
const AUTOSAVE_DEBOUNCE_MS = 3000;

// Same field whitelist as the shadow observer — must stay in sync.
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
    return v.length > 80 ? JSON.stringify(v.slice(0, 77) + '...') : JSON.stringify(v);
  }
  return JSON.stringify(v);
}

/**
 * @param {object} params
 * @param {string|null} params.draftId   currently active draft id (may be null on a fresh session)
 * @param {object}      params.fields    { title, storyText, animationStyle, ageGroup, voicePreset }
 * @param {boolean}     params.enabled   master switch (default true)
 * @param {function}    params.onDraftCreated  called once when the hook auto-creates a session
 *
 * @returns {{ version:number, lastRequestId:string|null, status:string }}
 */
export function useStorySessionAutosave({
  draftId,
  fields,
  enabled = true,
  onDraftCreated,
}) {
  // Server-authoritative version counter. Hook-owned.
  const versionRef = useRef(0);
  const canonicalLifecycleRef = useRef(null);
  const lastRequestIdRef = useRef(null);
  const lastSavedRef = useRef({ title: null, storyText: null });
  const debounceTimerRef = useRef(null);
  const sessionCreatingRef = useRef(false);
  const draftIdRef = useRef(draftId);
  const fieldsRef = useRef(fields);
  const mountedRef = useRef(true);

  // Per-canonical-version divergence dedupe (Phase 3a contract preserved).
  const loggedDivergenceRef = useRef({ version: -1, fields: new Set() });

  useEffect(() => { mountedRef.current = true; return () => { mountedRef.current = false; }; }, []);
  useEffect(() => { draftIdRef.current = draftId; }, [draftId]);
  useEffect(() => { fieldsRef.current = fields; }, [fields]);

  // ── Hydrate canonical version on draftId change ────────────────────────
  useEffect(() => {
    if (!enabled) return;
    if (!draftId) {
      versionRef.current = 0;
      canonicalLifecycleRef.current = null;
      loggedDivergenceRef.current = { version: -1, fields: new Set() };
      return;
    }
    let cancelled = false;
    (async () => {
      const r = await client.fetchSessionState(draftId);
      if (cancelled || !mountedRef.current) return;
      if (r.ok && r.state) {
        versionRef.current = r.state.version;
        canonicalLifecycleRef.current = r.state.lifecycle;
        lastRequestIdRef.current = r.state.requestId || r.requestId;
        _logDivergence(r.state, fieldsRef.current, loggedDivergenceRef);
      }
    })();
    return () => { cancelled = true; };
  }, [draftId, enabled]);

  // ── The single autosave commit, called from the debounced effect ──────
  const _commit = useCallback(async () => {
    if (!enabled) return;
    const f = fieldsRef.current || {};
    // Skip empty drafts — same guard as legacy autosave.
    if (!f.title?.trim() && !f.storyText?.trim()) return;
    // Skip if nothing changed since last save.
    if (f.title === lastSavedRef.current.title &&
        f.storyText === lastSavedRef.current.storyText) {
      return;
    }

    // ── Phase A: auto-create a session if we don't have a draftId yet ──
    let did = draftIdRef.current;
    if (!did) {
      if (sessionCreatingRef.current) return; // dedupe concurrent creates
      sessionCreatingRef.current = true;
      const created = await client.createSession();
      sessionCreatingRef.current = false;
      if (!mountedRef.current) return;
      if (!created.ok) {
        // P0 2026-05-30 — DRAFT_ALREADY_ACTIVE is a recoverable state.
        // The user already has a server-side active draft (lingering
        // from an earlier session, refresh, or Start-Fresh that
        // didn't fully archive). Adopt that draft instead of stranding
        // the user behind a generic toast. Pinned by audit
        // test_draft_already_active_recovery_2026_05.py.
        if (created.alreadyActive && created.activeDraftId) {
          const adopted = created.activeDraftId;
          const hydrated = await client.fetchSessionState(adopted);
          if (!mountedRef.current) return;
          if (hydrated.ok && hydrated.state) {
            did = adopted;
            versionRef.current = hydrated.state.version;
            canonicalLifecycleRef.current = hydrated.state.lifecycle;
            lastRequestIdRef.current = hydrated.state.requestId;
            if (typeof onDraftCreated === 'function') {
              onDraftCreated(did);
            }
            // Fall through into Phase B with the adopted draft.
          } else {
            // Adoption failed (e.g. 404 — draft was archived between
            // calls). Treat as a real failure and surface with ref.
            toast.error(
              `Couldn't resume your existing draft. Ref: ${hydrated.requestId || created.requestId || 'unknown'}`,
              { duration: 5000 }
            );
            return;
          }
        } else {
          // True failure — surface with request_id so support has a ref
          // but DO NOT wipe local text.
          toast.error(
            `Couldn't start a new draft. Ref: ${created.requestId || 'unknown'}`,
            { duration: 5000 }
          );
          return;
        }
      } else {
        did = created.state.draftId;
        versionRef.current = created.state.version;
        canonicalLifecycleRef.current = created.state.lifecycle;
        lastRequestIdRef.current = created.state.requestId;
        if (typeof onDraftCreated === 'function') {
          onDraftCreated(did);
        }
      }
    }

    // ── Phase B: version-locked patch ──
    const patch = {
      title: f.title,
      storyText: f.storyText,
      animationStyle: f.animationStyle,
      ageGroup: f.ageGroup,
      voicePreset: f.voicePreset,
    };
    // Lifecycle is always EDITING for autosave (idempotent at EDITING level).
    // Lifecycle progression beyond EDITING is Phase 3c.
    const desiredLifecycle = Lifecycle.EDITING;

    const r = await client.patchSession({
      draftId: did,
      expectedVersion: versionRef.current,
      patch,
      nextLifecycle: desiredLifecycle,
    });
    if (!mountedRef.current) return;

    if (r.ok) {
      versionRef.current = r.state.version;
      canonicalLifecycleRef.current = r.state.lifecycle;
      lastRequestIdRef.current = r.state.requestId;
      lastSavedRef.current = { title: f.title, storyText: f.storyText };
      _logDivergence(r.state, fieldsRef.current, loggedDivergenceRef);
      return;
    }

    // ── Phase C: stale-write non-destructive recovery ──
    if (r.error?.code === ErrorCode.STALE_WRITE) {
      // Refetch canonical to learn the latest server version.
      const fresh = await client.fetchSessionState(did);
      if (mountedRef.current && fresh.ok) {
        versionRef.current = fresh.state.version;
        canonicalLifecycleRef.current = fresh.state.lifecycle;
        lastRequestIdRef.current = fresh.state.requestId || r.requestId;
        // Non-destructive: keep local text. Next debounce tick will retry
        // with the corrected expected_version.
        toast.message(
          'Loaded the latest version from another tab — your unsaved text is preserved and will save shortly.',
          { duration: 4500 }
        );
        // Reset lastSavedRef so the next tick re-attempts the save.
        lastSavedRef.current = { title: null, storyText: null };
        _logDivergence(fresh.state, fieldsRef.current, loggedDivergenceRef);
      }
      return;
    }

    // Any other error path — silent but observable. We do NOT toast every
    // network blip because autosave runs every 3s; instead, we log with
    // request_id so ops can correlate.
    lastRequestIdRef.current = r.error?.requestId || r.requestId || null;
    // eslint-disable-next-line no-console
    console.warn(
      `[story-session/autosave-failed] request_id=${lastRequestIdRef.current || 'n/a'} ` +
        `draft_id=${did} code=${r.error?.code || 'UNKNOWN'} message=${_repr(r.error?.message)}`
    );
  }, [enabled, onDraftCreated]);

  // ── Debounced effect — preserves the legacy 3-second cadence ──────────
  useEffect(() => {
    if (!enabled) return undefined;
    const f = fields || {};
    if (!f.title?.trim() && !f.storyText?.trim()) return undefined;
    // Skip if nothing changed since last save.
    if (f.title === lastSavedRef.current.title &&
        f.storyText === lastSavedRef.current.storyText) {
      return undefined;
    }
    if (debounceTimerRef.current) clearTimeout(debounceTimerRef.current);
    debounceTimerRef.current = setTimeout(() => { _commit(); }, AUTOSAVE_DEBOUNCE_MS);
    return () => {
      if (debounceTimerRef.current) clearTimeout(debounceTimerRef.current);
    };
  }, [
    enabled,
    fields?.title,
    fields?.storyText,
    fields?.animationStyle,
    fields?.ageGroup,
    fields?.voicePreset,
    _commit,
  ]);

  return {
    version: versionRef.current,
    lastRequestId: lastRequestIdRef.current,
    status: sessionCreatingRef.current ? 'creating' : 'idle',
  };
}

// ─── Internal: divergence logger (mirrors useStorySessionShadow) ────────
function _logDivergence(canonicalState, legacy, loggedRef) {
  if (!canonicalState || !canonicalState.draftId) return;
  if (loggedRef.current.version !== canonicalState.version) {
    loggedRef.current = { version: canonicalState.version, fields: new Set() };
  }
  for (const f of TRACKED_FIELDS) {
    const canonical = canonicalState[f];
    const legacyVal = legacy ? legacy[f] : undefined;
    const norm = (x) => (x === null || x === undefined || x === '' ? null : x);
    if (norm(canonical) === norm(legacyVal)) continue;
    if (loggedRef.current.fields.has(f)) continue;
    loggedRef.current.fields.add(f);
    // eslint-disable-next-line no-console
    console.info(
      `[story-session/divergence] request_id=${canonicalState.requestId || 'n/a'} ` +
        `draft_id=${canonicalState.draftId} field=${f} legacy_value=${_repr(legacyVal)} ` +
        `canonical_value=${_repr(canonical)}`
    );
  }
}

export default useStorySessionAutosave;
