# Visionary Suite - PRD

## Original Problem Statement
Full-stack SaaS platform for creative content generation with monitoring, security, and admin analytics.

## LATEST UPDATE: 2026-03-12 — P0 Story To Video Image Generation Bug Fix

### Root Cause (PROVEN)
The image generation endpoint (`POST /api/story-video-studio/generation/images`) ran **synchronously** for 90-120+ seconds (generating 5-6 images, each taking ~20s via OpenAI GPT Image 1 API, plus R2 uploads). The Kubernetes ingress has a ~60s request timeout. When the endpoint exceeded this timeout, the HTTP response was dropped by the proxy, causing the frontend to interpret the timeout as a failure and display "Failed to generate images. Credits have been refunded." **In reality, images WERE generated successfully in the background, but the response never reached the client.**

### Root Cause Evidence
- Backend logs show all 6 images generated successfully in 118,458ms
- Curl to external URL returned empty after ~60s (ingress timeout)
- Same request via localhost:8001 returned full success response
- No prompt length issues — prompts ranged 531-695 chars (well within API limits)

### Fix Applied
1. **Converted image generation to background task + polling** (same pattern as video assembly)
   - `POST /images` → Returns instantly with `job_id` (29ms measured)
   - `GET /images/status/{job_id}` → Returns real-time progress (0-100%)
   - Background task processes images, updates job doc in `generation_jobs` collection
2. **Converted voice generation to background task + polling** (same pattern)
   - `POST /voices` → Returns instantly with `job_id`
   - `GET /voices/status/{job_id}` → Returns real-time progress
3. **Smart prompt truncation** (defense-in-depth)
   - `_truncate_prompt_smart()` caps prompts at 3800 chars
   - Preserves sentence boundaries and essential scene meaning
   - Applied to both standard and fast pipelines
4. **Frontend polling integration**
   - `generateImages()` → submit → poll `pollImageGenerationStatus()` every 3s
   - `generateVoices()` → submit → poll `pollVoiceGenerationStatus()` every 3s
   - Shows progress indicator during processing
5. **Credit refund integrity**
   - Single deduction at start (before background task)
   - Per-scene refund on individual scene failure
   - Full refund on total pipeline failure
   - Refund transactions logged with `type: "refund"`

### Stability Test Results (5 Consecutive Runs)
| Run | Scenes | Result | Endpoint Response Time |
|-----|--------|--------|----------------------|
| 1 | 6 | 6/6 SUCCESS | N/A (pre-fix) |
| 2 | 5 | 5/5 SUCCESS | <2s |
| 3 | 5 | 5/5 SUCCESS | <2s |
| 4 | 5 | 5/5 SUCCESS (testing agent) | <2s |
| 5 | 6 | 6/6 SUCCESS | 29ms |

### Test Results (Iteration 147)
- 16/16 pytest tests PASSED
- Frontend verified: polling flow works correctly
- Credit integrity verified: single deduction, proper refunds

## Performance Benchmark (Previous Session)
| Stage | Before | After | Improvement |
|-------|--------|-------|-------------|
| Scene Generation (LLM) | ~15-20s | **7.0s** | 2x faster |
| Image Generation | ~90-150s | **107.8s parallel** | Images+Voices simultaneous |
| Video Assembly | ~30-45s | **12.0s** | 3x faster (single-pass) |
| R2 Upload | ~10-15s | **4.1s** | Async |
| **TOTAL** | **~180-300s** | **~105-131s** | **50-60% faster** |

## Previous Fixes (Same Session History)
- P0: Infinite toast loop fix (useRef for polling)
- P0: Rating feedback fix
- P0: Promo videos (4/4 available)
- Payment History fix, Blog posts, Blog nav link

## Architecture
- Backend: FastAPI + MongoDB + Cashfree PG + Emergent LLM
- Video Pipeline: GPT-4o-mini (scenes) → GPT Image 1 (images) + TTS (voices) [PARALLEL] → ffmpeg (assembly) → R2 CDN
- Frontend: React + Shadcn UI
- New: `generation_jobs` collection for background task tracking

## Key API Endpoints
- `POST /api/story-video-studio/generation/images` → Returns job_id (background task)
- `GET /api/story-video-studio/generation/images/status/{job_id}` → Poll progress
- `POST /api/story-video-studio/generation/voices` → Returns job_id (background task)
- `GET /api/story-video-studio/generation/voices/status/{job_id}` → Poll progress
- `POST /api/story-video-studio/generation/video/assemble` → Returns job_id
- `GET /api/story-video-studio/generation/video/status/{job_id}` → Poll progress

## Backlog
- P0: Production deployment + verification on visionary-suite.com
- P1: Concurrent user testing (5-10 users)
- P1: LLM timeout retry logic (tenacity)
- P1: Full system audit on production
- P2: Job queue architecture, file cleanup, monitoring
- P2/P3: Consolidate standard + fast pipelines
