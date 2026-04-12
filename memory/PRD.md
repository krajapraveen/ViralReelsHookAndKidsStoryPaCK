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

## P0 Bug Fix: "Unfinished Worlds" Story Not Found — DONE (Apr 12)

### Root Cause:
Feed API (`engagement.py`) queries `pipeline_jobs` for Unfinished Worlds cards, but Viewer API (`story_multiplayer.py`) only queries `story_engine_jobs`. Classic **feed/detail contract mismatch** — cards were clickable but not loadable.

### Fixes:
1. **Viewer endpoint** now checks both `story_engine_jobs` AND `pipeline_jobs` (fallback). Handles different field names (`state` vs `status`).
2. **Engagement feed** tags `pipeline_jobs` items with `source: "pipeline"` for downstream routing.
3. **Graceful fallback UI** — instead of toast + redirect, shows "Story not available" page with "Browse Stories" and "Go Back" buttons.

### Rule enforced: **clickable = loadable**

---

## P0: Post-Launch-Branch Flow — DONE (Apr 12)
- "Entering battle..." loading, Battle Entry Banner on pipeline, auto-redirect to Watch Page
- Testing: iteration_504 — 12/12 (100%)

## Data Integrity — DONE (Apr 12)
## Export Pipeline — DONE (Apr 12)
## Consumption-First Loop — DONE (Apr 12)
## Entry Conversion Engine — DONE (Apr 12)

---

## Backlog

### P0 (Next)
- Conversion Analytics Dashboard

### P1
- Auto-Recovery for FAILED_PERSISTENCE, Secondary Action Matrix, Follow Creator

### P2
- Resend domain, personalized headlines, hover autoplay
