# Visionary Suite — Product Requirements Document

## Original Problem Statement
Build a viral, addictive "Story Universe Engine" with an optimized frontend growth loop and a Private, Self-Hosted Story-to-Video Engine backend. The architecture must enforce a strict pipeline: Episode Planning → Character Memory → Keyframe Generation → Moving Scene Clip Generation → FFmpeg Assembly.

## Architecture
- **Frontend**: React (Vite-like CRA), Shadcn UI, TailwindCSS
- **Backend**: FastAPI, Python 3.11
- **Database**: MongoDB
- **Storage**: Cloudflare R2 (Object Storage)
- **AI**: OpenAI GPT-4o-mini (planning), GPT Image 1 (keyframes), Sora 2 (clips), TTS — via Emergent LLM Key
- **Payments**: Cashfree

## What's Been Implemented

### P0.5 "Make It Look Alive" (DONE)
- Truth-based hype text, social proof badges, scroll traps on Dashboard

### P1 Zero-Friction Entry (DONE)
- Login only required on "Generate" click, full state preservation via localStorage

### P1 Share Reward System (DONE)
- +5/+15/+25 credit rewards for sharing, continuing, signing up

### P1 Click Psychology (DONE)
- Cinematic 4:5 ratio cards, overlaid hooks, urgency text, A/B tracking

### P1 Gallery / Explore Page (DONE)
- `/app/explore` with infinite scroll, category filters, sorting

### P0 Frontend → Story Engine Migration (DONE — 2026-03-26)
- **Wired ALL frontend calls** from `/api/pipeline/*` to `/api/story-engine/*`
- New Story Engine routes serve as SINGLE SOURCE OF TRUTH
- Transparent fallback: new endpoints query BOTH `story_engine_jobs` AND legacy `pipeline_jobs`
- Merged user-jobs listing shows all videos regardless of which pipeline created them
- Legacy pipeline routes kept ONLY for Gallery and Admin analytics
- Old pipeline_routes.py marked DEPRECATED
- **Testing**: 100% pass rate (34/34 backend, 12/12 frontend features)

### Trust & UI Fixes (DONE)
- Fixed broken Security tab, truth-based admin metrics, authentic live feed

### Monetization (DONE)
- Cashfree payments, strict credit checks, 50-credit standard allocation

## Prioritized Backlog

### P0 — In Progress
- None (migration complete)

### P1 — Next Up
- A/B test hook text variations on public pages
- Character-driven auto-share prompts after creation
- Rebuild Public Share Page (`/v/{slug}`) with auto-play video + CTA

### P2 — Future
- Remix Variants on share pages
- WebSocket upgrade for admin dashboard
- Story Chain leaderboard
- UI polish and style preset preview thumbnails

### P3 — Long Term
- Self-hosted GPU migration (Wan2.1, Kokoro) to replace Emergent APIs
- Branching episodes
- Mobile app wrapper

## API Architecture (Current State)

### PRIMARY: /api/story-engine/* (Story Engine — Single Source of Truth)
- `GET /options` — Animation styles, age groups, voice presets
- `GET /rate-limit-status` — Rate limit check
- `POST /create` — Create new video job (uses Story Engine pipeline)
- `GET /status/{job_id}` — Poll progress (queries both collections)
- `GET /validate-asset/{job_id}` — Post-gen asset validation
- `GET /user-jobs` — Merged jobs list (engine + legacy)
- `POST /resume/{job_id}` — Resume failed jobs (both engines)
- `GET /preview/{job_id}` — Scene preview data
- `POST /notify-when-ready/{job_id}` — Completion notification
- `GET /asset-proxy` — CORS proxy for R2 assets
- `POST /generate-fallback/{job_id}` — Fallback assets for legacy jobs

### LEGACY (DEPRECATED): /api/pipeline/*
- Gallery endpoints (gallery, categories, leaderboard)
- Admin analytics (funnel, performance, workers)
- Kept because they query `pipeline_jobs` collection directly

## Credentials
- Test User: `test@visionary-suite.com` / `Test@2026#`
- Admin User: `admin@creatorstudio.ai` / `Cr3@t0rStud!o#2026`
