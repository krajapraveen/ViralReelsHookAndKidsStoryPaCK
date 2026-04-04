# AI Creator Suite — Product Requirements Document

## Original Problem Statement
Full-stack AI creator suite with tools for story/comic/GIF/video generation, character creation, brand kits, and social content. Credit-based monetization with Cashfree payments. Features a "compulsion-driven" growth engine. Latest focus: "Daily Viral Idea Drop" — a queue-driven content pack generator producing viral-ready text, image, audio, and video assets with guaranteed output.

## Core Architecture
- **Frontend**: React (port 3000)
- **Backend**: FastAPI (port 8001)
- **Database**: MongoDB
- **AI**: OpenAI GPT-4o-mini (text), GPT Image 1 (thumbnails), OpenAI TTS (voiceover), Gemini (fallback text) — all via Emergent LLM Key
- **Video**: moviepy + ffmpeg (fast social video composition)
- **Storage**: Cloudflare R2
- **Payments**: Cashfree
- **Auth**: Emergent-managed Google Auth + JWT

## Completed Features

### P0 — Daily Viral Idea Drop Phase 2 (April 2026)
**New workers:**
- **Audio worker**: OpenAI TTS voiceover (voice=shimmer/energetic), skips gracefully if TTS fails
- **Video fast worker**: moviepy-based 6s MP4 from thumbnail + hook text overlay + Ken Burns zoom. Speed-first, not cinematic.
- **Repair worker**: Detects partial failures, retries individual tasks (max 3 attempts), structured failure reasons
- **Feedback flow**: 6 signals (useful, not_useful, regenerate_angle, more_aggressive_hook, safer_hook, better_captions), stored per asset type + niche

**Architecture:**
- 2-phase pipeline: Phase 1 (text+image in parallel) → Phase 2 (audio+video dispatched after Phase 1)
- Atomic Phase 2 dispatch via MongoDB `_phase2_dispatched` flag (prevents double dispatch)
- 7 total tasks per job, 7 registered queue handlers
- Partial failure never blocks pack delivery

**New API endpoints:**
- `POST /api/viral-ideas/jobs/{job_id}/feedback` — submit feedback signal
- `POST /api/viral-ideas/jobs/{job_id}/repair` — repair failed/incomplete tasks
- `GET /api/viral-ideas/feedback/summary` — aggregated feedback (for future ranking)

**Files:** `audio_generation_service.py`, `workers/audio_fast_worker.py`, `workers/video_fast_worker.py`, `workers/repair_worker.py`
**Test:** 21/21 tests passed (iteration_424)

### P0 — Daily Viral Idea Drop Phase 1 (April 2026)
- Queue-driven content pack generator with orchestrator/worker pattern
- 4 API routes, 7 services, 4→7 workers behind queue abstraction (`dispatch_task`)
- GPT-4o-mini primary, Gemini fallback, deterministic template fallback
- ZIP bundle packaging with race-condition-safe atomic dispatch
- Frontend: 3-view system (Feed → Progress → Result)

### Previous Completions
- Safe Rewrite Engine (20+ files)
- Story Video Studio crash fix
- Auth optimization (Google Auth instant redirect)
- Growth Engine, Cashfree Payments, Credit System
- Truth-based Admin Dashboard

## Current Status: Phase 2 Complete

## Next: P0 Phase 3 (When approved)
- Personalization, precomputed daily packs
- Quality mode upgrades
- Admin metrics dashboard
- Cost/margin analytics
- Retry better quality flow

## Frozen Backlog
- Share This Pack feature (P1 — premature until output quality is stronger)
- Auto captions for Reaction GIFs (P1)
- Multi-reaction pack generation (P1)
- Character DNA System (P1)
- A/B test hook variations (P1)
- Smart router, Advanced analytics (P2)

## Test Credentials
- Test User: `test@visionary-suite.com` / `Test@2026#`
- Admin User: `admin@creatorstudio.ai` / `Cr3@t0rStud!o#2026`
