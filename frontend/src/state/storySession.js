/**
 * Story Session State — Frontend canonical model (2026-05-17, Session 2)
 * ======================================================================
 *
 * This module mirrors the backend `StorySessionState` exactly. It is the
 * SINGLE place that knows the lifecycle graph for the frontend.
 *
 * Design pillars (founder-mandated):
 *   1. ONE canonical state object — no localStorage / split useState games
 *   2. Explicit lifecycle transitions enforced in the reducer
 *   3. Illegal transitions are dev-time errors (assertion) AND no-ops in prod
 *   4. Version is a number — server is authoritative
 *   5. Stale write rejection — when the server returns STALE_WRITE the
 *      reducer takes the server's current_version + payload and re-syncs
 *   6. Deterministic hydration — `hydrateFromServer(state)` is idempotent;
 *      replacing state never causes flicker because every selector is pure
 *   7. Single source of truth — components subscribe via `useStorySession`
 *   8. Immutable updates — every reducer action returns a NEW state object
 *   9. Strict ownership — `(draftId, userId)` baked into the state shape
 *  10. Regression coverage first-class — see __tests__/storySession.test.js
 *
 * Scope discipline
 * ----------------
 * No routes, no fetch, no React imports. Pure data. The fetch layer lives
 * in `storySessionClient.js`; the React binding lives in
 * `useStorySession.js`. This split keeps the reducer cheap to test and
 * reason about.
 */

// ─── Lifecycle constants ─────────────────────────────────────────────────
export const Lifecycle = Object.freeze({
  IDLE: 'IDLE',
  EDITING: 'EDITING',
  AUTOSAVING: 'AUTOSAVING',
  READY_TO_GENERATE: 'READY_TO_GENERATE',
  GENERATING: 'GENERATING',
  READY: 'READY',
  FAILED: 'FAILED',
  ARCHIVED: 'ARCHIVED',
});

// Mirror of backend/models/story_session.py `_LEGAL_TRANSITIONS`.
// Any change here MUST be matched on the backend, and vice-versa.
const LEGAL_TRANSITIONS = Object.freeze({
  IDLE:               new Set(['EDITING', 'ARCHIVED']),
  EDITING:            new Set(['AUTOSAVING', 'READY_TO_GENERATE', 'ARCHIVED']),
  AUTOSAVING:         new Set(['EDITING', 'READY_TO_GENERATE', 'ARCHIVED']),
  READY_TO_GENERATE:  new Set(['EDITING', 'GENERATING', 'ARCHIVED']),
  GENERATING:         new Set(['READY', 'FAILED']),
  READY:              new Set(['ARCHIVED']),
  FAILED:             new Set(['EDITING', 'ARCHIVED']),
  ARCHIVED:           new Set(),
});

export function isLegalTransition(prev, next) {
  if (prev === next) return true;        // idempotent retries
  const allowed = LEGAL_TRANSITIONS[prev];
  return allowed ? allowed.has(next) : false;
}

export function legalNextStates(prev) {
  const allowed = LEGAL_TRANSITIONS[prev];
  return allowed ? Array.from(allowed).sort() : [];
}

// ─── Error codes (match backend StorySessionErrorCode) ──────────────────
export const ErrorCode = Object.freeze({
  DRAFT_NOT_FOUND: 'DRAFT_NOT_FOUND',
  NOT_OWNED: 'NOT_OWNED',
  STALE_WRITE: 'STALE_WRITE',
  ILLEGAL_TRANSITION: 'ILLEGAL_TRANSITION',
  SCHEMA_UNSUPPORTED: 'DRAFT_SCHEMA_UNSUPPORTED',
  INVALID_PATCH: 'INVALID_PATCH',
  // P0 2026-05-30 — DRAFT_ALREADY_ACTIVE is a RECOVERABLE state, not a
  // failure. Backend returns 409 + `active_draft_id` so the client can
  // adopt the existing draft. Surfacing this as a generic error toast
  // (the "Couldn't start a new draft. Ref: ..." bug) strands the user.
  // Canonical recovery path: useStorySessionAutosave adopts the
  // existing draft on this code. Pinned by audit
  // test_draft_already_active_recovery_2026_05.py.
  DRAFT_ALREADY_ACTIVE: 'DRAFT_ALREADY_ACTIVE',
});

