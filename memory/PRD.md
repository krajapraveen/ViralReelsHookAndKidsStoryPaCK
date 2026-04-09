# Visionary Suite - Product Requirements Document

## Original Problem Statement
Build an AI Creator Suite with a compulsion-driven "Growth Engine" — a full-stack application featuring AI video generation, social sharing loops, and monetization via credits and payments. The platform must create irresistible user journeys from discovery to creation and sharing, with a retention layer that pulls users back daily.

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

### P0 Growth Loop (Compulsion Engine) — DONE
- Redesigned public pages, 1-click continue, open-loop endings, enhanced social proof

### P1 Monetization — DONE
- Cashfree payments, strict credit checks, 50-credit standard

### MySpace UX Overhaul — DONE
- Plain-English copy, fuzzy time estimates, skeleton loading

### Pipeline Resilience — DONE
- Graceful degradation with character fallbacks

### Remix Gallery + Addiction Layer — DONE
- Anonymous opt-in, trending badges, 1-click variants, session streaks

### P0 Failed Job Recovery Routing — DONE (Apr 9, 2026)
- Server-authoritative `view_mode` routing, FailedRecoveryScreen, deep-link support
- Testing: 17/18 passed (iteration_470)

### Retention Layer — Release 1 — DONE (Apr 9, 2026)
- In-App Notification System with bell, aggregated/throttled notifications
- Ownership Messaging ("X people remixed your story")
- Daily Challenge System with admin-configurable challenges
- Soft Leaderboard (Top Stories Today)
- Mock Email Service with admin preview
- Testing: 25/25 passed (iteration_471)

### Retention Layer — Release 2 — DONE (Apr 9, 2026)
- **Real Resend Email**: Wired Resend for comeback emails with per-user caps (max 2 remix/day, max 1 trending/12h, max 1 challenge/day). Domain verification required for full delivery.
- **Auto-play Hover Preview**: RemixGallery cards auto-play muted video on hover (900ms delay). Global singleton controller ensures only one preview plays at a time.
- **Challenge Participation Tracking**: `challenge_id` + `challenge_joined_at` stored in job documents. Studio shows "Challenge Entry" banner. MySpace shows challenge badge.
- **Challenge Leaderboard**: Weighted scoring (remix_count * 0.6 + views * 0.4). Challenge endpoint returns leaderboard entries.
- **Unsubscribe-ready metadata**: Each email event includes `email_type` and `user_preferences_key` for future compliance.
- Testing: 24/24 passed (iteration_472)

---

## Email System Status
- **Provider**: Resend (wired)
- **API Key**: Configured in .env as RESEND_API_KEY
- **Status**: Infrastructure working. Domain verification required for sending to non-owner emails.
- **Admin preview**: `GET /api/retention/email-events`
- **Safety**: Per-user caps, cooldown periods, unsubscribe metadata structure

---

## Prioritized Backlog

### P1 — Quality & Transparency
- "Improve consistency" CTA on completed cards
- Quality transparency note for character fallback
- Smarter retry logic (simplify prompt on retry)
- A/B test hook text variations on public pages

### P2 — Growth & Polish
- Resend domain verification for live email delivery
- Challenge Leaderboard on homepage (featured winner)
- "Remix Variants" on share pages
- Admin dashboard WebSocket upgrade
- Style preset preview thumbnails
- "Story Chain" leaderboard

---

## Key Files
- `/app/backend/services/retention_service.py` — Retention service (Resend email, notifications, challenges, stats)
- `/app/backend/routes/retention_hooks.py` — Retention API routes
- `/app/backend/routes/story_engine_routes.py` — Job APIs + view_mode + remix triggers + challenge tracking
- `/app/frontend/src/components/NotificationBell.js` — Bell with retention types
- `/app/frontend/src/components/RemixGallery.js` — Gallery with auto-play hover preview
- `/app/frontend/src/components/GlobalUserBar.jsx` — Top nav with bell
- `/app/frontend/src/pages/StoryVideoPipeline.js` — Studio + recovery + challenge banner
- `/app/frontend/src/pages/MySpacePage.js` — Dashboard + ownership + challenge badges
- `/app/frontend/src/pages/Dashboard.js` — Challenge banner + Top Stories leaderboard
