# Visionary Suite - PRD

## Original Problem Statement
Full-stack SaaS platform for creative content generation with monitoring, security, and admin analytics.

## LATEST UPDATE: 2026-03-12 — P0 Blank Page Bug Fix + Image Generation Fix

### Issue 1: Blank Page After Clicking Generate (P0)
**Root Cause**: Missing ErrorBoundary around StoryVideoStudio component. Any unhandled React error during render would unmount the entire component tree, resulting in a blank dark page. Additionally, unsafe property access on `project.promptPack.stats.*` without optional chaining could cause crashes on Step 4.

**Fix Applied**:
1. ErrorBoundary wrapping StoryVideoStudio in App.js (catches all render errors)
2. Component-level error recovery UI (Try Again + Dashboard buttons)
3. Null-safe access: `project?.promptPack?.stats?.total_scenes` etc.
4. `AlertCircle` icon import added for error UI
5. Polling fail-count limits (max 10 retries before graceful failure)
6. `componentError` state prevents blank page in edge cases

**Stability Proof**: 6 consecutive Generate Scenes runs with different stories/styles — ALL passed, page remained visible throughout, body text > 1000 chars at all times.

### Issue 2: Image Generation Timeout (P0)
**Root Cause**: Image generation endpoint ran synchronously for 90-120+ seconds, exceeding Kubernetes ingress ~60s timeout. Frontend received empty/error response.

**Fix Applied**:
1. Converted image generation to background task + polling (29ms response time)
2. Converted voice generation to background task + polling
3. Smart prompt truncation (3800 char cap, sentence-boundary preserving)
4. Both standard and fast pipelines fixed consistently
5. Single credit deduction at start, per-scene refund on failure, full refund on pipeline crash

**Stability Proof**: 5 consecutive image generation runs — ALL passed (27+ images total).

### Test Results
- **Iteration 148**: 6 Generate Scenes + 1 Image Gen = ALL PASSED
- **Iteration 147**: 16/16 backend tests PASSED

## Performance Benchmark
| Stage | Before | After | Improvement |
|-------|--------|-------|-------------|
| Scene Generation (LLM) | ~15-20s | **7.0s** | 2x faster |
| Image Generation | ~90-150s | **107.8s parallel** | Background task |
| Video Assembly | ~30-45s | **12.0s** | 3x faster |

## Key API Endpoints
- `POST /api/story-video-studio/generation/images` → Returns job_id (background)
- `GET /api/story-video-studio/generation/images/status/{job_id}` → Poll progress
- `POST /api/story-video-studio/generation/voices` → Returns job_id (background)
- `GET /api/story-video-studio/generation/voices/status/{job_id}` → Poll progress

## Files Changed (This Session)
- `/app/frontend/src/App.js` — ErrorBoundary import + wrapping
- `/app/frontend/src/pages/StoryVideoStudio.js` — Error recovery UI, null-safe access, polling with limits, AlertCircle import
- `/app/backend/routes/story_video_generation.py` — Background tasks, smart truncation
- `/app/backend/routes/story_video_fast.py` — Smart prompt truncation

## Backlog
- P0: Deploy to production + verify on visionary-suite.com
- P1: Concurrent user testing (5-10 users)
- P1: LLM timeout retry logic (tenacity)
- P1: Full system audit on production
- P2: Job queue architecture, file cleanup, monitoring
- P2/P3: Consolidate standard + fast pipelines