// ─── Canonical state shape ───────────────────────────────────────────────
export const initialStorySessionState = Object.freeze({
  // identity (immutable across draft lifetime)
  draftId: null,
  userId: null,
  schemaVersion: 1,

  // version + lifecycle
  version: 0,
  lifecycle: Lifecycle.IDLE,

  // domain fields
  title: '',
  storyText: '',
  animationStyle: null,
  ageGroup: null,
  voicePreset: null,

  // attached pipeline job
  attachedJobId: null,

  // timestamps
  createdAt: null,
  updatedAt: null,
  archivedAt: null,

  // client-side metadata (NOT sent to server)
  meta: Object.freeze({
    // last server-correlated request id — surfaces in error UX
    lastRequestId: null,
    // last error (only one in-flight at a time) — { code, message, retryable }
    lastError: null,
    // whether a save is currently in flight
    saving: false,
  }),
});

// ─── Action types ────────────────────────────────────────────────────────
export const Actions = Object.freeze({
  // Server-driven hydration. Single source of truth for incoming state.
  HYDRATE: 'storySession/HYDRATE',

  // Local edit — used by uncontrolled inputs before autosave runs.
  // Does NOT bump version (version is server-authoritative).
  LOCAL_EDIT: 'storySession/LOCAL_EDIT',

  // Save lifecycle markers.
  SAVE_PENDING: 'storySession/SAVE_PENDING',
  SAVE_OK: 'storySession/SAVE_OK',
  SAVE_FAILED: 'storySession/SAVE_FAILED',

  // Stale-write recovery — server returned the canonical state, take it.
  RESYNC: 'storySession/RESYNC',

  // Hard reset (Start Fresh).
  RESET: 'storySession/RESET',

  // Error envelope passthrough (no state change, just metadata).
  ERROR: 'storySession/ERROR',
});

// ─── Pure reducer ────────────────────────────────────────────────────────
// Always returns a NEW object. Never mutates. Frozen-input safe.
export function storySessionReducer(state, action) {
  const s = state || initialStorySessionState;
  switch (action.type) {
    case Actions.HYDRATE:
    case Actions.RESYNC: {
      // Server is the authority. Replace identity + version + lifecycle +
      // domain fields. Preserve client-side `meta` unless `meta` was
      // explicitly provided.
      const payload = action.payload || {};
      return {
        ...s,
        draftId: payload.draftId ?? s.draftId,
        userId: payload.userId ?? s.userId,
        schemaVersion: payload.schemaVersion ?? s.schemaVersion,
        version: payload.version ?? s.version,
        lifecycle: payload.lifecycle ?? s.lifecycle,
        title: payload.title ?? '',
        storyText: payload.storyText ?? '',
        animationStyle: payload.animationStyle ?? null,
        ageGroup: payload.ageGroup ?? null,
        voicePreset: payload.voicePreset ?? null,
        attachedJobId: payload.attachedJobId ?? null,
        createdAt: payload.createdAt ?? s.createdAt,
        updatedAt: payload.updatedAt ?? s.updatedAt,
        archivedAt: payload.archivedAt ?? null,
        meta: {
          ...s.meta,
          saving: false,
          lastError: null,
          lastRequestId: payload.requestId ?? s.meta.lastRequestId,
        },
      };
    }

    case Actions.LOCAL_EDIT: {
      // Lifecycle guard: editing is only legal from IDLE/EDITING/AUTOSAVING/
      // READY_TO_GENERATE/FAILED. GENERATING/READY/ARCHIVED reject edits.
      if (
        s.lifecycle === Lifecycle.GENERATING ||
        s.lifecycle === Lifecycle.READY ||
        s.lifecycle === Lifecycle.ARCHIVED
      ) {
        // dev-time loud, prod-time silent (last-write-wins is not legal here)
        if (process.env.NODE_ENV !== 'production') {
          // eslint-disable-next-line no-console
          console.warn(
            `[storySession] LOCAL_EDIT rejected in ${s.lifecycle} state`
          );
        }
        return s;
      }
      const patch = action.payload || {};
      const nextLifecycle =
        s.lifecycle === Lifecycle.IDLE ? Lifecycle.EDITING : s.lifecycle;
      return {
        ...s,
        title: patch.title ?? s.title,
        storyText: patch.storyText ?? s.storyText,
        animationStyle: patch.animationStyle ?? s.animationStyle,
        ageGroup: patch.ageGroup ?? s.ageGroup,
        voicePreset: patch.voicePreset ?? s.voicePreset,
        lifecycle: nextLifecycle,
      };
    }

    case Actions.SAVE_PENDING:
      return { ...s, meta: { ...s.meta, saving: true, lastError: null } };

    case Actions.SAVE_OK: {
      // Server returned canonical state — same as HYDRATE but flagged.
      const payload = action.payload || {};
      return {
        ...s,
        version: payload.version ?? s.version,
        lifecycle: payload.lifecycle ?? s.lifecycle,
        updatedAt: payload.updatedAt ?? s.updatedAt,
        attachedJobId: payload.attachedJobId ?? s.attachedJobId,
        archivedAt: payload.archivedAt ?? s.archivedAt,
        meta: {
          ...s.meta,
          saving: false,
          lastError: null,
          lastRequestId: payload.requestId ?? s.meta.lastRequestId,
        },
      };
    }

    case Actions.SAVE_FAILED: {
      const err = action.payload || {};
      return {
        ...s,
        meta: {
          ...s.meta,
          saving: false,
          lastError: {
            code: err.code || 'UNKNOWN',
            message: err.message || 'Save failed.',
            retryable: !!err.retryable,
          },
          lastRequestId: err.requestId ?? s.meta.lastRequestId,
        },
      };
    }

    case Actions.RESET:
      return { ...initialStorySessionState };

    case Actions.ERROR: {
      const err = action.payload || {};
      return {
        ...s,
        meta: {
          ...s.meta,
          lastError: {
            code: err.code || 'UNKNOWN',
            message: err.message || '',
            retryable: !!err.retryable,
          },
          lastRequestId: err.requestId ?? s.meta.lastRequestId,
        },
      };
    }

    default:
      return s;
  }
}

