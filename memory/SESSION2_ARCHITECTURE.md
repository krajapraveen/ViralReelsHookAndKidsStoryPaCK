# P0 Platform Stability Sprint — Session 2

## Canonical StorySessionState + Explicit State Machine + Optimistic Locking

**Date**: 2026-05-17  
**Status**: Foundation SHIPPED. Migration of live pages NOT started (intentional).  
**Production freeze**: still in effect (architecture-only).

---

## 1. Summary

Session 2 lays the **foundation primitives** that eliminate the class of bugs the founder
flagged: race-saved overwrites, phantom UI, tab corruption, distributed state ownership,
and non-deterministic hydration. The foundation is shipped behind backward-compatible
endpoints. No live UI was rewritten. The migration of consumers to the new contract is
a separate, gated rollout (Session 3).

The 10 mandated requirements are all met by the new module surface:

| # | Requirement | Where it lives |
|---|---|---|
| 1 | One canonical StorySessionState | `backend/models/story_session.py` :: `StorySessionState` |
| 2 | Explicit lifecycle transitions | `Lifecycle` enum + `_LEGAL_TRANSITIONS` graph |
| 3 | Illegal transition guards | `is_legal_transition()` + `patched()` raises `ILLEGAL_TRANSITION` |
| 4 | Draft version incrementing | `version` field; bumped on every `patched()` |
| 5 | Stale write rejection | `services/story_session_service.py` :: optimistic-lock CAS |
| 6 | Deterministic hydration | `GET /api/drafts/{id}/state` — single source-of-truth read |
| 7 | Single source of truth | All writes route through `story_session_service` |
| 8 | Immutable updates | Pydantic `frozen=True` + `patched()` returns new instance |
| 9 | Strict ownership by draft_id/job_id | Every service call requires `(draft_id, user_id)` |
| 10 | Regression coverage first-class | 38 backend + 23 frontend = 61 new tests, 144 cumulative |

---

## 2. State Transition Diagram

```
                       ┌──────────┐
                       │   IDLE   │  (fresh blank draft)
                       └────┬─────┘
                            │  user types
                            ▼
                       ┌──────────┐    autosave fires    ┌─────────────┐
                       │ EDITING  │ ───────────────────▶ │ AUTOSAVING  │
                       └────┬─────┘ ◀─────────────────── └──────┬──────┘
                            │     user kept typing              │
                            │                                   │
                            │   validation passes               │
                            ▼                                   ▼
                       ┌─────────────────────────────────────────────┐
                       │           READY_TO_GENERATE                 │
                       └────┬────────────────────────────────────────┘
                            │  user clicks Generate
                            ▼
                       ┌──────────┐  pipeline succeeds   ┌──────────┐
                       │GENERATING│ ───────────────────▶ │  READY   │  (terminal-ish)
                       └────┬─────┘                      └────┬─────┘
                            │  pipeline fails                 │
                            ▼                                 │
                       ┌──────────┐                           │
                       │  FAILED  │ ──▶ EDITING               │
                       └────┬─────┘     (retry)               │
                            │                                 │
                            ▼                                 ▼
                                       ┌──────────┐
                                       │ ARCHIVED │  (terminal, soft-deleted)
                                       └──────────┘

LEGAL EDGES (mirrors `_LEGAL_TRANSITIONS` in models/story_session.py)
  IDLE              → EDITING, ARCHIVED
  EDITING           → AUTOSAVING, READY_TO_GENERATE, ARCHIVED
  AUTOSAVING        → EDITING, READY_TO_GENERATE, ARCHIVED
  READY_TO_GENERATE → EDITING, GENERATING, ARCHIVED
  GENERATING        → READY, FAILED                ◀── ARCHIVE FORBIDDEN
  READY             → ARCHIVED                     ◀── EDITING FORBIDDEN
  FAILED            → EDITING, ARCHIVED
  ARCHIVED          → ∅                            ◀── TERMINAL
```

**Why GENERATING cannot ARCHIVE directly**: the pipeline owns the document during
generation. Start Fresh on a generating draft must first cancel the pipeline (which
transitions the draft to FAILED), then archive. This is what eliminates the comic
storybook "stuck-active" duplicate-generation class of bug at the architecture level.

**Why READY cannot revert to EDITING**: clean contract. Remix-into-same-draft is a
future design decision (would require a v2 schema migration).

---

## 3. Files Changed / Added

### Backend (NEW)
| File | Purpose | LOC |
|---|---|---|
| `backend/models/story_session.py` | Pydantic model, `Lifecycle` enum, transition table, error codes | 312 |
| `backend/services/story_session_service.py` | Single source-of-truth writes with optimistic CAS | 285 |

### Backend (EDITED, backward-compatible additions only)
| File | Change |
|---|---|
| `backend/routes/drafts.py` | Added 4 new endpoints + service hookups; legacy endpoints untouched |

### Backend tests (NEW)
| File | Tests |
|---|---|
| `backend/tests/test_story_session_state_machine_2026_05.py` | 24 (pure model + state machine) |
| `backend/tests/test_session2_drafts_service_2026_05.py` | 14 (service + route integration) |

