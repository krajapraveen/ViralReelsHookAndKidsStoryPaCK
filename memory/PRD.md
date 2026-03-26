# Visionary Suite — Product Requirements Document

## Original Problem Statement
Build a viral, addictive "Story Universe Engine" with an optimized frontend growth loop and a Private, Self-Hosted Story-to-Video Engine backend. The architecture must enforce a strict pipeline: Episode Planning → Character Memory → Keyframe Generation → Moving Scene Clip Generation → FFmpeg Assembly.

## Architecture
- **Frontend**: React (CRA), Shadcn UI, TailwindCSS
- **Backend**: FastAPI, Python 3.11
- **Database**: MongoDB
- **Storage**: Cloudflare R2 (Object Storage)
- **AI**: OpenAI GPT-4o-mini (planning), GPT Image 1 (keyframes), Sora 2 (clips), TTS — via Emergent LLM Key
- **Payments**: Cashfree

## What's Been Implemented

### P0 Frontend → Story Engine Migration (DONE — 2026-03-26)
- Wired ALL frontend calls from `/api/pipeline/*` to `/api/story-engine/*`
- Story Engine routes serve as SINGLE SOURCE OF TRUTH
- Transparent fallback: endpoints query BOTH `story_engine_jobs` AND legacy `pipeline_jobs`
- Merged user-jobs listing shows all videos regardless of pipeline source
- Testing: 100% pass rate (34/34 backend, 12/12 frontend — iteration_344)

### P0 E2E Story Engine Validation (PARTIALLY DONE — 2026-03-26)
- Pipeline code validated: INIT → PLANNING → CHARACTER_CONTEXT → MOTION → KEYFRAMES → CLIPS → AUDIO → ASSEMBLY → READY
- Credit deduction (21 credits) and refund on failure both work
- **BLOCKED**: Emergent LLM Key budget exceeded ($204.84 > $204.82 limit)
- **NOT YET INDEPENDENT**: Pipeline still depends on external AI (GPT-4o-mini, Sora 2, TTS)
- Full E2E validation pending budget top-up

### P1 Public Share Page Rebuild (DONE — 2026-03-26)
- `/v/{slug}` now auto-plays video when `video_url` exists (HTML5 `<video>` with autoPlay muted)
- Character intro badges show name, role, personality from Story Engine character_continuity
- Character card section with all characters listed
- Cliffhanger text prominently displayed from episode_plan
- Post-video CTA overlay appears when video ends ("The story doesn't end here...")
- Backend queries BOTH collections (story_engine_jobs + pipeline_jobs)
- Returns video_url, characters[], cliffhanger, episode_number, source fields
- Testing: 100% pass rate (19/19 backend, 14/14 frontend — iteration_345)

### Earlier Completed Work
- P0.5 "Make It Look Alive": Truth-based hype text, social proof, scroll traps
- P1 Zero-Friction Entry: Login only on Generate, full state preservation
- P1 Share Reward System: +5/+15/+25 credit rewards
- P1 Click Psychology: Cinematic 4:5 cards, overlaid hooks, A/B tracking
- P1 Gallery / Explore Page: Infinite scroll, category filters, sorting
- Trust & UI Fixes: Fixed Security tab, truth-based admin metrics, authentic live feed
- Monetization: Cashfree payments, strict credit checks, 50-credit standard

## API Architecture (Current State)

### PRIMARY: /api/story-engine/* (Single Source of Truth)
- `GET /options`, `GET /rate-limit-status`, `POST /create`, `GET /status/{job_id}`
- `GET /validate-asset/{job_id}`, `GET /user-jobs`, `POST /resume/{job_id}`
- `GET /preview/{job_id}`, `POST /notify-when-ready/{job_id}`
- `GET /asset-proxy`, `POST /generate-fallback/{job_id}`

### PUBLIC: /api/public/* (No Auth)
- `GET /creation/{slug}` — Now returns video_url, characters, cliffhanger, source
- `POST /creation/{slug}/remix` — Track remix clicks

### LEGACY (DEPRECATED): /api/pipeline/*
- Gallery endpoints only

## Prioritized Backlog

### P0 — Blocked
- E2E Story Engine validation (3 mandatory test jobs) — **BLOCKED on LLM budget**

### P1 — Next Up
- Character-driven auto-share prompts after creation
- A/B test hook text variations on public pages

### P2 — Future
- Remix Variants on share pages
- WebSocket upgrade for admin dashboard
- Story Chain leaderboard
- Self-hosted GPU migration (Wan2.1, Kokoro) to fully replace Emergent APIs

### P3 — Long Term
- Branching episodes
- Mobile app wrapper

## Credentials
- Test User: `test@visionary-suite.com` / `Test@2026#`
- Admin User: `admin@creatorstudio.ai` / `Cr3@t0rStud!o#2026`
