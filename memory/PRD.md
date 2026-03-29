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
5. **50 credits** standard for new normal users
6. **Centralized Credits Service** — all credit ops go through CreditsService

## Credits Service Architecture
- **File**: `/app/backend/services/credits_service.py`
- **Class**: `CreditsService` with `get_user_credit_state`, `check_credits`, `deduct_credits`, `refund_credits`, `award_credits`
- **Exception**: `InsufficientCreditsError` raised on insufficient balance
- **Atomic**: Uses `find_one_and_update` with `$gte` condition
- **Ledger**: Logs to `credit_ledger` collection
- **Unlimited**: Admin/dev/qa/test roles and `is_unlimited=true` users skip deduction
- **Phase 1 DONE**: Story Engine, story_video_generation, bedtime_story_builder, story_video_fast, coloring_book_v2, story_video_studio, + 10 routes via shared.py delegation
- **Phase 2/3 PENDING**: ~35 low-risk routes still use direct `$inc`

## Canonical Reference Documents
- `/app/ARCHITECTURE.md` — Technical architecture
- `/app/DB_RELATIONSHIPS.md` — MongoDB collection relationships
- `/app/BACKEND_SERVICE_MAP.md` — Backend service/pipeline map (10 services, strict layering)

## What's Been Implemented
- Story Universe Engine with 11 creator tools
- Homepage: Hero + 4 story rows (Trending, Fresh, Continue, Unfinished Worlds)
- Story card → Studio prefill (no auto-start)
- Story-to-Video pipeline with FFmpeg xfade fixes
- Blazing fast media loading (R2 CDN for images, lazy loading via IntersectionObserver)
- Compatibility layer mapping flat DB → nested API contracts
- API contract alignment (id, thumbnail_small_url, character_summary, /api/credits/me, source_surface, hook_text)
- Cashfree payment integration
- Google Auth (Emergent-managed)
- Admin dashboard with truth-based metrics
- Credit system centralized via CreditsService
- Character routes fixed to use `character_profiles` collection
- Growth/viral loop with momentum-based social proof
- Deployment health check PASSED

## Deployment Status
- **Deployment health check: PASSED** (Mar 2026)
- All deployer checks clean
- Ready for production deployment

## Prioritized Backlog

### P1
- Soft Launch monitoring (Click→Generate, Generate→Watch, Watch→Continue, Share→Signup)

### P2
- Migrate remaining ~35 routes to CreditsService (Phase 2/3)
- A/B test hook text variations on story cards
- Character-driven auto-share prompts after creation
- Remix Variants on share pages
- Self-hosted GPU models (Wan2.1, Kokoro) to replace APIs

### P3
- WebSockets for live admin job tracking

## Test Credentials
- Test User: test@visionary-suite.com / Test@2026#
- Admin User: admin@creatorstudio.ai / Cr3@t0rStud!o#2026
