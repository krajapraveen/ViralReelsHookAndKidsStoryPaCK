# Story Universe Engine — Product Requirements Document

## Original Problem Statement
Build a "Story Universe Engine" — a full-stack AI creator suite with 11 creator tools, growth/engagement engine, monetization via Cashfree payments, and a viral sharing loop.

## Core Architecture
- **Frontend**: React (CRA + Craco) on port 3000
- **Backend**: FastAPI on port 8001
- **Database**: MongoDB (no migrations — compatibility layer only)
- **Storage**: Cloudflare R2 (for story detail/watch/result pages only)
- **Payments**: Cashfree
- **AI**: OpenAI GPT-4o-mini, Sora 2, TTS + Gemini 3 via Emergent LLM Key

## Homepage Media Architecture (STATIC SAME-ORIGIN — Mar 30 2026)

### Mandatory Rule
**Homepage = same-origin static media. ZERO CDN/R2/proxy dependency.**

### Implementation
- **17 curated banners** in `/public/homepage-banners/` (compressed JPEG, 8-126KB each)
- **Hero images**: 800px wide, ~30KB each
- **Card images**: 400px wide, ~15KB each
- **Data module**: `/src/data/staticBanners.js` — maps job_id → static image paths
- **Dashboard.js** uses `getStaticHeroImg(jobId)` and `getStaticCardImg(jobId)` — plain `<img>` tags, no SafeImage, no mediaUrl, no CORS
- **Feed API** still provides row organization (trending, continue, fresh, unfinished) — images resolved from static lookup

### What's NOT on the homepage
- No `<video>` elements
- No R2 CDN URLs
- No `/api/media/r2/` proxy calls
- No `crossOrigin` attributes
- No SafeImage component
- No mediaUrl function

### Where dynamic media IS used
- Story detail page
- Watch/result page
- Share page
- Story Video Studio

### Why
Autoplay video + R2 CDN proxy was unreliable across Safari, mobile Chrome, mobile Safari. The homepage's job is: load fast, look alive, get clicks. It doesn't need to prove dynamic media infrastructure on first render.

## Key Design Principles
1. **NO DB MIGRATIONS** — use API-level compatibility mapping
2. **Explicit consent** — no auto-generation, user must click Generate
3. **Trust-first** — no synthetic/mocked data in user-facing UI
4. **Centralized Credits Service** — all credit ops go through CreditsService
5. **Continue Loop** — every story must drive continuation
6. **Homepage = static, deeper pages = dynamic** — media reliability architecture

## Credits Service Architecture
- **File**: `/app/backend/services/credits_service.py`
- **Phase 1 DONE**: Story Engine, video routes, bedtime builder, coloring book, + shared.py delegation
- **Phase 2/3 PENDING**: ~35 low-risk routes — **USER PAUSED**

## What's Been Implemented
- Story Universe Engine with 11 creator tools
- **Static same-origin homepage** with 4 story rows + hero (17 curated banners)
- Story-to-Video pipeline with addiction triggers
- Media proxy (asyncio.to_thread + LRU cache) for deeper pages
- Compatibility layer
- Cashfree payments + Google Auth
- Admin dashboard (truth-based)
- Credit system (50 credits for new users)
- Continue Story Loop Optimization
- Addiction Loop Metrics Dashboard
- Frontend event tracking (impression, click, watch, continue, share)
- Netflix-style Dashboard UI — poster-first, CSS-only motion (Ken Burns, light sweep, badge pulse)
- Mobile-first Dashboard (60vh mobile hero, 160x220 mobile cards)
- 1-second perception optimization (shimmer, progressive IntersectionObserver)
- GitHub Actions workflows fixed (manual-only triggers, CJS config)

## Prioritized Backlog
### P1
- Soft Launch monitoring

### P2 (User-paused)
- Migrate remaining ~35 routes to CreditsService
- A/B test hook text variations
- Character-driven auto-share prompts
- Remix Variants on share pages

### P3
- Self-hosted GPU models (Wan2.1, Kokoro)
- WebSockets for live admin job tracking

## Test Credentials
- Test User: test@visionary-suite.com / Test@2026#
- Admin User: admin@creatorstudio.ai / Cr3@t0rStud!o#2026
