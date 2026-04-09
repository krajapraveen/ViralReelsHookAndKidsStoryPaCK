# Visionary Suite - Product Requirements Document

## Original Problem Statement
Build an AI Creator Suite with a compulsion-driven "Growth Engine" — a full-stack application featuring AI video generation, social sharing loops, and monetization via credits and payments. The platform must create irresistible user journeys from discovery to creation and sharing.

## Architecture
- **Frontend**: React (CRA) + TailwindCSS + Shadcn/UI
- **Backend**: FastAPI + MongoDB + Redis
- **Integrations**: OpenAI (GPT-4o-mini, GPT Image 1, Sora 2, TTS), Gemini, Cloudflare R2, Cashfree, Google Auth (Emergent-managed)
- **Key URL**: https://trust-engine-5.preview.emergentagent.com

## Core User Personas
- **Creators**: Generate AI videos from story prompts, customize styles, share socially
- **Admins**: Monitor platform health, revenue, user metrics

## Credentials
- Test: test@visionary-suite.com / Test@2026#
- Admin: admin@creatorstudio.ai / Cr3@t0rStud!o#2026

---

## What's Been Implemented

### P0 Growth Loop (Compulsion Engine) — DONE
- Redesigned public pages with momentum-based social proof
- 1-click continue flow (generation before login)
- Enforced open-loop story endings
- Enhanced social proof (momentum messaging, Character Power Score, time-based decay)

### P1 Monetization — DONE
- Cashfree payments wired
- Strict credit checks on all generation tools
- 50-credit standard for all normal users
- Admin Dashboard with real revenue/credit metrics

### MySpace UX Overhaul — DONE
- Plain-English copy, fuzzy time estimates, asset explanations
- Skeleton loading, completed card pulse, re-engagement buttons
- Credit psychology nudges

### Pipeline Resilience — DONE
- Graceful degradation: character continuity failures → warnings with fallbacks
- Pipeline continues with simplified prompts instead of crashing

### Remix Gallery — DONE
- Anonymous opt-in, filtered auto-seeding, "Remix This" flow
- Trending badges

### Addiction Layer — DONE
- "Your vs Popular" comparisons, instant one-click variants
- Session-based streaks

### Trust & UI Fixes — DONE
- Fixed broken Profile → Security tab
- Truth-based admin satisfaction metric
- Diverse, non-repeating "Live on the Platform" feed
- Credit system consistency (eliminated hidden 100-credit grants)

### P0 Failed Job Recovery Routing — DONE (Apr 9, 2026)
- **Root cause**: StoryVideoPipeline.js didn't read `projectId` from URL on page load
- **Fix**: Server-authoritative `view_mode` routing (progress/result/failed_recovery)
- Added `loadProjectById` deep-link handler
- Built dedicated `FailedRecoveryScreen` with dynamic failure-specific messaging
- Centralized `FAILED_STATE_LABELS` map — no raw enums leak to UI
- Backend DELETE /api/story-engine/jobs/{job_id} endpoint
- Recovery analytics tracking (failed_job_viewed, retry_clicked, edit_retry_clicked, delete_failed_project)
- MySpacePage "Retry" triggers actual API retry (not just navigation)
- Legacy pipeline_jobs also include view_mode and retry_info
- **Testing**: 17/18 passed, 0 failed (iteration_470)

---

## Prioritized Backlog

### P0 — Retention Layer (Next)
- In-App Notification System (remix, trending, daily challenge triggers)
- Email comeback hooks
- "Your Story" ownership messaging in MySpace cards
- Daily Challenge block on homepage
- Soft leaderboard ("Top Stories Today")
- Auto-play gallery hover preview

### P1 — Quality & Transparency
- "Improve consistency" CTA on completed cards (regenerate character stage)
- Quality transparency note for character fallback
- Smarter retry logic (simplify prompt on retry)
- Improved fallback descriptions (extract adjectives from story text)
- A/B test hook text variations on public pages

### P2 — Growth & Polish
- "Remix Variants" on share pages
- Character-driven auto-share prompts after creation
- Admin dashboard WebSocket upgrade
- Style preset preview thumbnails
- "Story Chain" leaderboard

---

## Key Files
- `/app/frontend/src/pages/StoryVideoPipeline.js` — Studio + recovery routing
- `/app/frontend/src/pages/MySpacePage.js` — Dashboard + project cards
- `/app/frontend/src/components/RemixGallery.js` — Social growth loop
- `/app/backend/routes/story_engine_routes.py` — Job APIs + view_mode routing
- `/app/backend/services/story_engine/pipeline.py` — Async generation pipeline
