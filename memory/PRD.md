# Visionary Suite — Product Requirements Document

## Problem Statement
Build a viral, addictive "Story Universe Engine" — an AI creator suite that generates story videos, comics, reels. The platform must feel alive and Netflix-like, not like an empty tool grid. **The dashboard must NEVER show empty under any data condition.**

## Architecture
- **Frontend**: React (CRA) + Tailwind CSS + Shadcn/UI
- **Backend**: FastAPI + MongoDB (motor) + Redis
- **Storage**: Cloudflare R2 via backend proxy (`/api/media/r2/`)
- **AI**: OpenAI GPT-4o-mini, Sora 2, TTS + Gemini via Emergent LLM Key
- **Payments**: Cashfree
- **Auth**: JWT + Emergent Google Auth

## What's Been Implemented

### P0 — Netflix-Style Dashboard (DONE — Mar 28, 2026)
**Root causes found and fixed across 3 iterations:**
1. Backend `thumbnail_url` filter hid stories without thumbnails → Removed filter
2. Frontend `{xxx.length > 0 && <Row/>}` conditional rendering hid ALL rows when trending was empty → Rows now render unconditionally
3. Hero video `moov` atom at end of file (no faststart) → Re-muxed + pipeline fixed
4. R2 proxy had no HEAD or Range support → Added both for video streaming

**Current architecture:**
- **Hero** ALWAYS renders: Real story poster/video when data exists, gradient CTA ("Your Story Universe Awaits") when empty
- **Trending Now** ALWAYS renders: Real story cards or 6 seed CTA cards with creative story prompts
- **Fresh Stories** ALWAYS renders: Same fallback strategy
- **Watch Now**: Conditional (only when real video stories exist)
- **Seed cards**: 6 pre-written story ideas with CREATE badges, + Create CTAs, gradient backgrounds. Click navigates to story creator with title as prefill.
- **Video**: Layered approach (gradient → thumbnail image → autoplay video). Faststart moov for streaming. H.264 graceful fallback to poster.
- **Credits**: Skeleton → exact number → "Unlimited". refreshCredits() on mount.

### P0 — Core Pipeline (DONE)
- Story-to-Video: GPT → image → Sora 2 → TTS → FFmpeg concat with `-movflags +faststart`

### P0 — R2 Media Proxy (DONE)
- `/api/media/r2/{filepath}`: HEAD (200), Range (206), GET (200)

### P0 — Growth Loop (DONE)
### P1 — Monetization (DONE)
### P1 — Trust Fixes (DONE)

## Pending / Backlog
- P1: A/B test hook text variations
- P1: Character-driven auto-share prompts
- P2: Remix Variants, Self-hosted GPU, WebSocket admin, Story Chain leaderboard
- Blocked: SendGrid email (needs valid API key)

## Key Endpoints
- `GET /api/engagement/story-feed` — 20 completed stories (no thumbnail filter)
- `GET /api/media/r2/{path}` — HEAD + Range + GET support
- `GET /api/credits/balance` — User credits

## Test Credentials
- Test: `test@visionary-suite.com` / `Test@2026#`
- Admin: `admin@creatorstudio.ai` / `Cr3@t0rStud!o#2026`
