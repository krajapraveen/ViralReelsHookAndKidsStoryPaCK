# Daily Viral Idea Drop — PRD

## Original Problem Statement
Build a "Growth Engine" / "Daily Viral Idea Drop" — a queue-driven AI content creation platform that generates full viral content packs (hooks, scripts, captions, thumbnails, voiceover, video) from trending ideas. The product must never show a dead-end UI and must be optimized strictly for growth and conversion.

## Core Architecture
- React frontend + FastAPI backend + MongoDB
- 7 background workers: text, image, audio, video, packaging, orchestrator, repair
- Queue abstraction simulating Redis using Python asyncio
- Fallback ladder: GPT-4o-mini → Gemini → deterministic templates
- Teaser-first share pages with soft paywalls
- Static files served locally via `/api/static/generated/...`

## Key DB Collections
- `viral_ideas_daily`, `viral_jobs`, `viral_job_tasks`, `viral_assets`, `viral_job_events`

## 3rd Party Integrations
- OpenAI & Gemini (Emergent LLM Key)
- Cloudflare R2 (Object Storage — for other features, NOT viral pack assets yet)
- Cashfree (Payments)
- Google Auth (Emergent-managed)

## What's Been Implemented

### Phase 1 & 2: Backend Workers (DONE)
- Orchestrator + 7 parallel workers (text, image, audio, video, packaging, repair)
- Queue abstraction, fallback ladder, output guarantee

### Growth Engine (DONE)
- Teaser-first share pages, soft paywalls, viral hooks

### P0 Fix: Empty Feed Blocker (DONE)
- 12 hardcoded fallback ideas, triple-layer fallback

### P0 Fix: Generation Blank Screen Bug (DONE — April 4, 2026)
- Root cause: `handleGenerate` never set idea context state + ProgressView not receiving props
- Fix: Added state setters + prop passing

### P0 Fix: Broken Media Assets on Result Page (DONE — April 4, 2026)
**Root causes identified:**
1. **Video encoding**: moviepy's bundled ffmpeg v7.0.2 produced MP4s with moov atom at end + potential codec profile issues
2. **No error handling**: All media elements (`<video>`, `<audio>`, `<img>`) had no `onError` handlers, showing browser-native error states

**Fixes applied:**
1. **Video worker** (`video_fast_worker.py`): Added system ffmpeg re-encode post-processing (`-profile:v baseline -level 3.0 -movflags +faststart -pix_fmt yuv420p`)
2. **VideoAsset component**: Error handler shows "Video preview unavailable" + Retry + Download MP4
3. **VoiceoverAsset component**: Error handler shows "Audio preview unavailable" + Retry + Download Audio
4. **ThumbnailAsset component**: Error handler shows placeholder + Retry + Download Image
5. **Progress view thumbnail**: Added `onError` to hide broken image
6. **Retroactive fix**: All existing videos re-encoded with system ffmpeg
7. **Deployment fixes**: Quoted URL values in .env files for containerized parsing

**Important note for production:**
- Media files (video, audio, thumbnails) are stored on the LOCAL filesystem of the server
- Files generated in preview won't exist on production unless the same server is used
- For persistent cross-deployment media, consider migrating to R2 object storage

## User Mandate
- Optimizing strictly for Growth and Conversion
- Do NOT build new features (admin dashboards, personalization, UI polish)
- Only fix blockers or increase shares/revenue

## Backlog (Frozen by User)
- (P1) Migrate viral pack media assets to R2 for cross-deployment persistence
- (P1) A/B test hook text variations
- (P1) Character-driven auto-share prompts
- (P1) Personalization and Admin Dashboard
- (P1) Precomputed Daily Packs
- (P1) Quality Modes and advanced routing
- (P2) Remix Variants on share pages
- (P2) Story Chain leaderboard
- (P2) General UI polish

## Key Files
- `/app/frontend/src/pages/DailyViralIdeas.js` — Feed, Progress, Result views + VideoAsset, ThumbnailAsset, VoiceoverAsset components
- `/app/frontend/src/pages/ViralPackShare.js` — Teaser-first share page
- `/app/backend/routes/viral_ideas_v2.py` — Fallback ideas, feed, generation
- `/app/backend/services/viral/workers/video_fast_worker.py` — Video worker with system ffmpeg re-encode
- `/app/backend/services/viral/workers/audio_fast_worker.py` — Audio worker (TTS)
- `/app/backend/services/viral/workers/*.py` — Other workers

## Credentials
- Test: `test@visionary-suite.com` / `Test@2026#`
- Admin: `admin@creatorstudio.ai` / `Cr3@t0rStud!o#2026`
