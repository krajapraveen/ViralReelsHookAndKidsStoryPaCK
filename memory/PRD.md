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
7. **Continue Loop** — every story must drive continuation

## Continue Story Loop (Growth Engine)
### What's implemented
1. **Post-Video Auto Continue Overlay** (StoryPreview.js + PublicCreation.js)
   - Triggers on video end / last scene reached
   - Shows actual cliffhanger text from the story
   - "This wasn't the end..." + cliffhanger + "What happens next?"
   - Primary CTA: "Continue This Story"

2. **CTA Hierarchy** — Continue is PRIMARY everywhere
   - StoryPreview header: "What Happens Next?" (gradient, bold)
   - StoryPreview banner: Cliffhanger text + Continue CTA
   - StoryPreview sidebar: Continue section ABOVE downloads
   - Export/Download demoted to secondary

3. **Studio Prefill on Continue** — Full context pass
   - title, story_text, animation_style, parent_video_id
   - hook_text (cliffhanger)
   - characters (from continuity)
   - Via both location.state.prefill AND localStorage remix_data

4. **Cliffhanger Enforcement (Backend)**
   - planning_llm.py validates cliffhanger after generation
   - If < 15 chars or missing → LLM rewrite with dedicated prompt
   - Fallback: "But what they found next changed everything..."

5. **Share Page = Continue Trigger**
   - PublicCreation overlay shows cliffhanger text
   - All CTAs drive toward "Continue This Story"

## Credits Service Architecture
- **File**: `/app/backend/services/credits_service.py`
- **Class**: `CreditsService` with `get_user_credit_state`, `check_credits`, `deduct_credits`, `refund_credits`, `award_credits`
- **Exception**: `InsufficientCreditsError`
- **Phase 1 DONE**: Story Engine, video routes, bedtime builder, coloring book, + shared.py delegation
- **Phase 2/3 PENDING**: ~35 low-risk routes

## Canonical Reference Documents
- `/app/ARCHITECTURE.md` — Technical architecture
- `/app/DB_RELATIONSHIPS.md` — MongoDB collection relationships
- `/app/BACKEND_SERVICE_MAP.md` — Backend service/pipeline map

## What's Been Implemented
- Story Universe Engine with 11 creator tools
- Homepage: Hero + 4 story rows (Trending, Fresh, Continue, Unfinished Worlds)
- Story card → Studio prefill (no auto-start)
- Story-to-Video pipeline with FFmpeg xfade fixes
- Blazing fast media loading (R2 CDN for images, lazy loading)
- Compatibility layer mapping flat DB → nested API contracts
- Cashfree payment integration
- Google Auth (Emergent-managed)
- Admin dashboard with truth-based metrics
- Credit system centralized via CreditsService
- Character routes fixed to use `character_profiles` collection
- Growth/viral loop with momentum-based social proof
- **Continue Story Loop Optimization** — complete
- Deployment health check PASSED

## Deployment Status
- **Deployment health check: PASSED** (Mar 2026)
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
