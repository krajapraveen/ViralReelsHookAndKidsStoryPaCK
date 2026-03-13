# Visionary Suite — PRD

## Original Problem Statement
Full-stack SaaS platform for creative content generation. Story → Video was unreliable (blank pages, timeouts, stalled progress). Required complete architectural redesign.

## P0 Architecture Redesign — Story → Video Pipeline (2026-03-13)

### Architecture
```
User clicks "Generate Video"
  → POST /api/pipeline/create (<200ms)
  → pipeline_jobs DB doc created (status=QUEUED)
  → Job enqueued to asyncio.Queue
  → One of 3 dedicated workers picks job
  → Executes stages:
     SCENES → IMAGES(parallel×3) → VOICES(parallel×4) → RENDER → UPLOAD(R2+verify)
  → Frontend polls GET /status/{job_id} every 3s
  → Shows filmstrip thumbnails as scenes complete
  → Final: video player + download
```

### Performance
| Stage | Time |
|-------|------|
| Job creation | 131ms |
| Scenes | 7.9s |
| Images | 49.6s |
| Voices | 10.9s |
| Render | 14.7s |
| Upload | 6.1s |
| **Total** | **89.3s** |

### Testing Summary (Iterations 148-150)
- 5 consecutive single-user runs: ALL COMPLETED
- 3 concurrent users: ALL COMPLETED (211-278s)
- Resume from checkpoint: VERIFIED (28s recovery)
- Refresh recovery: VERIFIED (auto-detects active job)
- Credit integrity: VERIFIED (no duplicates, refunds work)
- No blank page: VERIFIED (body > 500 chars at all times)
- Video download: VERIFIED (HTTP 200, video/mp4, R2 CDN)
- Platform audit: Login, Dashboard, Story Video, Projects — all working

### Files
- NEW: `/app/backend/services/pipeline_engine.py`
- NEW: `/app/backend/services/pipeline_worker.py`
- NEW: `/app/backend/routes/pipeline_routes.py`
- NEW: `/app/frontend/src/pages/StoryVideoPipeline.js`
- MOD: `/app/backend/server.py`
- MOD: `/app/frontend/src/App.js`

### Production Deployment Status
⚠️ Production API at www.visionary-suite.com returns 502 Bad Gateway.
Pipeline code verified on preview, needs production deployment.

### Backlog
- P0: Production deployment + verification
- P1: WebSocket progress (replace polling)
- P1: Worker auto-scaling
- P2: Email notification when video ready
- P2: 5-10 concurrent user stress test
- P3: GPU-accelerated rendering
