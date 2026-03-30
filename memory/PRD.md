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
8. **POSTER-FIRST HOMEPAGE** — no autoplay video on homepage; video belongs on watch/result/share pages only

## Homepage Media Architecture (POSTER-FIRST — Mar 2026)
### Mandatory Rules
- **Homepage = posters only.** No `<video>` elements on Dashboard.js.
- **Watch/result/share pages = real video.** All video playback complexity lives deeper in the flow.
- **Motion on homepage = CSS only.** Ken Burns zoom, light sweep shimmer, badge pulse, hover scale — no browser video dependencies.

### Why
Autoplay video on homepage causes: Safari failures, mobile failures, slow paint, black/blank states, codec/CORS issues, battery/network problems. The homepage is for attraction, speed, click-through — not video playback.

### Implementation
- **Hero**: Poster image + Ken Burns slow zoom (8s cycle) + light sweep shimmer overlay + gradient fallback
- **Story Cards**: Poster thumbnail + badge pulse + hover scale(1.05) + card light sweep on hover + play button overlay
- **No video, mute, autoplay, playsInline, crossOrigin on any homepage element**
- **Click → navigate to studio** where real video plays

## Media Proxy Architecture (Mar 2026)
- All R2 CDN URLs routed through `/api/media/r2/{path}` for CORS/Safari/mobile compatibility
- `asyncio.to_thread()` for all boto3 S3 calls — prevents event loop blocking
- In-memory LRU cache (150 entries, 1hr TTL) for resized images
- Auto-resize images >300KB to 800px even without `?w` parameter
- `?w=400&q=80` for card thumbnails, `?w=800` for hero poster
- 5 concurrent images: 0.33s (was 9.7s/each before fix)

## Addiction Loop Metrics Dashboard
- **Endpoint**: `GET /api/growth/loop-dashboard?days=7|14|30`
- **5 Core Metrics**: Click Rate, Completion Rate, Continue Rate (NORTH STAR), Share Rate, K-Factor
- **Frontend Tracking**: `growthTracker.js` — batched event queue (3s flush / 10 events)

## Credits Service Architecture
- **File**: `/app/backend/services/credits_service.py`
- **Phase 1 DONE**: Story Engine, video routes, bedtime builder, coloring book, + shared.py delegation
- **Phase 2/3 PENDING**: ~35 low-risk routes — **USER PAUSED**

## What's Been Implemented
- Story Universe Engine with 11 creator tools
- Homepage with 4 story rows + hero (poster-first)
- Story-to-Video pipeline
- Media optimization (R2 CDN + async proxy + LRU cache)
- Compatibility layer
- Cashfree payments + Google Auth
- Admin dashboard (truth-based)
- Credit system centralized (50 credits for new users)
- Character routes fixed to character_profiles
- Continue Story Loop Optimization
- Addiction Loop Metrics Dashboard — all 7 sections
- Frontend event tracking — impression, click, watch, continue, share
- Netflix-style Dashboard UI — poster-first, CSS-only motion
- Mobile-first Dashboard — 60vh mobile hero, 160x220 mobile cards
- 1-second perception optimization — shimmer loading, progressive IntersectionObserver
- Addiction Triggers in Video Generation (watch/result pages)
- Cross-Browser Media Fix (media proxy for CORS/Safari)
- **Poster-First Homepage Architecture (Mar 30 2026)** — ZERO video on homepage, Ken Burns + light sweep + badge pulse + hover scale
- **Media Proxy Concurrent Fix (Mar 30 2026)** — asyncio.to_thread, LRU cache, auto-resize

## Prioritized Backlog
### P1
- Soft Launch monitoring using the new dashboard

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
