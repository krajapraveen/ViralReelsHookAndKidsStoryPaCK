# Visionary Suite - Product Requirements Document

## Architecture
- **Frontend**: React (CRA) + TailwindCSS + Shadcn/UI
- **Backend**: FastAPI + MongoDB + Redis
- **URL**: https://trust-engine-5.preview.emergentagent.com

## Credentials
- Test: test@visionary-suite.com / Test@2026#
- Admin: admin@creatorstudio.ai / Cr3@t0rStud!o#2026

---

## Core Philosophy: WATCH > MAKE YOUR VERSION > CREATE

---

## P0: SLOTS_BUSY → Queue System — DONE (Apr 12)

### Before: "All rendering slots are busy" → dead-end error toast → user leaves
### After: Job QUEUED → auto-renders when slot frees → never blocks user intent

**Implementation:**
- `check_rate_limits()` no longer blocks for concurrent slots. Returns None to allow creation.
- `should_queue_job()` detects when active jobs >= MAX_CONCURRENT_JOBS (2)
- `create_job()` sets state=QUEUED when slots busy. Credits still deducted, job still created.
- `_finalize_job()` auto-drains queue: when a job completes, promotes oldest QUEUED → INIT + runs pipeline (FIFO)
- All callers (quick-shot, continue-branch, continue-episode, instant-rerun) check `result.queued` before `run_pipeline()`
- Frontend shows "Queued for rendering" toast (not error)
- `detect_abuse()` uses RATE_LIMIT prefix, never SLOTS_BUSY

### States: QUEUED → INIT (promoted) → pipeline stages → READY
### Testing: iteration_505 — 15/15 (100%)

---

## P0: Unfinished Worlds Fix — DONE (Apr 12)
- Viewer endpoint checks pipeline_jobs as fallback
- Graceful "Story not available" page for invalid IDs
- Rule: clickable = loadable

## P0: Post-Launch-Branch Flow — DONE (Apr 12)
## Data Integrity — DONE (Apr 12)
## Export Pipeline — DONE (Apr 12)
## Consumption-First Loop — DONE (Apr 12)
## Entry Conversion Engine — DONE (Apr 12)

---

## Backlog

### P0 (Next)
- Conversion Analytics Dashboard

### P1
- Auto-Recovery FAILED_PERSISTENCE, Secondary Action Matrix, Follow Creator

### P2
- Resend domain, personalized headlines, hover autoplay
