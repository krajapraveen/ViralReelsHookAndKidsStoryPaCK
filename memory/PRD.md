# Visionary Suite - Product Requirements Document

## Original Problem Statement
Build an AI Creator Suite with a compulsion-driven "Growth Engine" — a full-stack application featuring AI video generation, social sharing loops, and monetization via credits and payments. The platform must create irresistible user journeys from discovery to creation and sharing, with a retention layer that pulls users back daily.

## Architecture
- **Frontend**: React (CRA) + TailwindCSS + Shadcn/UI
- **Backend**: FastAPI + MongoDB + Redis
- **Integrations**: OpenAI (GPT-4o-mini, GPT Image 1, Sora 2, TTS), Gemini, Cloudflare R2, Cashfree, Google Auth (Emergent-managed)
- **Key URL**: https://trust-engine-5.preview.emergentagent.com

## Core User Personas
- **Creators**: Generate AI videos from story prompts, customize styles, share socially
- **Admins**: Monitor platform health, revenue, user metrics, manage daily challenges

## Credentials
- Test: test@visionary-suite.com / Test@2026#
- Admin: admin@creatorstudio.ai / Cr3@t0rStud!o#2026

---

## What's Been Implemented

### P0 Growth Loop (Compulsion Engine) — DONE
- Redesigned public pages with momentum-based social proof
- 1-click continue flow (generation before login)
- Enforced open-loop story endings

### P1 Monetization — DONE
- Cashfree payments wired
- Strict credit checks, 50-credit standard for all normal users

### MySpace UX Overhaul — DONE
- Plain-English copy, fuzzy time estimates, skeleton loading

### Pipeline Resilience — DONE
- Graceful degradation: character continuity failures → warnings with fallbacks

### Remix Gallery — DONE
- Anonymous opt-in, filtered auto-seeding, "Remix This" flow, Trending badges

### Addiction Layer — DONE
- "Your vs Popular" comparisons, instant one-click variants, session streaks

### Trust & UI Fixes — DONE
- Fixed Profile → Security, truth-based admin metrics, diverse live feed

### P0 Failed Job Recovery Routing — DONE (Apr 9, 2026)
- Server-authoritative `view_mode` routing (progress/result/failed_recovery)
- Dedicated `FailedRecoveryScreen` with dynamic failure-specific messaging
- Deep-link support via `projectId` query param
- Recovery analytics tracking
- Backend DELETE /api/story-engine/jobs/{job_id} endpoint
- **Testing**: 17/18 passed (iteration_470)

### Retention Layer — Release 1 — DONE (Apr 9, 2026)
- **In-App Notification System**: Bell icon in GlobalUserBar with unread badge, dropdown with clickable notifications. New types: `story_remixed`, `story_trending`, `daily_challenge_live`, `ownership_milestone`. Throttling: 30min aggregation for remix notifications, 12h cooldown for trending, 1/day for challenges.
- **Ownership Messaging**: MySpace ProjectCard shows remix counts ("X people remixed your story", "People are remixing YOUR idea") with Trending badge for 5+ remixes.
- **Daily Challenge System**: Admin-configurable challenges stored in MongoDB. Dashboard banner with "Today's Challenge" + Join Challenge CTA. Tracks participation count.
- **Soft Leaderboard**: "Top Stories Today" section on Dashboard (populated when gallery jobs exist with views).
- **Mock Email Service**: Provider-agnostic `send_email()` abstraction. All emails simulated/logged to `email_events` collection. Admin preview panel at `/api/retention/email-events`.
- **Remix Notification Triggers**: Automatic notification to original author when their story is remixed. Milestone notifications at 5, 10, 25, 50, 100 remixes.
- **Testing**: 25/25 passed (iteration_471)

---

## Prioritized Backlog

### P0 — Retention Layer (Remaining)
- Email comeback hooks — wire real provider (Resend recommended)
- Auto-play gallery hover preview (hover card → muted preview)
- Challenge participation tracking in Studio

### P1 — Quality & Transparency
- "Improve consistency" CTA on completed cards
- Quality transparency note for character fallback
- Smarter retry logic (simplify prompt on retry)
- A/B test hook text variations on public pages

### P2 — Growth & Polish
- "Remix Variants" on share pages
- Character-driven auto-share prompts after creation
- Admin dashboard WebSocket upgrade
- Style preset preview thumbnails
- "Story Chain" leaderboard

---

## Key Files
- `/app/backend/services/retention_service.py` — Retention service (notifications, email, challenges, stats)
- `/app/backend/routes/retention_hooks.py` — Retention API routes
- `/app/backend/routes/story_engine_routes.py` — Job APIs + view_mode routing + remix notification trigger
- `/app/frontend/src/components/NotificationBell.js` — Bell with retention notification types
- `/app/frontend/src/components/GlobalUserBar.jsx` — Top nav with bell integration
- `/app/frontend/src/pages/StoryVideoPipeline.js` — Studio + recovery routing
- `/app/frontend/src/pages/MySpacePage.js` — Dashboard + ownership messaging
- `/app/frontend/src/pages/Dashboard.js` — Daily Challenge banner + Top Stories leaderboard

## Email System Status
- **Current**: MOCKED — emails are logged to `email_events` collection, not sent
- **Recommended next step**: Wire Resend for real delivery
- **Admin preview**: `GET /api/retention/email-events` (admin-only)
