# Visionary Suite — PRD

## Original Problem Statement
AI Creator Suite ("Visionary Suite") — a comprehensive platform for AI-powered content creation including story videos, comics, GIFs, thumbnails, and more. The platform has pivoted through multiple phases: pricing engine → AI Character Memory → Growth Engine → Monetization Discipline.

## Core Architecture
- **Frontend**: React + Shadcn/UI + Tailwind CSS
- **Backend**: FastAPI + MongoDB + Redis
- **Integrations**: OpenAI (GPT-4o-mini, GPT Image 1, Sora 2, TTS), Gemini, Google Auth (Emergent-managed), Cloudflare R2 (Object Storage), Cashfree (Payments)
- **Analytics**: Growth event tracking spine → Admin dashboard

## What's Been Implemented

### Phase 1: Core Platform (Complete)
- Full AI creator suite (story video, comic, GIF, thumbnail, etc.)
- User auth (JWT + Google OAuth)
- Pricing system with Cashfree payments
- AI Character Memory system

### Phase 2: Growth Engine (Complete — Mar 2026)
- Auto-character extraction from stories
- Basic sharing loop
- Series completion rewards
- Growth event tracking (7 core events)
- Truth-based Admin Dashboard (5 sections)

### Phase 3: Compulsion Engine (Complete — Mar 19, 2026)
- **Shared Page Redesign**: PublicCharacterPage & PublicCreation redesigned with:
  - Character-driven hero with social proof
  - Dual CTAs: "Continue This Story" + "Create Your Own Version"
  - Cliffhanger teasers to create curiosity
  - No login wall on public pages
- **1-Click Continue Flow**: StoryVideoStudio route opened to unauthenticated users. Auth check happens ONLY at "Generate" step (not page load). remix_data pipeline pre-fills the studio.
- **Open-Loop Story Endings**: Backend prompts (story_video_studio.py + story_series.py) modified to enforce cliffhanger/open-loop endings on every story.
- **401 Interceptor Fix**: api.js updated to whitelist open-access paths from redirect.

### Phase 4: Monetization Discipline (Complete — Mar 19, 2026)
- **Cashfree Production Verification**: Confirmed production mode, webhook signature verification, idempotency, replay protection.
- **Credit Enforcement**: story_video_studio.py now requires auth + deducts credits before generation. All generation tools enforce credits.
- **Credit Reset**: Admin endpoint `/api/admin/metrics/credit-reset` — 29 normal users reset to 50 credits. Admin/test/uat/dev excluded. Audit logged.
- **Credit Banner**: `show_credit_banner` flag on user model. Auto-shown via CreditContext toast, auto-dismissed via `/api/auth/dismiss-credit-banner`.
- **Admin Dashboard — Revenue**: Real Cashfree data (total_revenue_inr, successful/failed payments, ARPU, recent payments).
- **Admin Dashboard — Credits**: Credits issued/consumed, avg per user, top users by usage, Credit Reset widget.
- **Admin Dashboard — Conversion**: Free→paid rate, top-up rate, subscription rate, repeat buyers.

## Prioritized Backlog

### P1 (Next)
- A/B test hook text variations on public pages
- Character-driven auto-share prompts after creation
- Enhance social proof counters (real-time usage tracking)

### P2
- Remix Variants on share pages
- WebSocket live updates for Admin funnel
- Style preset preview thumbnails
- General UI polish
- Fix minor lint errors in comic_storybook.py and gif_maker.py

## Key Credentials
- Test User: test@visionary-suite.com / Test@2026#
- Admin User: admin@creatorstudio.ai / Cr3@t0rStud!o#2026

## Critical Technical Notes
- Cashfree is PRODUCTION mode (hardcoded, never sandbox)
- Credits are deducted BEFORE generation, refunded on failure
- Story generation prompts enforce open-loop/cliffhanger endings
- StoryVideoStudio is open-access (auth at generate step only)
- 401 interceptor whitelists: /app/story-video-studio, /app/story-preview, /v/, /character/
