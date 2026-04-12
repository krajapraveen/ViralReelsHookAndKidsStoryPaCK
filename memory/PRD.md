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

## Queue System (Hardened) — DONE (Apr 12)

### Design: Accept then queue, never reject user intent.

**States**: QUEUED → INIT (promoted via FIFO) → pipeline stages → READY/FAILED
**Capacity**: MAX_CONCURRENT_JOBS = 2 per user

**Guarantees:**
- FIFO ordering: sort by `created_at` ASC
- No duplicate execution: `update_one` with `state=QUEUED` filter
- Credits deducted ONCE at creation, not again on promotion (no double billing)
- Queue drains on BOTH success (`_finalize_job`) AND failure (`_fail_job_terminal`)
- Queue position visible in UI: "Queued for rendering — position #N"
- SLOTS_BUSY error eliminated entirely from codebase
- RATE_LIMIT prefix for hourly/daily abuse prevention (10/hr, 50/day)

**Key files:**
- `/app/backend/services/story_engine/schemas.py` — JobState.QUEUED enum
- `/app/backend/services/story_engine/state_machine.py` — QUEUED transitions, labels, progress
- `/app/backend/services/story_engine/safety.py` — check_rate_limits, should_queue_job
- `/app/backend/services/story_engine/pipeline.py` — create_job (QUEUED state), _drain_queue_for_user, _finalize_job, _fail_job_terminal

Testing: iteration_505 (15/15) + iteration_506 (21/21) + manual 6/6 queue integrity tests

---

## Completed (All Apr 12)
- Unfinished Worlds fix (viewer checks pipeline_jobs + graceful fallback)
- Post-Launch-Branch flow (battle entry experience)
- Data Integrity (completed = persisted)
- Export Pipeline fix
- Consumption-First Viral Loop
- Entry Conversion Engine
- System Integrity

---

## Backlog

### P0 (Next)
- Conversion Analytics Dashboard

### P1
- Auto-Recovery FAILED_PERSISTENCE, Secondary Action Matrix, Follow Creator

### P2
- Resend domain, personalized headlines, hover autoplay