### Frontend (NEW, not yet wired into live pages)
| File | Purpose |
|---|---|
| `frontend/src/state/storySession.js` | Pure reducer, lifecycle constants, action creators, selectors, wire-format mapping |
| `frontend/src/state/storySessionClient.js` | Version-aware API client (CRUD: fetch / create / patch / transition) |
| `frontend/src/state/useStorySession.js` | React hook (orchestration + auto-resync) |

### Frontend tests (NEW)
| File | Tests |
|---|---|
| `frontend/src/state/__tests__/storySession.test.js` | 23 (reducer, lifecycle, selectors, wire mapping) |

---

## 4. New API surface (backward-compatible)

```
GET    /api/drafts/{draft_id}/state          Canonical hydration (incl. version + lifecycle + allowed_next)
POST   /api/drafts/session                    Service-backed session create (refuses if active draft exists)
POST   /api/drafts/{draft_id}/patch           Version-locked partial update + optional lifecycle transition
POST   /api/drafts/{draft_id}/transition      Pure lifecycle move (e.g., pipeline GENERATING → READY)
```

Legacy endpoints (`/drafts/save`, `/drafts/current`, `/drafts/recent`, `/drafts/{id}`,
`/drafts/archive`, `/drafts/create`, `/drafts/status`, `/drafts/discard`, `/drafts/idea`)
all remain working untouched. No existing client breaks.

### Canonical state payload shape

```json
{
  "success": true,
  "state": {
    "draft_id": "abc...",
    "schema_version": 1,
    "version": 7,
    "lifecycle": "EDITING",
    "legacy_status": "draft",
    "title": "...",
    "story_text": "...",
    "animation_style": "cartoon_2d",
    "age_group": "kids_5_8",
    "voice_preset": "narrator_warm",
    "attached_job_id": null,
    "created_at": "2026-05-17T...",
    "updated_at": "2026-05-17T...",
    "archived_at": null,
    "allowed_next": ["ARCHIVED", "AUTOSAVING", "READY_TO_GENERATE"]
  },
  "request_id": "..."
}
```

### Structured error envelopes

Every error response carries:
```json
{
  "detail": {
    "code": "STALE_WRITE",            // canonical enum value
    "message": "human-readable",
    "request_id": "...",              // from middleware
    "retryable": true,                // whether client should retry
    "current_version": 12,            // (STALE_WRITE only) — for replay
    "allowed_next": [...]             // (ILLEGAL_TRANSITION only) — for UX
  }
}
```

Specific error codes:
- `DRAFT_NOT_FOUND` (404) — draft missing or owned by another user (same envelope; never leak existence)
- `DRAFT_ALREADY_ACTIVE` (409) — `/session` refused because user already has one
- `STALE_WRITE` (409, retryable) — client's `expected_version` lost the CAS race
- `ILLEGAL_TRANSITION` (409) — `next_lifecycle` not in `_LEGAL_TRANSITIONS[current]`
- `DRAFT_SCHEMA_UNSUPPORTED` (409) — document's `schema_version` is from the future
- `INVALID_PATCH` (400) — patch payload contained no actionable fields

---

## 5. Migration Strategy

The migration is intentionally **opt-in** and **per-page**. Pages call the legacy
endpoints today; they switch to the new contract one at a time after smoke verification.

### Migration phases

1. **Foundation (this session, COMPLETE)** — model + service + endpoints + tests. Zero
   live page touched. No behavior change visible to users.

2. **Read-side observer (Session 3a, NOT STARTED)** — wire `useStorySession` into
   `StoryVideoPipeline.js` as a **read-only observer** alongside the existing
   `useState` ownership. Logs any divergence between the two state shapes. No writes
   yet — pure shadow mode. ~1 day, low risk.

3. **Write migration: autosave (Session 3b, NOT STARTED)** — replace `api.post('/api/drafts/save', ...)`
   with `commit({ patch, nextLifecycle: 'AUTOSAVING' })`. Old `/save` endpoint stays
   available for rollback. Frontend hook handles `STALE_WRITE` auto-resync.

4. **Write migration: lifecycle (Session 3c)** — replace `api.post('/api/drafts/status', ...)`
   with `transition({ nextLifecycle })`. Pipeline workers move to
   `POST /drafts/{id}/transition` for GENERATING → READY/FAILED.

5. **Comic Storybook P0 stuck-active fix (Session 4)** — once GENERATING is owned by
   the state machine, the comic storybook "Your comic is already generating" stale-state
   class is structurally impossible (the doc cannot stay in GENERATING after the
   pipeline emits READY/FAILED). Add a janitor that scans for GENERATING drafts whose
   pipeline jobs are in terminal status and transitions them.

6. **Legacy retirement (Session 5+)** — once every consumer is on the new contract,
   the legacy `/save`, `/status`, `/discard` endpoints can be deprecated. Not before.

### Why this order

