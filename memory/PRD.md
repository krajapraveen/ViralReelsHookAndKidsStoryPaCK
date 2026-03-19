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

### Phase 2: Growth Engine (Complete)
- Auto-character extraction, sharing loop, rewards
- Growth event tracking (7 core events)
- Truth-based Admin Dashboard

### Phase 3: Compulsion Engine (Complete — Mar 19, 2026)
- Shared Page Redesign with character-driven hooks, momentum CTAs
- 1-Click Continue Flow (no login wall before generate)
- Open-Loop Story Endings (backend enforcement)

### Phase 4: Monetization Discipline (Complete — Mar 19, 2026)
- Cashfree Production Verified
- Credit Enforcement on all generation tools
- Admin Dashboard — Revenue/Credits/Conversion sections

### Phase 5: Enhanced Social Proof (Complete — Mar 19, 2026)
- Momentum-based messaging (not vanity metrics)
- Character Power Score
- CTAs: "Continue where others left off"
- Trending badge (real thresholds only)
- Time-based decay

### Phase 6: Credit Consistency Fix (Complete — Mar 19, 2026)
**Root cause found and eliminated:**
- `server.py` had auto-top-up code that reset ALL users to 100 credits on EVERY server restart — REMOVED
- Multiple frontend pages showed "100 free credits" text — ALL fixed to 50
- `monetization.py` free tier showed 10 credits — fixed to 50
- Signup flow (email + Google OAuth) set 0 credits — fixed to 50
- AdminUsersManagement defaults were 100 — fixed to 50
- `server_modular.py` and `server_monolith_backup.py` had 100 credit grants — fixed

**What was done:**
1. Removed `server.py` auto-top-up that overrode every credit reset on restart
2. Fixed ALL UI text references (Landing, Pricing, Signup, TermsOfService, Reviews, DemoReelGenerator, HelpGuide, AppTour, AdminUsersManagement)
3. Fixed backend config (monetization.py free tier: 10→50)
4. Fixed signup flows (email + Google OAuth: 0→50 credits)
5. Re-executed credit reset: 27 normal users at exactly 50 credits
6. Verified: 0 normal users with >50 credits
7. Verified: No auto-grant on server restart
8. Added demo@ to exclusion list in credit reset

**Single Source of Truth:**
- Credits come ONLY from: (a) signup bonus (50), (b) Cashfree payment, (c) admin credit reset
- No frontend defaults, no cached placeholders, no hardcoded values
- New user default = 50 credits (signup flow)

## Key Credentials
- Test User: test@visionary-suite.com / Test@2026# (excluded from reset, has 999K credits)
- Admin User: admin@creatorstudio.ai / Cr3@t0rStud!o#2026

## Prioritized Backlog
### P1 (Next)
- A/B test hook text variations on public pages
- Character-driven auto-share prompts after creation

### P2
- Remix Variants on share pages
- WebSocket live updates for Admin funnel
- Style preset preview thumbnails
- General UI polish
