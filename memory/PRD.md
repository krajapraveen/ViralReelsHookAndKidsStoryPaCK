# Visionary-Suite PRD

## Original Problem Statement
The "Story To Video" feature was unstable, slow, and unreliable in production. The system was re-architected into a durable, async, stage-based job pipeline. After deployment, production experienced a persistent crash loop (520 errors) requiring multiple fixes.

## Architecture
- **Frontend**: React (CRA with craco) on port 3000
- **Backend**: FastAPI on port 8001 
- **Database**: MongoDB (creatorstudio_production)
- **Storage**: Cloudflare R2
- **Payment**: Cashfree
- **LLM**: OpenAI GPT-4o-mini, GPT Image 1, OpenAI TTS, Sora 2

## What's Been Implemented

### Story → Video Pipeline (Re-architected)
- Stage-based async pipeline: Scenes → Images → Voices → Render → Upload
- 1 dedicated pipeline worker (reduced from 3 for stability)
- DB-persisted checkpoints for every stage
- Per-stage retries with backoff
- Resume-on-refresh capability
- Credit deduction on creation, refund on failure
- Async ffmpeg rendering (asyncio.create_subprocess_exec)
- Voice + Image upload to R2 for durability
- Download fallbacks from R2 in render stage
- ffprobe fault-tolerance

### Production Crash-Fix (Pending Deployment)
- Stale PROCESSING/QUEUED jobs marked FAILED + refunded on startup (prevents crash loop)
- Staggered service startup (10s/15s/20s delays)
- Worker counts reduced: pipeline 3→1, job_queue 4→1
- apt-packages.txt for ffmpeg system dependency
- .gitignore cleaned

## Key Files
- `/app/backend/services/pipeline_engine.py` - Core pipeline logic
- `/app/backend/services/pipeline_worker.py` - Worker pool management
- `/app/backend/routes/pipeline_routes.py` - API endpoints
- `/app/backend/server.py` - Server startup with staggered initialization
- `/app/frontend/src/pages/StoryVideoStudioPipeline.js` - Frontend component

## Current Status (2026-03-13)

### P0: Production 520 Crash Loop
- **Status**: FIX READY, AWAITING DEPLOYMENT
- **Root Cause**: On restart, workers re-process stale PROCESSING/QUEUED jobs → ffmpeg memory exhaustion → OOM → crash → restart loop
- **Fix**: Stale jobs marked FAILED + refunded; workers reduced; staggered startup
- **Preview**: Verified working (pipeline completes in ~100-106s)

### P1: SendGrid Email Service  
- **Status**: BLOCKED (awaiting user's SendGrid plan upgrade)

## Preview Test Results (Post-Fix)
- Pipeline runs: 10+ COMPLETED, 0 FAILED
- Avg time: ~100 seconds
- Concurrent (3 jobs): All completed
- Testing agent: 95% backend, 100% frontend pass rate
- Video downloads verified on R2

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
- P3: Delete obsolete old Story→Video code
- P3: GPU-accelerated rendering

## Test Credentials
- UAT: test@visionary-suite.com / Test@2026#
- Admin: admin@creatorstudio.ai / Cr3@t0rStud!o#2026
