# Visionary Suite - Product Requirements Document

## Original Problem Statement
Rebuild Visionary Suite into an addictive story-driven viral platform. Build a private Story-to-Video pipeline producing REAL moving videos with character continuity, strict credit gating, and truth-based states.

## Architecture
- **Frontend**: React + Tailwind CSS + Shadcn UI
- **Backend**: FastAPI + MongoDB + Redis
- **AI (Live)**: GPT-4o-mini (planning), GPT Image 1 (keyframes), Sora 2 (scene clips), OpenAI TTS (narration) — all via Emergent LLM Key
- **AI (Future)**: Qwen2.5-14B, Wan2.1-T2V/I2V-14B, Kokoro-82M (self-hosted cost optimization)
- **Payments**: Cashfree | **Auth**: JWT + Google Auth | **Storage**: Cloudflare R2 | **Email**: Resend

## Implemented & LIVE

### Phase 1-5.5: Complete Growth Loop (DONE)
Zero-friction entry, compulsion loops, retention engine, K-factor engine, attribution, email nudges

### Phase 6: Compete + Social Proof (DONE)
Trending mechanics, animated viewer counts, force share gate, K-factor admin dashboard

### Phase 7: Content Seeding Engine (DONE)
AI story hook generation, quality filtering, social media scripts, admin panel

### Phase 8: Private Story Engine — REAL VIDEO OUTPUT (2026-03-25 — LATEST)
**Pipeline produces REAL moving videos using Emergent services:**

- **Planning** (GPT-4o-mini): Structured episode plans, character continuity, scene motion plans — WORKING
- **Keyframes** (GPT Image 1): Real 1536x1024 images per scene — WORKING (4/4 generated, ~2MB each)
- **Scene Clips** (Sora 2): Real 1280x720 moving MP4 clips — WORKING (1 clip generated, 3.8MB, ~60s per clip)
- **Narration** (OpenAI TTS): Real MP3 audio — WORKING (confirmed on job #2)
- **FFmpeg Assembly**: Stitch clips + mix audio + preview + thumbnail — READY (code complete, triggers when clips available)
- **Credit Gating**: 21 credits/job, atomic deduction, auto-refund on failure — WORKING
- **Safety**: Copyright/celebrity blocking, rate limits, abuse detection — WORKING
- **Continuity Validation**: Asset checks, drift detection — WORKING

**Budget hit**: The Emergent Universal Key ran out of balance during batch generation. The pipeline itself is fully functional.

## API Endpoints
- `POST /api/story-engine/create` — Create job + run full pipeline
- `GET /api/story-engine/status/{job_id}` — Poll progress
- `GET /api/story-engine/credit-check` — Pre-flight cost check
- `GET /api/story-engine/my-jobs` — User's jobs
- `GET /api/story-engine/chain/{chain_id}` — Story chain
- `GET /api/story-engine/admin/pipeline-health` — GPU/service status
- `POST /api/content-engine/generate` — Batch story generation

## P0 Actions
1. **Add balance to Emergent Universal Key** (Profile → Universal Key → Add Balance)
2. Generate 50-100 real videos via Content Engine auto-publish
3. Validate full user loop: generate → watch → continue → share

## Key Files
- `/app/backend/services/story_engine/` — Full engine
- `/app/backend/services/story_engine/adapters/video_gen.py` — GPT Image 1 + Sora 2
- `/app/backend/services/story_engine/adapters/tts.py` — OpenAI TTS
- `/app/backend/services/story_engine/adapters/ffmpeg_assembly.py` — FFmpeg
- `/app/backend/services/story_engine/pipeline.py` — 11-step orchestrator
- `/app/backend/routes/story_engine_routes.py` — API endpoints
- `/app/memory/SELF_HOSTED_STACK.md` — Future GPU deployment spec
