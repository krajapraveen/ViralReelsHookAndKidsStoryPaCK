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

## P0 CRITICAL: Data Integrity — Completed Means Persisted — DONE (Apr 12)

### Rule: A job is NEVER marked completed without a durable output_url.

### What was wrong:
- 22/27 "completed" jobs had NO output_url (videos on ephemeral storage)
- `should_mark_ready()` allowed up to 2 errors including missing output_url → PARTIAL_READY
- Users saw "Download" button on jobs with no downloadable file
- "Download not available" → trust-breaking UX

### Fixes Applied:
1. **`should_mark_ready()`**: Missing output_url is now a HARD FAILURE. Job cannot reach READY or PARTIAL_READY without durable URL.
2. **Backfill repair**: `POST /api/media/admin/repair-false-completed` reclassified 20 false-completed → `FAILED_PERSISTENCE`, 1 expired local file → `EXPIRED`
3. **Integrity monitoring**: `GET /api/media/admin/integrity-check` reports `healthy: true/false` based on zero completed-without-output rule
4. **Download-token validation**: Checks `output_url` → `preview_url` → `fallback_video_url`. Validates local files exist on disk. Returns structured errors: 202 (processing), 410 (expired/failed), 404 (not_ready).
5. **UI truthfulness**: StoryPreview shows "This video is no longer available" + "Regenerate Video" button for undownloadable jobs. No dead-end buttons.

### After Repair:
| Metric | Before | After |
|--------|--------|-------|
| healthy | false | **true** |
| completed_total | 27 (lying) | **6** (truthful) |
| with_r2_url | 4 | 4 |
| without_url | 20 | **0** |
| failed_persistence | 0 | 20 (honest) |

### Pipeline States:
```
rendering → uploading → READY (with durable R2 output_url)
                      → PARTIAL_READY (non-critical issues, but output exists)
                      → FAILED (critical failures)
                      → FAILED_PERSISTENCE (completed processing but no durable storage)
                      → EXPIRED (local file no longer exists)
```

---

## P0: Export Pipeline Fix — DONE (Apr 12)
- StoryPreview import fix (ProtectedContentContainer)
- Admin watermark bypass
- Structured download errors
- File existence validation
- Testing: iteration_503 — 8/8 (100%)

## Consumption-First Viral Loop — DONE (Apr 12)
- Phase 0: 12 baseline tracking events
- Phase 1: Watch-first CTA hierarchy everywhere
- Phase 2: Watch Page with engagement, auto-play, remix chain
- Testing: iteration_502 — 19/19 (100%)

## Entry Conversion Engine — DONE (Apr 12)
- Quick Shot, Personalized CTA, Pressure Timer, First-Win Boost, Streak Hook
- Testing: iteration_501 — 18/18 (100%)

---

## Key Files
- `/app/backend/services/story_engine/continuity.py` — `should_mark_ready()` with output_url hard rule
- `/app/backend/routes/media_routes.py` — Download token + repair + integrity check
- `/app/frontend/src/pages/StoryPreview.js` — Honest download state UI
- `/app/frontend/src/components/EntitledDownloadButton.js` — Structured error handling
- `/app/frontend/src/components/ProtectedContent.js` — Admin watermark bypass

---

## Backlog

### P0 (Next)
- Conversion Analytics Dashboard

### P1
- Secondary Action Matrix, Follow Creator, Phase C Gamification

### P2
- Resend domain, personalized headlines, hover autoplay
