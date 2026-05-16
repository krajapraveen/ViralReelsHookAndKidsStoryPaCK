/**
 * storySession reducer — pure unit tests
 * ========================================
 * Run with: cd frontend && yarn test src/state/__tests__
 *
 * No React, no DOM, no fetch — just the reducer + lifecycle table.
 * Locks in:
 *   • Lifecycle transition graph matches the backend
 *   • Immutable updates (state is never mutated in-place)
 *   • LOCAL_EDIT is rejected in terminal/in-flight states
 *   • RESYNC replaces server-authoritative fields without flicker
 *   • SAVE_FAILED carries the request_id for the recovery UX
 */
import {
  Actions,
  Lifecycle,
  actions,
  fromServerState,
  initialStorySessionState,
  isLegalTransition,
  legalNextStates,
  selectors,
  storySessionReducer,
} from '../storySession';

describe('Lifecycle table', () => {
  test('matches canonical state graph (mirrors backend)', () => {
    const expected = {
      IDLE: ['ARCHIVED', 'EDITING'],
      EDITING: ['ARCHIVED', 'AUTOSAVING', 'READY_TO_GENERATE'],
      AUTOSAVING: ['ARCHIVED', 'EDITING', 'READY_TO_GENERATE'],
      READY_TO_GENERATE: ['ARCHIVED', 'EDITING', 'GENERATING'],
      GENERATING: ['FAILED', 'READY'],
      READY: ['ARCHIVED'],
      FAILED: ['ARCHIVED', 'EDITING'],
      ARCHIVED: [],
    };
    for (const [from, next] of Object.entries(expected)) {
      expect(legalNextStates(from)).toEqual(next);
    }
  });

  test('ARCHIVED is terminal — every outbound edge denied', () => {
    for (const v of Object.values(Lifecycle)) {
      if (v === Lifecycle.ARCHIVED) continue;
      expect(isLegalTransition(Lifecycle.ARCHIVED, v)).toBe(false);
    }
  });

  test('GENERATING cannot archive directly (pipeline owns the doc)', () => {
    expect(isLegalTransition(Lifecycle.GENERATING, Lifecycle.ARCHIVED)).toBe(
      false
    );
  });

  test('READY cannot revert to EDITING', () => {
    expect(isLegalTransition(Lifecycle.READY, Lifecycle.EDITING)).toBe(false);
  });

  test('FAILED can recover to EDITING', () => {
    expect(isLegalTransition(Lifecycle.FAILED, Lifecycle.EDITING)).toBe(true);
  });

  test('idempotent same-state transitions are legal', () => {
    for (const v of Object.values(Lifecycle)) {
      expect(isLegalTransition(v, v)).toBe(true);
    }
  });
});

describe('storySessionReducer', () => {
  test('returns initial state for unknown actions', () => {
    expect(storySessionReducer(undefined, { type: '__nope' })).toBe(
      initialStorySessionState
    );
  });

  test('HYDRATE replaces server-authoritative fields, preserves meta shape', () => {
    const s = storySessionReducer(
      initialStorySessionState,
      actions.hydrate({
        draftId: 'abc',
        version: 4,
        lifecycle: Lifecycle.EDITING,
        title: 'Hi',
        storyText: 'There',
        requestId: 'req-1',
      })
    );
    expect(s.draftId).toBe('abc');
    expect(s.version).toBe(4);
    expect(s.lifecycle).toBe(Lifecycle.EDITING);
    expect(s.title).toBe('Hi');
    expect(s.storyText).toBe('There');
    expect(s.meta.lastRequestId).toBe('req-1');
    expect(s.meta.saving).toBe(false);
    // Original untouched (immutability proof)
    expect(initialStorySessionState.draftId).toBe(null);
  });

  test('LOCAL_EDIT upgrades IDLE → EDITING', () => {
    const s = storySessionReducer(
      { ...initialStorySessionState, lifecycle: Lifecycle.IDLE },
      actions.localEdit({ title: 'x' })
    );
    expect(s.lifecycle).toBe(Lifecycle.EDITING);
    expect(s.title).toBe('x');
  });

  test('LOCAL_EDIT is a no-op in GENERATING', () => {
    const before = {
      ...initialStorySessionState,
      lifecycle: Lifecycle.GENERATING,
      title: 'locked',
    };
    const after = storySessionReducer(before, actions.localEdit({ title: 'no' }));
    expect(after.title).toBe('locked');
    expect(after.lifecycle).toBe(Lifecycle.GENERATING);
  });

  test('LOCAL_EDIT is a no-op in READY and ARCHIVED', () => {
    const ready = { ...initialStorySessionState, lifecycle: Lifecycle.READY, title: 'r' };
    expect(storySessionReducer(ready, actions.localEdit({ title: 'x' })).title).toBe('r');
    const archived = { ...initialStorySessionState, lifecycle: Lifecycle.ARCHIVED, title: 'a' };
    expect(storySessionReducer(archived, actions.localEdit({ title: 'x' })).title).toBe('a');
  });

  test('SAVE_PENDING flips saving=true, clears lastError', () => {
    const after = storySessionReducer(
      { ...initialStorySessionState, meta: { ...initialStorySessionState.meta, lastError: { code: 'X' } } },
      actions.savePending()
    );
    expect(after.meta.saving).toBe(true);
    expect(after.meta.lastError).toBe(null);
  });

  test('SAVE_OK advances version + lifecycle without touching domain fields', () => {
    const before = {
      ...initialStorySessionState,
      version: 2,
      lifecycle: Lifecycle.EDITING,
      title: 'Keep me',
    };
    const after = storySessionReducer(
      before,
      actions.saveOk({
        version: 3,
        lifecycle: Lifecycle.AUTOSAVING,
        updatedAt: '2026-05-17T00:00:00Z',
        requestId: 'req-2',
      })
    );
    expect(after.version).toBe(3);
    expect(after.lifecycle).toBe(Lifecycle.AUTOSAVING);
    expect(after.title).toBe('Keep me');
    expect(after.meta.lastRequestId).toBe('req-2');
    expect(after.meta.saving).toBe(false);
  });

  test('SAVE_FAILED carries error envelope to meta.lastError', () => {
    const after = storySessionReducer(
      initialStorySessionState,
      actions.saveFailed({
        code: 'STALE_WRITE',
        message: 'Old version',
        retryable: true,
        requestId: 'req-3',
      })
    );
    expect(after.meta.saving).toBe(false);
    expect(after.meta.lastError).toEqual({
      code: 'STALE_WRITE',
      message: 'Old version',
      retryable: true,
    });
    expect(after.meta.lastRequestId).toBe('req-3');
  });

  test('RESYNC behaves like HYDRATE for state replacement', () => {
    const after = storySessionReducer(
      { ...initialStorySessionState, version: 1, title: 'stale' },
      actions.resync({
        draftId: 'd',
        version: 9,
        lifecycle: Lifecycle.READY_TO_GENERATE,
        title: 'fresh',
      })
    );
    expect(after.version).toBe(9);
    expect(after.title).toBe('fresh');
    expect(after.lifecycle).toBe(Lifecycle.READY_TO_GENERATE);
  });

  test('RESET returns to initial state', () => {
    const dirty = { ...initialStorySessionState, draftId: 'x', version: 7 };
    const after = storySessionReducer(dirty, actions.reset());
    expect(after).toEqual(initialStorySessionState);
  });

  test('immutability: state is never mutated in place', () => {
    const before = { ...initialStorySessionState, title: 'orig' };
    const snapshot = JSON.stringify(before);
    storySessionReducer(before, actions.localEdit({ title: 'changed' }));
    expect(JSON.stringify(before)).toBe(snapshot);
  });
});

