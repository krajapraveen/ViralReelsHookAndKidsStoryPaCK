# Visionary Suite — Product Requirements Document

## Original Problem Statement
Build a viral, addictive "Story Universe Engine" with an optimized frontend growth loop and a Private Story-to-Video Engine backend. Pipeline: Episode Planning → Character Memory → Keyframe Generation → Moving Scene Clip Generation → FFmpeg Assembly.

## Architecture
- **Frontend**: React (CRA), Shadcn UI, TailwindCSS
- **Backend**: FastAPI, Python 3.11
- **Database**: MongoDB
- **Storage**: Cloudflare R2 (Object Storage)
- **AI**: GPT-4o-mini (planning), GPT Image 1 (keyframes), Sora 2 (clips), OpenAI TTS — via Emergent LLM Key
- **Video Assembly**: FFmpeg 5.1 (system binary, must be installed on deploy server)
- **Payments**: Cashfree
- **NOTE**: System is NOT yet a fully independent personal API. Still depends on external LLM/video/TTS budgets.

## What's Been Implemented

### P0 E2E Story Engine — PROVEN (2026-03-26)
**"The Crystal Cave" — Full pipeline validated with real AI outputs:**
- INIT → PLANNING (GPT-4o-mini episode plan with cliffhanger)
- → BUILDING_CHARACTER_CONTEXT (2 characters: Sage the fox, Owl the wise mentor)
- → PLANNING_SCENE_MOTION (4 scene motion plans with camera/action directives)
- → GENERATING_KEYFRAMES (4 GPT Image 1 keyframes, uploaded to R2)
- → GENERATING_SCENE_CLIPS (3 Sora 2 video clips + 1 Ken Burns fallback)
- → GENERATING_AUDIO (OpenAI TTS narration)
- → ASSEMBLING_VIDEO (FFmpeg stitch + audio mix + transitions)
- → READY (final video 14.5s, 4.7MB, hosted on R2)
- Credit deduction (21 credits) and refund on failure both proven
- Public share page: video auto-plays, character intro, cliffhanger displayed

**Known Issues:**
- FFmpeg assembly requires `ffmpeg` system binary (not a Python package)
- Hot-reload during FFmpeg assembly can kill subprocess — mitigated with `os.setsid` process isolation
- Assembly retry-from-checkpoint available via admin endpoint `/admin/retry-assembly/{job_id}`

### P0 Frontend → Story Engine Migration (DONE)
- ALL frontend calls use `/api/story-engine/*` (single source of truth)
- Transparent fallback queries both `story_engine_jobs` AND `pipeline_jobs`
- Testing: 100% pass rate (iteration_344)

### P1 Public Share Page Rebuild (DONE)
- Auto-play video when video_url exists
- Character intro badges, character cards, cliffhanger section
- Post-video CTA overlay
- Testing: 100% pass rate (iteration_345)

### Earlier Completed Work
- P0.5 Truth-based hype text, social proof, scroll traps
- P1 Zero-Friction Entry (login only on Generate)
- P1 Share Reward System (+5/+15/+25 credits)
- P1 Click Psychology (cinematic cards, A/B tracking)
- P1 Gallery / Explore Page (infinite scroll, filters)
- Trust & UI Fixes, Monetization (Cashfree)

## Prioritized Backlog

### P1 — Next Up
- Character-driven auto-share prompts after creation
- A/B test hook text variations on public pages
- E2E validation: degraded/fallback job and continue/chain job (pending budget)

### P2 — Future
- Remix Variants, WebSocket admin dashboard, Story Chain leaderboard
- Self-hosted GPU migration (Wan2.1, Kokoro) for true independence

### P3 — Long Term
- Branching episodes, Mobile app wrapper

## API Architecture

### PRIMARY: /api/story-engine/* (Single Source of Truth)
- `GET /options`, `GET /rate-limit-status`, `POST /create`
- `GET /status/{job_id}`, `GET /validate-asset/{job_id}`, `GET /user-jobs`
- `POST /resume/{job_id}`, `GET /preview/{job_id}`, `POST /notify-when-ready/{job_id}`
- `GET /asset-proxy`, `POST /generate-fallback/{job_id}`
- `POST /admin/retry-assembly/{job_id}` — Retry only FFmpeg assembly

### PUBLIC: /api/public/* (No Auth)
- `GET /creation/{slug}` — Returns video_url, characters, cliffhanger

## Credentials
- Test User: `test@visionary-suite.com` / `Test@2026#`
- Admin: `admin@creatorstudio.ai` / `Cr3@t0rStud!o#2026`

## Deploy Requirements
- System: `apt-get install ffmpeg` (required for video assembly)
