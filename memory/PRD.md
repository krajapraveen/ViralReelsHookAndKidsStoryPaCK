# Visionary Suite - Product Requirements Document

## Original Problem Statement
Build an AI Creator Suite with a compulsion-driven "Growth Engine" — a full-stack application featuring AI video generation, social sharing loops, and monetization via credits and payments. The platform must create irresistible user journeys with a multi-day retention engine that pulls creators back through notifications, email, challenges, and social proof.

## Architecture
- **Frontend**: React (CRA) + TailwindCSS + Shadcn/UI
- **Backend**: FastAPI + MongoDB + Redis
- **Integrations**: OpenAI (GPT-4o-mini, GPT Image 1, Sora 2, TTS), Gemini, Cloudflare R2, Cashfree, Google Auth, Resend (email)
- **Key URL**: https://trust-engine-5.preview.emergentagent.com

## Credentials
- Test: test@visionary-suite.com / Test@2026#
- Admin: admin@creatorstudio.ai / Cr3@t0rStud!o#2026

---

## What's Been Implemented

### Core Platform — DONE
- P0 Growth Loop, P1 Monetization, MySpace UX, Pipeline Resilience, Remix Gallery, Addiction Layer, Trust Fixes

### P0 Failed Job Recovery — DONE (Apr 9)
- Server-authoritative view_mode routing, FailedRecoveryScreen, deep-link support
- Testing: 17/18 (iteration_470)

### Retention Layer — Release 1 — DONE (Apr 9)
- In-App Notifications (bell, throttled, aggregated), Ownership Messaging, Daily Challenges, Soft Leaderboard, Mock Email
- Testing: 25/25 (iteration_471)

### Retention Layer — Release 2 — DONE (Apr 9)
- Real Resend email, auto-play hover preview, challenge participation tracking, challenge leaderboard, challenge badges
- Testing: 24/24 (iteration_472)

### Creator Digest — DONE (Apr 9)
- **Weekly digest** computing per-user stats: total views, new remixes, top story highlight, momentum signal, percentile comparison, Rising Fast badge
- **Smart skip**: No digest for zero-activity users or guest accounts
- **Personalized CTA**: Dynamic based on user's top metric (remixes → "See who remixed", views → "See why trending")
- **Per-user weekly cap**: Max 1 digest/week
- **Admin controls**: Preview digest for any user, send to specific user, run-all weekly digest
- **Email template**: Clean dark theme, 20-second read, stats + top story + momentum + CTA
- **User lookup fix**: Searches by `id` field (matching users collection schema)
- Testing: 14/14 (iteration_473)

---

## Email System Status
- **Provider**: Resend (wired, API key configured)
- **Status**: Infrastructure complete. Domain verification needed for non-owner delivery.
- **Templates**: story_remixed, story_trending, daily_challenge_live, ownership_milestone, creator_digest
- **Safety**: Per-user caps, cooldowns, weekly digest cap, unsubscribe metadata
- **Admin**: Preview at GET /api/retention/email-events

---

## Prioritized Backlog

### P0 — Immediate
- Verify Resend domain for live email delivery (user action)

### P1 — Next Features
- Homepage featured challenge winner hero slot
- "Improve consistency" CTA on completed cards
- A/B test hook text variations

### P2 — Growth & Polish
- Monthly creator milestone digest
- "Remix Variants" on share pages
- Admin WebSocket upgrade
- Story Chain leaderboard

---

## Key Files
- `/app/backend/services/retention_service.py` — Full retention service (email, notifications, challenges, digest)
- `/app/backend/routes/retention_hooks.py` — Retention API routes (challenges, digest, email preview)
- `/app/backend/routes/story_engine_routes.py` — Job APIs + view_mode + remix triggers
- `/app/frontend/src/components/NotificationBell.js` — Bell with retention types
- `/app/frontend/src/components/RemixGallery.js` — Gallery with auto-play hover preview
- `/app/frontend/src/components/GlobalUserBar.jsx` — Top nav with bell
- `/app/frontend/src/pages/StoryVideoPipeline.js` — Studio + recovery + challenge
- `/app/frontend/src/pages/MySpacePage.js` — Dashboard + ownership + challenge badges
- `/app/frontend/src/pages/Dashboard.js` — Challenge banner + Top Stories leaderboard