describe('selectors', () => {
  test('canEdit reflects lifecycle gates', () => {
    expect(selectors.canEdit({ lifecycle: Lifecycle.IDLE })).toBe(true);
    expect(selectors.canEdit({ lifecycle: Lifecycle.EDITING })).toBe(true);
    expect(selectors.canEdit({ lifecycle: Lifecycle.GENERATING })).toBe(false);
    expect(selectors.canEdit({ lifecycle: Lifecycle.READY })).toBe(false);
    expect(selectors.canEdit({ lifecycle: Lifecycle.ARCHIVED })).toBe(false);
  });

  test('canGenerate requires content + non-terminal lifecycle', () => {
    expect(
      selectors.canGenerate({
        lifecycle: Lifecycle.READY_TO_GENERATE,
        title: 'x',
        storyText: '',
      })
    ).toBe(true);
    expect(
      selectors.canGenerate({
        lifecycle: Lifecycle.READY_TO_GENERATE,
        title: '',
        storyText: '',
      })
    ).toBe(false);
    expect(
      selectors.canGenerate({
        lifecycle: Lifecycle.GENERATING,
        title: 'x',
        storyText: 'y',
      })
    ).toBe(false);
  });

  test('lastError + lastRequestId pass-through', () => {
    const s = {
      meta: { lastError: { code: 'STALE_WRITE' }, lastRequestId: 'r' },
    };
    expect(selectors.lastError(s).code).toBe('STALE_WRITE');
    expect(selectors.lastRequestId(s)).toBe('r');
  });
});

describe('fromServerState (wire-format mapping)', () => {
  test('translates snake_case → camelCase loss-free', () => {
    const wire = {
      draft_id: 'd-1',
      schema_version: 1,
      version: 5,
      lifecycle: 'EDITING',
      title: 'T',
      story_text: 'S',
      animation_style: 'cartoon_2d',
      age_group: 'kids_5_8',
      voice_preset: 'narrator_warm',
      attached_job_id: 'job-1',
      created_at: '2026-05-17T00:00:00Z',
      updated_at: '2026-05-17T00:00:01Z',
      archived_at: null,
      allowed_next: ['AUTOSAVING', 'READY_TO_GENERATE', 'ARCHIVED'],
    };
    const c = fromServerState(wire, 'req-x');
    expect(c.draftId).toBe('d-1');
    expect(c.storyText).toBe('S');
    expect(c.animationStyle).toBe('cartoon_2d');
    expect(c.attachedJobId).toBe('job-1');
    expect(c.allowedNext).toEqual(['AUTOSAVING', 'READY_TO_GENERATE', 'ARCHIVED']);
    expect(c.requestId).toBe('req-x');
  });

  test('returns null for null input', () => {
    expect(fromServerState(null)).toBe(null);
  });
});

describe('Actions enum (canonical wire identifiers)', () => {
  test('every documented action type is exported and unique', () => {
    const vals = Object.values(Actions);
    expect(new Set(vals).size).toBe(vals.length);
    for (const v of vals) expect(typeof v).toBe('string');
  });
});
