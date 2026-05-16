/**
 * useStorySession — React binding for the canonical session reducer
 * ===================================================================
 * Single-page consumer hook. Subscribes to the canonical state and
 * orchestrates server-authoritative writes with automatic stale-write
 * recovery.
 *
 * Why a hook and not a context?
 * -----------------------------
 * Each editor tool owns its own draft. Sharing one global context would
 * re-trigger renders across tools whenever any single draft mutated, and
 * we have no cross-tool sync need yet. A per-page hook keeps the blast
 * radius local — exactly the discipline this sprint is enforcing.
 *
 * Wiring
 * ------
 *   const { state, dispatch, api, status } = useStorySession({ draftId });
 *
 * `state`     — frozen-shape canonical model (see storySession.js)
 * `dispatch`  — raw reducer dispatch for low-level needs
 * `api`       — { commit, transition, refresh, startFresh } — all
 *                version-aware, all auto-resync on STALE_WRITE
 * `status`    — { loading, saving, lastError, lastRequestId }
 *
 * Not wired into any production page yet
 * --------------------------------------
 * Per the founder freeze, no live UI surface has been migrated to this
 * hook. It is foundation infrastructure; the migration is a separate,
 * gated rollout. See SESSION2_ARCHITECTURE.md for the migration plan.
 */
import { useCallback, useEffect, useReducer, useRef } from 'react';
import {
  actions,
  initialStorySessionState,
  storySessionReducer,
} from './storySession';
import client from './storySessionClient';

export function useStorySession({ draftId }) {
  const [state, dispatch] = useReducer(
    storySessionReducer,
    initialStorySessionState
  );
  const loadingRef = useRef(false);
  const mountedRef = useRef(true);

  useEffect(() => () => { mountedRef.current = false; }, []);

  // ── refresh: canonical hydration ──────────────────────────────────────
  const refresh = useCallback(async () => {
    if (!draftId) return { ok: false };
    loadingRef.current = true;
    const r = await client.fetchSessionState(draftId);
    if (!mountedRef.current) return r;
    if (r.ok) dispatch(actions.hydrate(r.state));
    else dispatch(actions.error(r.error));
    loadingRef.current = false;
    return r;
  }, [draftId]);

  useEffect(() => { if (draftId) refresh(); }, [draftId, refresh]);

  // ── commit: version-locked save with auto-resync ──────────────────────
  const commit = useCallback(
    async ({ patch, nextLifecycle } = {}) => {
      if (!draftId) return { ok: false };
      dispatch(actions.savePending());
      const r = await client.patchSession({
        draftId,
        expectedVersion: state.version,
        patch,
        nextLifecycle,
      });
      if (!mountedRef.current) return r;
      if (r.ok) {
        dispatch(actions.saveOk(r.state));
        return r;
      }
      // Stale write — pull canonical and let caller decide to replay.
      if (r.stale) {
        const fresh = await client.fetchSessionState(draftId);
        if (mountedRef.current && fresh.ok) {
          dispatch(actions.resync(fresh.state));
        }
        dispatch(actions.saveFailed(r.error));
        return { ...r, latestState: fresh.ok ? fresh.state : null };
      }
      dispatch(actions.saveFailed(r.error));
      return r;
    },
    [draftId, state.version]
  );

  // ── transition: pure lifecycle move (no field changes) ────────────────
  const transition = useCallback(
    async ({ nextLifecycle, attachedJobId } = {}) => {
      if (!draftId) return { ok: false };
      const r = await client.transitionSession({
        draftId,
        expectedVersion: state.version,
        nextLifecycle,
        attachedJobId,
      });
      if (!mountedRef.current) return r;
      if (r.ok) {
        dispatch(actions.saveOk(r.state));
        return r;
      }
      if (r.stale) {
        const fresh = await client.fetchSessionState(draftId);
        if (mountedRef.current && fresh.ok) {
          dispatch(actions.resync(fresh.state));
        }
      }
      dispatch(actions.saveFailed(r.error));
      return r;
    },
    [draftId, state.version]
  );

  // ── startFresh: archive current + create new + redirect-style reset ───
  // Stays as a thin wrapper. The actual archive/create endpoints are owned
  // by the existing /archive + /create + /session endpoints — we re-use
  // them here so the contract surface stays identical.
  const startFresh = useCallback(async () => {
    const create = await client.createSession();
    if (!mountedRef.current) return create;
    if (create.ok) {
      dispatch(actions.reset());
      dispatch(actions.hydrate(create.state));
    } else {
      dispatch(actions.error(create.error));
    }
    return create;
  }, []);

  return {
    state,
    dispatch,
    api: { commit, transition, refresh, startFresh },
    status: {
      loading: loadingRef.current,
      saving: !!state?.meta?.saving,
      lastError: state?.meta?.lastError || null,
      lastRequestId: state?.meta?.lastRequestId || null,
    },
  };
}

export default useStorySession;
