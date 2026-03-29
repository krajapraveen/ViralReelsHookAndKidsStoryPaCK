# Story Universe Engine — Product Requirements Document

## Original Problem Statement
Build a "Story Universe Engine" — a full-stack AI creator suite with 11 creator tools, growth/engagement engine, monetization via Cashfree payments, and a viral sharing loop.

## Core Architecture
- **Frontend**: React (CRA + Craco) on port 3000
- **Backend**: FastAPI on port 8001
- **Database**: MongoDB (no migrations — compatibility layer only)
- **Storage**: Cloudflare R2 (CDN for images, proxy for video)
- **Payments**: Cashfree
- **AI**: OpenAI GPT-4o-mini, Sora 2, TTS + Gemini 3 via Emergent LLM Key

## Key Design Principles
1. **NO DB MIGRATIONS** — use API-level compatibility mapping
2. **Explicit consent** — no auto-generation, user must click Generate
3. **R2 CDN for images** — backend proxy only for video chunked streaming
4. **Trust-first** — no synthetic/mocked data in user-facing UI
5. **Centralized Credits Service** — all credit ops go through CreditsService
6. **Continue Loop** — every story must drive continuation
7. **Track behavior, not traffic** — only loop events matter

## Addiction Loop Metrics Dashboard
### What's implemented
- **Endpoint**: `GET /api/growth/loop-dashboard?days=7|14|30`
- **5 Core Metrics**: Click Rate, Completion Rate, Continue Rate (NORTH STAR), Share Rate, K-Factor
- **7 Dashboard Sections**:
  1. Growth Loop Health (top bar with benchmarks)
  2. Funnel (impression → click → watch → complete → continue → share)
  3. Drop-off Analysis (with worst drop-off highlighted)
  4. Top Performing Stories (continue%, share%, completions)
  5. Hook A/B Performance (CTR, continue% per variant)
  6. Category Performance (continue%, share% per category)
  7. Real-Time Activity Feed (last 20 events)
- **Frontend Tracking**: `growthTracker.js` — batched event queue (3s flush / 10 events)
- **Events Tracked**: impression (IntersectionObserver on cards), click (card click), watch_start (video play), watch_complete (video end), continue (continue CTA), share (share button)
- **Pages Instrumented**: Dashboard.js, PublicCreation.js, StoryPreview.js

## Continue Story Loop (Growth Engine)
1. Post-Video Auto Continue Overlay (StoryPreview + PublicCreation)
2. CTA Hierarchy — Continue is PRIMARY everywhere
3. Studio Prefill — title, story_text, animation_style, parent_video_id, hook_text, characters
4. Cliffhanger Enforcement (Backend) — planning_llm.py validates and rewrites weak cliffhangers
5. Share Page = Continue Trigger

## Credits Service Architecture
- **File**: `/app/backend/services/credits_service.py`
- **Class**: `CreditsService` with `get_user_credit_state`, `check_credits`, `deduct_credits`, `refund_credits`, `award_credits`
- **Phase 1 DONE**: Story Engine, video routes, bedtime builder, coloring book, + shared.py delegation
- **Phase 2/3 PENDING**: ~35 low-risk routes

## Canonical Reference Documents
- `/app/ARCHITECTURE.md` — Technical architecture
- `/app/DB_RELATIONSHIPS.md` — MongoDB collection relationships
- `/app/BACKEND_SERVICE_MAP.md` — Backend service/pipeline map

## What's Been Implemented
- Story Universe Engine with 11 creator tools
- Homepage with 4 story rows + hero
- Story-to-Video pipeline
- Media optimization (R2 CDN)
- Compatibility layer
- Cashfree payments + Google Auth
- Admin dashboard (truth-based)
- Credit system centralized
- Character routes fixed to character_profiles
- Continue Story Loop Optimization
- **Addiction Loop Metrics Dashboard** — all 7 sections
- **Frontend event tracking** — impression, click, watch, continue, share
- **Netflix-style Dashboard UI** — 9 sections: Hero (72vh, auto-rotate, video/poster/gradient fallback), Metrics Strip, 4 Story Rows (Trending/Fresh/Continue/Unfinished), Creator Tools grid, Activity Bar, Footer
- **Dashboard media resilience** — Hero never shows black void (gradient fallback on poster/video failure), SafeImage gradient fallback on card thumbnail failure, removed invalid preload warning
- **Mobile-first Dashboard** — 60vh mobile hero with full-width CTA, 160x220 mobile cards (220x300 desktop), horizontal scroll metrics pills, 2-col feature grid (10 tools), sticky bottom nav (Home/Explore/Create/Stories/Profile)
- **First 1-second perception optimization** — blur-to-video hero swap, shimmer loading (no spinners), progressive IntersectionObserver row reveal, requestIdleCallback thumbnail preloading, CTA glow pulse, card float micro-animations, real-time activity signals, zero dead states

## Deployment Status
- Deployment health check: PASSED (Mar 2026)

## Prioritized Backlog
### P1
- Soft Launch monitoring using the new dashboard

### P2
- Migrate remaining ~35 routes to CreditsService
- A/B test hook text variations
- Character-driven auto-share prompts
- Remix Variants on share pages
- Self-hosted GPU models (Wan2.1, Kokoro)

### P3
- WebSockets for live admin job tracking

## Test Credentials
- Test User: test@visionary-suite.com / Test@2026#
- Admin User: admin@creatorstudio.ai / Cr3@t0rStud!o#2026
