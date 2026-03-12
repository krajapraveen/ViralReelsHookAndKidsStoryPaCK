# Visionary Suite - PRD

## Original Problem Statement
Full-stack SaaS platform for creative content generation with monitoring, security, and admin analytics.

## LATEST UPDATE: 2026-03-12 — P0 Story To Video Performance Optimization

### Performance Benchmark Results

| Stage | Before (Sequential) | After (Parallel) | Improvement |
|-------|-------------------|------------------|-------------|
| Scene Generation (LLM) | ~15-20s | **7.0s** | 2x faster (gpt-4o-mini) |
| Image Generation | ~90-150s (sequential) | **107.8s parallel** | Images+Voices run simultaneously |
| Voice Generation | ~20-30s (after images) | **Included above** | Eliminated wait time |
| Video Assembly | ~30-45s (scene-by-scene + watermark re-encode) | **12.0s** | 3x faster (single-pass) |
| R2 Upload | ~10-15s (blocking) | **4.1s** | Async, non-blocking |
| **TOTAL** | **~180-300s (3-5 min)** | **~105-131s** | **50-60% faster** |

### Optimizations Applied
1. **Parallel Image + Voice Generation** — Run ALL images AND voices simultaneously via asyncio.gather (biggest win: saves 20-30s)
2. **Semaphore-controlled concurrency** — Max 4 parallel images, 6 parallel voices to prevent API overload
3. **Single-pass ffmpeg rendering** — Encode per scene → concat with watermark baked in (eliminates separate re-encode)
4. **Parallel scene encoding** — Standard renderer now encodes scenes concurrently (3 at a time)
5. **Async R2 upload** — Non-blocking cloud storage upload
6. **Granular progress tracking** — Real-time updates: scene gen → image gen → voice gen → rendering → uploading
7. **Credit refund on failure** — Auto-refund if pipeline fails

### Remaining Bottleneck
- **GPT Image 1 API**: 20-50s per image (82% of total time). This is an external API limitation.
- Mitigation: Images run in parallel so total image time = slowest single image, not sum of all

### Test Results (Iteration 146)
- 28/28 pytest tests PASSED
- Frontend regression: All pages working (GIF maker, blog, dashboard, payment history)
- Copyright compliance: Blocks trademarked characters
- Video output: Valid H.264+AAC on R2 CDN

## Previous Fixes (Same Session)
- P0: Infinite toast loop fix
- P0: Rating feedback fix
- P0: Promo videos (4/4 available)
- Payment History fix, Blog posts, Blog nav link

## Architecture
- Backend: FastAPI + MongoDB + Cashfree PG + Emergent LLM
- Video Pipeline: GPT-4o-mini (scenes) → GPT Image 1 (images) + TTS (voices) [PARALLEL] → ffmpeg (assembly) → R2 CDN
- Frontend: React + Shadcn UI

## Backlog
- P0: Replace Deployment to production
- P1: LLM timeout retry logic (tenacity)
- P1: Full system audit on production
- P2: Job queue architecture, file cleanup, monitoring
