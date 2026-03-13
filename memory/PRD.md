# Visionary-Suite PRD

## Original Problem Statement
The "Story To Video" feature was unstable, slow, and unreliable in production. The system was re-architected into a durable, async, stage-based job pipeline. After deployment, production experienced persistent crash loops (520 errors) and OOM kills due to ffmpeg memory exhaustion. After fixing OOM, a full platform audit was requested.

## Architecture
- **Frontend**: React (CRA with craco) on port 3000
- **Backend**: FastAPI on port 8001 
- **Database**: MongoDB (creatorstudio_production)
- **Storage**: Cloudflare R2
- **Payment**: Cashfree
- **LLM**: OpenAI GPT-4o-mini, GPT Image 1, OpenAI TTS, Sora 2, Gemini (storybook images)
- **Video Processing**: ffmpeg (system dependency via apt-packages.txt)

## Features & Status (All Verified 2026-03-13)

### Core Features
| Feature | Route | API Prefix | Credit Cost | Deduction Type | Status |
|---------|-------|-----------|-------------|----------------|--------|
| Reel Generator | /app/reel-generator | /api/generate/reel | 10 | Upfront | ✅ |
| Kids Story Pack | /app/story-generator | /api/generate/story | 10 | Upfront | ✅ |
| Photo to Comic | /app/photo-to-comic | /api/photo-to-comic/* | 15-45 | Deferred | ✅ |
| GIF Maker | /app/gif-maker | /api/gif-maker/* | 10+15dl | Deferred | ✅ |
| Comic Storybook | /app/comic-storybook | /api/comic-storybook/* | 10+/page+20dl | Deferred | ✅ |
| Story→Video | /app/story-video-studio | /api/pipeline/* | 50-120 | Upfront | ✅ |

### Credit Integrity Audit Results
- **Upfront deduction** (Reel, Story, Pipeline): Exact amount deducted immediately on creation ✅
- **Deferred deduction** (Photo-to-Comic, GIF, Storybook): Deducted after background processing completes ✅
- **Insufficient credits rejection**: All features correctly reject and prevent generation ✅
- **No double-deductions detected** ✅
- **Refund on failure**: Pipeline refunds credits when job fails or stale on restart ✅

### Production-Safe Render Stage (P0 Fix)
- Sequential scene rendering, single-threaded ffmpeg (-threads 1)
- 640x360 @ 10fps, CRF 35, maxrate/bufsize 400k
- -nostdin, -loglevel error auto-injected
- gc.collect() after each scene, aggressive temp cleanup
- Concat step also single-threaded with matching low-memory settings

### Verified Render Benchmarks (Preview)
| Metric | Value |
|--------|-------|
| Per-scene render | 1.3-2.4s |
| Full render (3 scenes) | 4.9-7.4s |
| Full pipeline | 78-86s |
| Video size | 0.5-0.6MB |
| 5 consecutive runs | 5/5 ✅ |
| 3 concurrent runs | 3/3 ✅ |

### Testing Summary
| Test | Result |
|------|--------|
| iteration_153: Story Video Pipeline | 100% (13/13 backend) |
| iteration_154: Full Platform Audit | 100% (18/18 backend, 9/9 frontend) |
| Credit integrity (manual) | All 6 features verified |
| Insufficient credits | All features reject correctly |
| Stale job recovery + refund | ✅ |

## Key Files
- `/app/backend/services/pipeline_engine.py` - Pipeline + render logic
- `/app/backend/services/pipeline_worker.py` - Worker management
- `/app/backend/routes/pipeline_routes.py` - Pipeline API
- `/app/backend/routes/generation.py` - Reel + Story API
- `/app/backend/routes/photo_to_comic.py` - Photo to Comic API
- `/app/backend/routes/gif_maker.py` - GIF Maker API
- `/app/backend/routes/comic_storybook.py` - Storybook API
- `/app/backend/routes/credits.py` - Credit system
- `/app/frontend/src/App.js` - All route definitions

## Pending
- P1: SendGrid email (blocked on user's plan upgrade)

## Backlog
- P2: WebSocket real-time progress (replace polling)
- P2: Worker auto-scaling
- P2: Email notifications on completion
- P3: Delete obsolete old Story→Video code
- P3: GPU-accelerated rendering

## Test Credentials
- UAT: test@visionary-suite.com / Test@2026#
- Admin: admin@creatorstudio.ai / Cr3@t0rStud!o#2026