// ─── Action creators ─────────────────────────────────────────────────────
export const actions = {
  hydrate: (payload) => ({ type: Actions.HYDRATE, payload }),
  resync: (payload) => ({ type: Actions.RESYNC, payload }),
  localEdit: (patch) => ({ type: Actions.LOCAL_EDIT, payload: patch }),
  savePending: () => ({ type: Actions.SAVE_PENDING }),
  saveOk: (payload) => ({ type: Actions.SAVE_OK, payload }),
  saveFailed: (err) => ({ type: Actions.SAVE_FAILED, payload: err }),
  reset: () => ({ type: Actions.RESET }),
  error: (err) => ({ type: Actions.ERROR, payload: err }),
};

// ─── Selectors (pure) ────────────────────────────────────────────────────
export const selectors = {
  isSaving: (s) => !!s?.meta?.saving,
  isArchived: (s) => s?.lifecycle === Lifecycle.ARCHIVED,
  isGenerating: (s) => s?.lifecycle === Lifecycle.GENERATING,
  canEdit: (s) =>
    s &&
    s.lifecycle !== Lifecycle.GENERATING &&
    s.lifecycle !== Lifecycle.READY &&
    s.lifecycle !== Lifecycle.ARCHIVED,
  canGenerate: (s) =>
    !!s &&
    (s.lifecycle === Lifecycle.EDITING ||
      s.lifecycle === Lifecycle.AUTOSAVING ||
      s.lifecycle === Lifecycle.READY_TO_GENERATE ||
      s.lifecycle === Lifecycle.FAILED) &&
    (!!s.title?.trim() || !!s.storyText?.trim()),
  lastError: (s) => s?.meta?.lastError || null,
  lastRequestId: (s) => s?.meta?.lastRequestId || null,
  legalNext: (s) => legalNextStates(s?.lifecycle || Lifecycle.IDLE),
};

// ─── Wire-format mapping (server <-> client field names) ─────────────────
// The backend uses snake_case (draft_id, story_text, attached_job_id, etc.)
// The frontend uses camelCase. This is the SINGLE place that knows the map.
export function fromServerState(serverState, requestId = null) {
  if (!serverState) return null;
  return {
    draftId: serverState.draft_id,
    schemaVersion: serverState.schema_version,
    version: serverState.version,
    lifecycle: serverState.lifecycle,
    title: serverState.title || '',
    storyText: serverState.story_text || '',
    animationStyle: serverState.animation_style || null,
    ageGroup: serverState.age_group || null,
    voicePreset: serverState.voice_preset || null,
    attachedJobId: serverState.attached_job_id || null,
    createdAt: serverState.created_at || null,
    updatedAt: serverState.updated_at || null,
    archivedAt: serverState.archived_at || null,
    allowedNext: serverState.allowed_next || [],
    requestId,
  };
}
