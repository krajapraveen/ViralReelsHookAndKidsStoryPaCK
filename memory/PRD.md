# Story Universe Engine — Product Requirements Document

## Original Problem Statement
Build a "Story Universe Engine" — a full-stack AI creator suite with 11 creator tools, growth/engagement engine, monetization via Cashfree payments, and a viral sharing loop.

## Core Architecture
- **Frontend**: React (CRA + Craco) on port 3000
- **Backend**: FastAPI on port 8001
- **Database**: MongoDB
- **Storage**: Cloudflare R2 (for story detail/watch/result pages only — NOT homepage)
- **Payments**: Cashfree
- **AI**: OpenAI GPT-4o-mini, Sora 2, TTS + Gemini 3 via Emergent LLM Key

## Homepage Media Architecture (WEBPACK-BUNDLED — Mar 30 2026)

### Hard Rule
**Homepage images = webpack-bundled local assets. ZERO network dependency.**

### How it works
- 28 JPEG files in `frontend/src/assets/homepage/` (14 hero + 14 card)
- Imported via `import heroImg from '../assets/homepage/hero.jpg'` in `staticBanners.js`
- Webpack hashes and bundles them → served as `/static/media/*.contenthash.jpg`
- Dashboard.js uses `getStaticHeroImg(jobId)` / `getStaticCardImg(jobId)` — returns webpack-hashed URLs
- Plain `<img>` tags, no SafeImage, no mediaUrl, no CORS, no crossOrigin

### What's NOT on the homepage
- No R2 CDN URLs
- No `/api/media/r2/` proxy calls
- No `/public/` static file serving
- No `<video>` elements
- No remote/dynamic/generated media
- No SafeImage component

### Where dynamic media IS used
- Story detail page, Watch/result page, Share page, Story Video Studio

## Key Design Principles
1. Homepage = bundled, deeper pages = dynamic
2. Trust-first — no synthetic/mocked data
3. No DB migrations — API-level compatibility
4. Continue Loop — every story drives continuation
5. Centralized Credits Service

## Credits Service
- Phase 1 DONE: Story Engine, video routes, bedtime builder, coloring book
- Phase 2/3 PENDING (~35 routes) — **USER PAUSED**

## What's Been Implemented
- Story Universe Engine with 11 creator tools
- **Webpack-bundled homepage** with 4 story rows + hero (17 stories, 28 images)
- Story-to-Video pipeline with addiction triggers
- Media proxy (asyncio.to_thread + LRU cache) for deeper pages
- Cashfree payments + Google Auth
- Admin dashboard (truth-based, 50 credits for new users)
- Addiction Loop Metrics Dashboard + Frontend event tracking
- Netflix-style UI — poster-first, CSS-only motion (Ken Burns, light sweep, badge pulse)
- Mobile-first (60vh hero, 160x220 cards)
- GitHub Actions workflows fixed (manual-only triggers)

## Prioritized Backlog
### P2 (User-paused)
- Migrate remaining ~35 routes to CreditsService
- A/B test hook text variations
- Remix Variants on share pages

### P3
- Self-hosted GPU models
- WebSockets for admin dashboard

## Test Credentials
- Test User: test@visionary-suite.com / Test@2026#
- Admin User: admin@creatorstudio.ai / Cr3@t0rStud!o#2026
