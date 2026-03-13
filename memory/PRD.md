# Visionary Suite — PRD

## Original Problem Statement
Full-stack SaaS platform for creative content generation. Story → Video was unreliable (blank pages, timeouts, stalled progress). Required a complete architectural redesign.

## P0 Architecture Redesign — Story → Video Pipeline (2026-03-13)

### Architecture Diagram
```
User clicks "Generate Video"
  → POST /api/pipeline/create (<200ms)
  → pipeline_jobs DB doc created (status=QUEUED)
  → Job enqueued to asyncio.Queue
  → One of 3 dedicated workers picks job
  → Executes stages sequentially:
     ┌─────────────────────────────────────────┐
     │ SCENES  → DB checkpoint                 │
     │ IMAGES  → parallel(3), per-scene save   │
     │ VOICES  → parallel(4), per-scene save   │
     │ RENDER  → single-pass ffmpeg            │
     │ UPLOAD  → R2 CDN + verify               │
     └─────────────────────────────────────────┘
  → Frontend polls GET /status/{job_id} every 3s
  → Shows filmstrip thumbnails as scenes complete
  → Final: video player + download
```

### DB Schema: pipeline_jobs
```json
{
  "job_id": "uuid",
  "user_id": "string",
  "title": "string",
  "story_text": "string",
  "status": "QUEUED|PROCESSING|COMPLETED|FAILED",
  "progress": 0-100,
  "current_stage": "scenes|images|voices|render|upload",
  "current_step": "human-readable status",
  "stages": {
    "scenes": { "status": "PENDING|RUNNING|COMPLETED|FAILED|RETRYING", "duration_ms": int, "retry_count": int, "error": str },
    "images": { ... },
    "voices": { ... },
    "render": { ... },
    "upload": { ... }
  },
  "scenes": [ { "scene_number": 1, "title": "...", "narration_text": "...", "visual_prompt": "..." } ],
  "scene_images": { "1": { "url": "...", "storage": "r2" }, ... },
  "scene_voices": { "1": { "path": "...", "duration": 5.2 }, ... },
  "output_url": "https://r2.dev/videos/...",
  "credits_charged": 50,
  "timing": { "scenes_ms": 6000, "images_ms": 49000, "voices_ms": 14000, "render_ms": 17000, "upload_ms": 4000, "total_ms": 90000 },
  "created_at": "datetime",
  "completed_at": "datetime"
}
```

### Stage Execution Design
| Stage | What | Retry | Backoff | Timeout | Checkpoint |
|-------|------|-------|---------|---------|------------|
| Scenes | LLM generates scene breakdown | 3x | 2,4,8s | 90s | Full scene array saved to DB |
| Images | OpenAI GPT Image 1 per scene | 2x + 1 per-scene | 3,6s | 300s | Each image saved individually |
| Voices | OpenAI TTS per scene | 2x | 3,6s | 180s | Each voice saved individually |
| Render | ffmpeg zoompan + concat | 3x | 2,4,8s | 120s | Video file on disk |
| Upload | R2 multipart + verify | 3x | 2,4,8s | 60s | URL verified before COMPLETED |

### Non-retriable failures (fail fast):
- Copyright/blocked content
- Invalid/empty input
- API key not configured
- Insufficient credits

### Resume Design
When a job fails at stage N:
1. Stages 1..N-1 remain COMPLETED (checkpointed)
2. User clicks "Resume from Checkpoint"
3. POST /api/pipeline/resume/{job_id} resets stage N to PENDING
4. Job re-enqueued; worker skips completed stages
5. Stage N re-runs using already-saved partial outputs

Tested: Voice stage failure → resume → completed in 28s (vs 100s full run)

### Performance Benchmark
| Metric | Old System | New Pipeline | Improvement |
|--------|-----------|--------------|-------------|
| Job creation response | 1-2s (or timeout) | **131-176ms** | 10x faster |
| Single user total | 180-300s (often stalled) | **89s** | 2-3x faster |
| 3 concurrent users | Crashed/stalled | **211-278s all complete** | Now works |
| Image generation | Sequential, timeout-prone | **Parallel(3), checkpointed** | Reliable |
| Voice generation | Sequential, timeout-prone | **Parallel(4), checkpointed** | Reliable |
| Render | Multi-pass, slow | **Single-pass, ultrafast preset** | Faster |

### Load Test Results
| Users | Jobs Created | Completed | Failed | Avg Time | Queue Wait |
|-------|-------------|-----------|--------|----------|------------|
| 1 | 1 | 1 | 0 | 89s | 0s |
| 3 | 3 | 3 | 0 | 254s avg | ~0-5s |
| 5+ | Not tested yet | - | - | - | - |

### Credit Verification
- Deductions: 9 jobs × 50 credits = 450 total
- Refunds: 1 × 50 credits (failed job)
- Net: 400 credits for 9 completed videos
- No duplicate deductions, no missing refunds
- Ledger consistent with job status

### Reliability Report
- No blank page: ✅ (body > 500 chars at all times)
- No fake failure: ✅ (status reflects actual state)
- No stuck progress: ✅ (stages advance with checkpoints)
- Resume works: ✅ (tested: voice failure → resume → complete in 28s)
- Refund logic works: ✅ (Pipeline Test 1 failed → 50 credits refunded)
- Final video accessible: ✅ (R2 CDN URLs verified)

### Files Created/Modified
- NEW: `/app/backend/services/pipeline_engine.py` — Pipeline orchestrator
- NEW: `/app/backend/services/pipeline_worker.py` — Worker pool (3 workers)
- NEW: `/app/backend/routes/pipeline_routes.py` — API routes
- NEW: `/app/frontend/src/pages/StoryVideoPipeline.js` — Frontend UI
- MOD: `/app/backend/server.py` — Route registration + worker startup
- MOD: `/app/frontend/src/App.js` — Route to new pipeline component

## API Endpoints
- `POST /api/pipeline/create` — Create job (instant)
- `GET /api/pipeline/status/{job_id}` — Poll progress
- `POST /api/pipeline/resume/{job_id}` — Resume from checkpoint
- `GET /api/pipeline/user-jobs` — User's job history
- `GET /api/pipeline/options` — Available styles/ages/voices
- `GET /api/pipeline/workers/status` — Worker pool diagnostics

## Backlog
- P0: Deploy to production + verify on visionary-suite.com
- P1: 5-10 concurrent user load test
- P1: Full system audit on production
- P2: Worker scaling (auto-scale based on queue depth)
- P2: Email notification when video is ready
- P3: Real-time WebSocket progress (replace polling)
