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
- Basic sharing loop + series completion rewards
- Growth event tracking (7 core events)
- Truth-based Admin Dashboard (5 sections)

### Phase 3: Compulsion Engine (Complete — Mar 19, 2026)
- **Shared Page Redesign**: PublicCharacterPage & PublicCreation with character-driven hooks, dual CTAs, cliffhanger teasers, no login wall
- **1-Click Continue Flow**: StoryVideoStudio open to unauthenticated users. Auth check at "Generate" step only. remix_data pre-fills studio
- **Open-Loop Story Endings**: Backend prompts enforce cliffhanger/open-loop endings

### Phase 4: Monetization Discipline (Complete — Mar 19, 2026)
- **Cashfree Production Verified**: Production mode, webhook sig verification, idempotency, replay protection
- **Credit Enforcement**: All tools require auth + credit deduction before generation. Refund on failure
- **Credit Reset Executed**: 29 normal users reset to 50 credits. Admin/test/uat/dev excluded. Audit logged
- **Credit Banner**: show_credit_banner flag, auto-toast on login, auto-dismiss endpoint
- **Admin Dashboard — Revenue/Credits/Conversion**: 3 new sections with real Cashfree data

### Phase 5: Enhanced Social Proof (Complete — Mar 19, 2026)
- **Momentum-Based Social Proof**: Not vanity metrics. Real data:
  - Total continuations, total stories per character, last continuation timestamp
  - Continuations in last 1h/24h for freshness
  - "Last continued X minutes ago" — urgency signal
  - "Story is still evolving" (green) vs "Be the first to continue today" (amber) — time-based decay
- **Character Power Score**: "Used in X stories, Y continuations, Z tools"
- **CTAs Updated**: "Create your own" → "Continue where others left off" (with social count)
- **Trending Badge**: Real thresholds only (continuations_1h >= 2 OR continuations_24h >= 5 + views >= 20). No fake trending
- **Time-Based Decay**: If no activity in 24h → "Be the first to continue today"

## Prioritized Backlog

### P1 (Next)
- A/B test hook text variations on public pages
- Character-driven auto-share prompts after creation
- "Story is alive" messaging variations

### P2
- Remix Variants on share pages
- WebSocket live updates for Admin funnel
- Style preset preview thumbnails
- General UI polish

## Key Credentials
- Test User: test@visionary-suite.com / Test@2026#
- Admin User: admin@creatorstudio.ai / Cr3@t0rStud!o#2026

## Critical Technical Notes
- Cashfree is PRODUCTION mode (hardcoded, never sandbox)
- Credits deducted BEFORE generation, refunded on failure
- Story prompts enforce open-loop/cliffhanger endings
- StoryVideoStudio is open-access (auth at generate step only)
- 401 interceptor whitelists: /app/story-video-studio, /v/, /character/
- Social proof uses real momentum data only — no fake trending, no vanity counters
- is_alive returns proper boolean (fixed by testing agent)
