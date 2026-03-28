# Visionary Suite — Product Requirements Document

## Problem Statement
Build a viral, addictive "Story Universe Engine" — an AI creator suite that generates story videos, comics, reels. The platform must feel alive and Netflix-like, not like an empty tool grid.

## Architecture
- **Frontend**: React (CRA) + Tailwind CSS + Shadcn/UI
- **Backend**: FastAPI + MongoDB (motor) + Redis
- **Storage**: Cloudflare R2 via backend proxy (`/api/media/r2/`)
- **AI**: OpenAI GPT-4o-mini, Sora 2, TTS + Gemini via Emergent LLM Key
- **Payments**: Cashfree
- **Auth**: JWT + Emergent Google Auth

## What's Been Implemented

### P0 — Netflix-Style Dashboard (DONE — Mar 28, 2026)
- **Hero Section**: Layered approach (gradient → thumbnail image → autoplay video). FEATURED badge, carousel (5 stories), title, hook text, Watch & Continue / Create New CTAs.
- **Video autoplay**: Works in real Chrome (H.264+AAC with faststart moov). Graceful fallback to thumbnail in non-H264 browsers.
- **Three dense rows**: Trending Now (10 cards), Fresh Stories (10 cards), Watch Now (10 cards). No dead space.
- **Story cards**: 3:4 aspect ratio, gradient/thumbnail background, dark overlay, badges (TRENDING/HOT/NEW), italic hook text, Continue CTA, hover-to-play video.
- **Credits**: Skeleton → exact number → "Unlimited". RefreshCredits on mount for post-login flow.
- **Create bar**: Search input + Create button. Quick Tools pills (Story Video, Reels, Comic, Bedtime).
- **Zero dead space**: 0px gap between hero and first row.
- **Root causes fixed**:
  - Backend `thumbnail_url` filter removed — stories without thumbnails now shown with gradient fallbacks
  - Hero video re-muxed with `-movflags +faststart` (moov at byte 40)
  - R2 proxy supports HEAD + Range requests (206 Partial Content) for video streaming
  - All FFmpeg encoding commands now include `-movflags +faststart`

### P0 — Core Pipeline (DONE)
- Story-to-Video: GPT text → image gen → Sora 2 video → TTS audio → FFmpeg concat
- FFmpeg uses reliable `concat` with `-movflags +faststart` for web streaming
- All AI tools enforce credit deduction

### P0 — R2 Media Proxy (DONE)
- `/api/media/r2/{filepath}` streams via boto3
- HEAD requests: 200 with Content-Length + Accept-Ranges
- Range requests: 206 Partial Content with Content-Range
- Full GET: 200 with complete file
- Bypasses Cloudflare R2 presigned URL 403 errors

### P0 — Growth Loop (DONE)
- Public share pages with momentum social proof
- 1-click continue flow
- Open-loop story endings

### P1 — Monetization (DONE)
- Cashfree payments, strict credit checks
- 50-credit standard for new users
- Admin dashboard with real metrics

### P1 — Trust Fixes (DONE)
- Profile → Security tab fixed
- Truth-based admin satisfaction metric
- Diverse "Live on Platform" feed

## Pending / Backlog

### P1 — Upcoming
- A/B test hook text variations on story cards
- Character-driven auto-share prompts

### P2 — Future
- Remix Variants on share pages
- Self-hosted GPU models (Wan2.1, Kokoro)
- WebSocket admin dashboard
- Story Chain leaderboard

### P2 — Blocked
- SendGrid email (forgot password) — blocked on valid API key

## Key Endpoints
- `GET /api/engagement/story-feed` — Dashboard feed (hero + 20 trending + characters + stats)
- `GET /api/media/r2/{filepath}` — R2 media proxy (HEAD, Range, GET)
- `GET /api/credits/balance` — User credit balance
- `POST /api/auth/login` — Login

## Test Credentials
- Test User: `test@visionary-suite.com` / `Test@2026#`
- Admin User: `admin@creatorstudio.ai` / `Cr3@t0rStud!o#2026`
