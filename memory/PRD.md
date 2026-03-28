# Visionary Suite — Product Requirements Document

## Problem Statement
Build a viral, addictive "Story Universe Engine" — an AI creator suite that generates story videos, comics, reels, and more. The platform must feel alive and Netflix-like, not like an empty tool grid.

## Core Users
- **Creators**: Content creators using AI tools to generate story videos, comics, reels
- **Viewers**: Users who discover and continue stories (viral loop)
- **Admin**: Platform operator monitoring analytics, payments, and content

## Architecture
- **Frontend**: React (CRA) with Tailwind CSS + Shadcn/UI
- **Backend**: FastAPI with MongoDB (async motor)
- **Storage**: Cloudflare R2 via backend proxy (`/api/media/r2/`)
- **AI**: OpenAI GPT-4o-mini, Sora 2, TTS + Gemini via Emergent LLM Key
- **Payments**: Cashfree
- **Auth**: JWT + Emergent Google Auth

## What's Been Implemented

### P0 — Core Pipeline (DONE)
- Story-to-Video generation: GPT text → image gen → Sora 2 video → TTS audio → FFmpeg concat
- FFmpeg assembly uses reliable `concat` method (xfade was broken)
- All AI tools enforce credit deduction before generation

### P0 — Netflix-Style Dashboard (DONE — Feb 28, 2026)
- **Hero Section**: Full-bleed autoplaying video with muted/loop/playsInline, title, hook text, FEATURED badge, LIVE indicator, Watch & Continue / Create New CTAs, mute toggle, 5-hero carousel with dots
- **Trending Now Row**: Top 8 stories by engagement, large cards (w-72), horizontal scroll with arrows
- **Fresh Stories Row**: 8 most recent stories, medium cards
- **Watch Now Row**: 8 stories with video output, medium cards
- **Story Cards**: 3:4 aspect ratio, real thumbnails via R2 proxy, dark gradient overlay, badge (TRENDING/HOT/NEW), title, italic hook text, hover-to-play video, scale animation
- **Credits Display**: Skeleton while loading, exact number when loaded, "Unlimited" for pro users
- **Create Bar**: Inline search input + Create button
- **Quick Tools**: Pill-style shortcuts (Story Video, Reels, Comic, Bedtime)
- **Zero dead space**: 0px gap between hero and first content row
- **Loading Skeleton**: Full-page skeleton with hero + card placeholders

### P0 — R2 Media Proxy (DONE)
- Backend proxy at `/api/media/r2/{filepath}` streams files via boto3
- Bypasses Cloudflare R2 presigned URL 403 errors
- Frontend `mediaUrl()` helper converts proxy paths to full URLs

### P0 — Growth Loop / Compulsion Engine (DONE)
- Redesigned public share pages with momentum-based social proof
- 1-click continue flow (generation before login)
- Enforced open-loop story endings
- Character Power Score

### P1 — Monetization (DONE)
- Cashfree payment integration
- Strict credit checks before generation
- 50-credit standard allocation for new users
- Admin dashboard with real revenue/credit metrics

### P1 — Trust Fixes (DONE)
- Fixed broken Profile → Security tab
- Truth-based admin satisfaction metric
- Diverse "Live on Platform" feed (no fake data)
- Credit system consistency (eliminated hidden 100-credit grants)

## Pending / Backlog

### P1 — Upcoming
- A/B test hook text variations on story cards
- Character-driven auto-share prompts after creation

### P2 — Future
- Remix Variants on share pages
- Self-hosted GPU models (Wan2.1, Kokoro) to replace APIs
- WebSocket admin dashboard for live updates
- Story Chain leaderboard
- General UI polish and style preset thumbnails

### P2 — Blocked
- SendGrid email (forgot password) — blocked on valid API key

## Key Endpoints
- `GET /api/engagement/story-feed` — Dashboard feed (hero + trending + characters + stats)
- `GET /api/media/r2/{filepath}` — R2 media proxy
- `GET /api/credits/balance` — User credit balance
- `POST /api/auth/login` — Login
- `GET /api/engagement/explore` — Gallery with category filters

## Test Credentials
- Test User: `test@visionary-suite.com` / `Test@2026#`
- Admin User: `admin@creatorstudio.ai` / `Cr3@t0rStud!o#2026`