The foundation lands first (this session). The risky part — touching the live
3,467-line `StoryVideoPipeline.js` — is gated behind a separate user-verified
deploy. The user explicitly required Session 2 before Comic Storybook because
the latter is a downstream symptom; this ordering enforces that contract.

---

## 6. Backward Compatibility Risks

| Risk | Mitigation |
|---|---|
| Pre-Session-2 documents lack `version` and `lifecycle` fields | `StorySessionState.from_mongo()` backfills both; live tested by `test_legacy_*` tests |
| Pre-Session-2 documents lack `draft_id` (only `_id`) | `_find_draft_doc()` falls back to ObjectId lookup if hex |
| Existing autosave (`/save`) writes `version` only when going through service | We intentionally leave `/save` last-write-wins for now. Service-backed callers get full optimistic locking; legacy callers continue working as before. No silent data corruption — they just don't gain stale-write protection until migrated. |
| Frontend reducer divergence from backend graph | Both graphs cited in tests; any drift is a CI failure (`test_legal_transitions_match_spec` on backend + `matches canonical state graph (mirrors backend)` on frontend) |
| Test isolation across new + legacy fixtures | New `clean_slate` fixture does direct DB delete (legacy `/archive` cannot reach `processing` rows) |
| Pipeline workers writing directly to `story_drafts` collection | None currently. If discovered, route them through `transition_session(next=READY/FAILED)`. |

---

## 7. Cumulative Test Count

| Suite | Pre-Session-2 | New This Session | Total |
|---|---|---|---|
| Backend (Resume-Draft, Reliability, Modal Trust, MySpace, Prod UX, P2C/Reel KPI) | 106 | — | 106 |
| Backend (StorySession state machine — pure) | — | 24 | 24 |
| Backend (Session 2 service+routes integration) | — | 14 | 14 |
| Frontend (storySession reducer + selectors + wire) | — | 23 | 23 |
| **TOTAL** | **106** | **61** | **167** |

All 144 backend tests + 23 frontend reducer tests passing at ship time.

Cumulative across the entire P0 Stability Sprint (Sessions 0-2): **167 tests, 100% green.**

---

## 8. Remaining Architectural Risk Areas

These are the **known unaddressed risks** going into Session 3. Listing them
explicitly so the next agent doesn't waste a turn rediscovering them.

### A. `StoryVideoPipeline.js` still has split ownership (HIGH)
The page has **22 `useState` hooks** for editor fields, autosave timer, draft id,
and pending-draft snapshots. Until the page migrates to `useStorySession`, the
new contract is not protecting live users — it's purely available infrastructure.

**Mitigation today**: foundation primitives are in place; migration is a 1-2 day
job per major page, with rollback via leaving the legacy endpoints active.

### B. Pipeline workers still write `status="completed"` directly (MEDIUM)
Several pipeline services emit `db.pipeline_jobs.update_one({"state": "READY"})`
but do **not** transition the linked `story_drafts` document. There is no current
link between `pipeline_jobs.state` and `story_drafts.lifecycle`. Session 3c
introduces this link via `transition_session(GENERATING → READY)` called from the
pipeline completion handler.

### C. localStorage still owns cross-tool hydration (MEDIUM)
`remix_video`, `remix_data` localStorage keys are still the only working channel
between tools (Comic → Reel, Reel → Story, etc.) because React Router drops
`location.state` on external hard navigates. The Session 2 service is per-tool;
cross-tool hydration is a separate sprint.

### D. Comic Storybook P0 not started (HIGH — but gated by user)
The user explicitly paused this. The state machine + janitor will make it
structurally impossible, but the implementation is Session 4.

### E. There's no admin "draft inspector" UI (LOW)
For ops debugging, an admin endpoint to view raw `StorySessionState` JSON for any
draft would speed up bug triage. Easy add: `GET /api/admin/drafts/{id}/raw`.
Out of scope this session.

### F. `version` field is per-draft, not per-field (BY DESIGN)
A concurrent autosave + lifecycle transition cannot both win — exactly one wins
the CAS, the other gets STALE_WRITE and retries. This is correct under our model
(autosave is one writer; the user is one writer; the pipeline is one writer; only
one per draft at any time). If we ever fan out to multi-writer per draft (e.g.,
collaborative editing), per-field versions become needed.

---

## 9. What was NOT touched (discipline maintained)

- `StoryVideoPipeline.js` (3,467 lines) — zero changes
- `MySpacePage.js` — zero changes
- Comic Storybook Builder — zero changes
- Any UI styling, copy, or visual surface — zero changes
- Auth, billing, pipeline, R2 — zero changes

**Production freeze: still in effect.**

---

## 10. Next session entry point

For the next agent:

> Read `/app/memory/SESSION2_ARCHITECTURE.md`. The foundation is shipped and tested.
> The migration of `StoryVideoPipeline.js` to `useStorySession` is the next P0 task —
> but wait for explicit user approval, because it touches the live editor and the
> production freeze is still active. The comic-storybook stuck-active bug is gated
> behind this migration; do not attempt to patch it directly.
