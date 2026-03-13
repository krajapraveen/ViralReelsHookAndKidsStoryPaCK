# Visionary-Suite PRD

## Original Problem Statement
The "Story To Video" feature was unstable, slow, and unreliable in production. The system was re-architected into a durable, async, stage-based job pipeline. After deployment, production experienced persistent crash loops (520 errors) and OOM kills due to ffmpeg memory exhaustion.

## Architecture
- **Frontend**: React (CRA with craco) on port 3000
- **Backend**: FastAPI on port 8001 
- **Database**: MongoDB (creatorstudio_production)
- **Storage**: Cloudflare R2
- **Payment**: Cashfree
- **LLM**: OpenAI GPT-4o-mini, GPT Image 1, OpenAI TTS, Sora 2
- **Video Processing**: ffmpeg (system dependency via apt-packages.txt)

## What's Been Implemented

### Story → Video Pipeline (Stable)
- Stage-based async pipeline: Scenes → Images → Voices → Render → Upload
- 1 dedicated pipeline worker (production stability)
- DB-persisted checkpoints for every stage
- Per-stage retries with backoff
- Resume-on-refresh capability
- Credit deduction on creation, refund on failure

### Production-Safe Render Stage (P0 Fix - 2026-03-13)
- **Sequential scene rendering** (one ffmpeg at a time)
- **Single-threaded ffmpeg** (`-threads 1` on ALL ffmpeg calls)
- **640x360 resolution** at 10fps (CRF 35)
- **-nostdin, -loglevel error** auto-injected on all ffmpeg calls
- **maxrate/bufsize: 400k** for bounded memory
- **Aggressive temp cleanup** + `gc.collect()` after each scene
- **Concat step also single-threaded** with matching low-memory settings
- Stale job cleanup on startup → FAILED + credits refunded
- Async ffmpeg subprocesses (non-blocking)

### Verified Render Benchmarks (Preview)
| Metric | Value |
|--------|-------|
| Per-scene render time | 1.3-2.4s |
| Total render (3 scenes + concat) | 4.9-7.4s |
| Full pipeline time | 78-86s |
| Video file size | 0.5-0.6MB |
| Resolution | 640x360 @ 10fps |
| Worker count | 1 |

### Stability Test Results (Preview - 2026-03-13)
- **5 consecutive runs**: 5/5 COMPLETED ✅
- **3 concurrent runs**: 3/3 COMPLETED ✅ (sequential by 1 worker)
- **Stale job recovery**: Verified - cleanup on restart + refund ✅
- **Video download**: Verified - valid H.264 MP4 ✅
- **Testing agent**: 100% backend (13/13), 100% frontend ✅

## Key Files
- `/app/backend/services/pipeline_engine.py` - Core pipeline logic + render stage
- `/app/backend/services/pipeline_worker.py` - Worker pool management
- `/app/backend/routes/pipeline_routes.py` - API endpoints
- `/app/backend/server.py` - Server startup with staggered initialization
- `/app/frontend/src/pages/StoryVideoPipeline.js` - Frontend component

## Current Status (2026-03-13)

### P0: Story To Video OOM Fix
- **Status**: ✅ FIXED AND VERIFIED (Preview)
- **Awaiting**: Production deployment and production verification

### P1: SendGrid Email Service  
- **Status**: BLOCKED (awaiting user's SendGrid plan upgrade)

## Pending Production Tests (After Deployment)
1. 5 consecutive single-user Story→Video runs
2. 3 concurrent runs
3. Refresh recovery test
4. Forced failure + refund test
5. Full platform audit (all features)
6. Credit integrity audit
7. Performance benchmarks

## Backlog
- P2: WebSocket progress (replace polling)
- P2: Worker auto-scaling
- P2: Email notification on completion
- P3: Delete obsolete old Story→Video code:
  - `/app/backend/routes/story_to_video_routes/`
  - `/app/backend/routes/standard_story_to_video_routes/`
  - `/app/frontend/src/pages/StoryToVideoStudio.js`
- P3: GPU-accelerated rendering

## Test Credentials
- UAT: test@visionary-suite.com / Test@2026#
- Admin: admin@creatorstudio.ai / Cr3@t0rStud!o#2026

## API Endpoints
- POST /api/pipeline/create
- GET /api/pipeline/status/{job_id}
- POST /api/pipeline/resume/{job_id}
- GET /api/pipeline/user-jobs
- GET /api/pipeline/options
- GET /api/pipeline/workers/status
