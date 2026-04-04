# Daily Viral Idea Drop — PRD

## Original Problem Statement
Build a "Growth Engine" / "Daily Viral Idea Drop" — a queue-driven AI content creation platform that generates full viral content packs (hooks, scripts, captions, thumbnails, voiceover, video) from trending ideas. The product must never show a dead-end UI and must be optimized strictly for growth and conversion.

## Core Architecture
- React frontend + FastAPI backend + MongoDB
- 7 background workers: text, image, audio, video, packaging, orchestrator, repair
- Queue abstraction simulating Redis using Python asyncio
- Fallback ladder: GPT-4o-mini → Gemini → deterministic templates
- Teaser-first share pages with soft paywalls

## Key DB Collections
- `viral_ideas_daily`, `viral_jobs`, `viral_job_tasks`, `viral_assets`, `viral_job_events`

## 3rd Party Integrations
- OpenAI & Gemini (Emergent LLM Key)
- Cloudflare R2 (Object Storage)
- Cashfree (Payments)
- Google Auth (Emergent-managed)

## What's Been Implemented

### Phase 1 & 2: Backend Workers (DONE)
- Orchestrator + 7 parallel workers (text, image, audio, video, packaging, repair)
- Queue abstraction, fallback ladder, output guarantee

### Growth Engine (DONE)
- Teaser-first `/share/{job_id}` page with blurred thumbnails, partial scripts
- "Generate Your Own Free Pack" CTA
- Soft paywall & 4 structured viral hook categories

### P0 Fix: Empty Feed Blocker (DONE)
- 12 hardcoded fallback ideas in both backend and frontend
- Triple-layer fallback ensures feed never returns empty

### P0 Fix: Generation Blank Screen Bug (DONE — April 4, 2026)
- **Root cause**: `handleGenerate` never set `activeIdea`/`activeNiche` state, and `ProgressView` wasn't receiving idea context props
- **Fix**: Added `setActiveIdea(idea)` and `setActiveNiche(niche)` calls in `handleGenerate`, passed `ideaText`/`ideaNiche` props to `ProgressView`
- **Verified**: Full flow Feed → Generate → Progress → Result works end-to-end

### P0 Fix: Broken Video & Thumbnail on Result Page (DONE — April 4, 2026)
- **Root cause (video)**: moviepy's bundled ffmpeg v7.0.2 produced MP4 files that some browsers rejected (wrong encoder version, moov atom at end of file)
- **Fix (video worker)**: Added post-processing step using system ffmpeg to re-encode with `-profile:v baseline -level 3.0 -pix_fmt yuv420p -movflags +faststart` for maximum browser compatibility
- **Fix (frontend)**: Added `VideoAsset` and `ThumbnailAsset` components with `onError` handlers that show graceful fallback UI (Retry + Download MP4/Image buttons) instead of broken media elements
- **Retroactive fix**: Re-encoded ALL existing video files with system ffmpeg
- **Verified**: Thumbnail renders, video fallback UI works, all 6 asset types display correctly

## User Mandate
- Optimizing strictly for Growth and Conversion
- Do NOT build new features (admin dashboards, personalization, UI polish)
- Only fix blockers or increase shares/revenue

## Backlog (Frozen by User)
- (P1) Personalization and Admin Dashboard
- (P1) Precomputed Daily Packs
- (P1) Quality Modes and advanced routing
- (P1) A/B test hook text variations
- (P1) Character-driven auto-share prompts
- (P2) Remix Variants on share pages
- (P2) Story Chain leaderboard
- (P2) General UI polish

## Key Files
- `/app/frontend/src/pages/DailyViralIdeas.js` — Feed, Progress, Result views (VideoAsset, ThumbnailAsset components)
- `/app/frontend/src/pages/ViralPackShare.js` — Teaser-first share page
- `/app/backend/routes/viral_ideas_v2.py` — Fallback ideas, feed, generation
- `/app/backend/services/viral/workers/video_fast_worker.py` — Video worker with system ffmpeg re-encode
- `/app/backend/services/viral/workers/*.py` — Other workers

## Credentials
- Test: `test@visionary-suite.com` / `Test@2026#`
- Admin: `admin@creatorstudio.ai` / `Cr3@t0rStud!o#2026`
