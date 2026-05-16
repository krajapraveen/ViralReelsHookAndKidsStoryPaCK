/**
 * Story Session API client (2026-05-17, Session 2)
 * ===================================================
 * Thin, version-aware fetch wrapper around the new canonical endpoints.
 * Lives below the reducer; speaks the wire format and translates to/from
 * the camelCase domain model.
 *
 * Every method returns a Promise of `{ ok, state?, error?, requestId }`:
 *   • ok=true  → state present, fresh canonical view
 *   • ok=false → error.code is one of ErrorCode (STALE_WRITE, …) and
 *                error.currentVersion is present on stale writes so the
 *                caller can replay its local edit.
 *
 * NEVER throws on 4xx. Network/5xx errors still throw — those are programmer
 * bugs (auth missing, etc.) and the global axios interceptor handles them.
 */
import api from '../utils/api';
import { ErrorCode, fromServerState } from './storySession';

function _toClientError(detail, requestId) {
  if (!detail || typeof detail !== 'object') {
    return { code: 'UNKNOWN', message: 'Unknown error', retryable: false, requestId };
  }
  return {
    code: detail.code || 'UNKNOWN',
    message: detail.message || '',
    retryable: !!detail.retryable,
    currentVersion: detail.current_version ?? null,
    activeDraftId: detail.active_draft_id ?? null,
    allowedNext: detail.allowed_next ?? null,
    requestId: detail.request_id || requestId,
    extra: detail,
  };
}

function _envelope(resp) {
  const requestId =
    resp?.headers?.['x-request-id'] || resp?.data?.request_id || null;
  return { requestId, data: resp?.data || {} };
}

// ─── GET /api/drafts/{draftId}/state ────────────────────────────────────
export async function fetchSessionState(draftId) {
  try {
    const resp = await api.get(`/api/drafts/${draftId}/state`);
    const { requestId, data } = _envelope(resp);
    return {
      ok: true,
      state: fromServerState(data.state, requestId),
      requestId,
    };
  } catch (e) {
    const requestId = e?.response?.headers?.['x-request-id'] || null;
    return {
      ok: false,
      error: _toClientError(e?.response?.data?.detail, requestId),
      requestId,
    };
  }
}

// ─── POST /api/drafts/session — create new canonical session ────────────
export async function createSession() {
  try {
    const resp = await api.post('/api/drafts/session', {});
    const { requestId, data } = _envelope(resp);
    return {
      ok: true,
      state: fromServerState(data.state, requestId),
      requestId,
    };
  } catch (e) {
    const requestId = e?.response?.headers?.['x-request-id'] || null;
    return {
      ok: false,
      error: _toClientError(e?.response?.data?.detail, requestId),
      requestId,
    };
  }
}

// ─── POST /api/drafts/{draftId}/patch — optimistic-locked update ───────
export async function patchSession({
  draftId,
  expectedVersion,
  patch,
  nextLifecycle,
}) {
  // Translate camelCase → snake_case for the wire payload.
  const wire = {
    expected_version: expectedVersion,
    patch: {},
    next_lifecycle: nextLifecycle || null,
  };
  if (patch?.title !== undefined) wire.patch.title = patch.title;
  if (patch?.storyText !== undefined) wire.patch.story_text = patch.storyText;
  if (patch?.animationStyle !== undefined)
    wire.patch.animation_style = patch.animationStyle;
  if (patch?.ageGroup !== undefined) wire.patch.age_group = patch.ageGroup;
  if (patch?.voicePreset !== undefined)
    wire.patch.voice_preset = patch.voicePreset;

  try {
    const resp = await api.post(`/api/drafts/${draftId}/patch`, wire);
    const { requestId, data } = _envelope(resp);
    return {
      ok: true,
      state: fromServerState(data.state, requestId),
      requestId,
    };
  } catch (e) {
    const requestId = e?.response?.headers?.['x-request-id'] || null;
    const err = _toClientError(e?.response?.data?.detail, requestId);
    return {
      ok: false,
      error: err,
      // Stale writes are recoverable — let callers replay.
      stale: err.code === ErrorCode.STALE_WRITE,
      requestId,
    };
  }
}

// ─── POST /api/drafts/{draftId}/transition — pure lifecycle move ───────
export async function transitionSession({
  draftId,
  expectedVersion,
  nextLifecycle,
  attachedJobId,
}) {
  const wire = {
    expected_version: expectedVersion,
    next_lifecycle: nextLifecycle,
    attached_job_id: attachedJobId || null,
  };
  try {
    const resp = await api.post(`/api/drafts/${draftId}/transition`, wire);
    const { requestId, data } = _envelope(resp);
    return {
      ok: true,
      state: fromServerState(data.state, requestId),
      requestId,
    };
  } catch (e) {
    const requestId = e?.response?.headers?.['x-request-id'] || null;
    const err = _toClientError(e?.response?.data?.detail, requestId);
    return {
      ok: false,
      error: err,
      stale: err.code === ErrorCode.STALE_WRITE,
      illegal: err.code === ErrorCode.ILLEGAL_TRANSITION,
      requestId,
    };
  }
}

export default {
  fetchSessionState,
  createSession,
  patchSession,
  transitionSession,
};
