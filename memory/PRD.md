# Visionary Suite - Product Requirements Document

## Original Problem Statement
Rebuild Visionary Suite into an **addictive story-driven viral platform** with compulsion loops: enter → engage → return → share → grow. Achieve K-factor > 0.5. Build a private, self-hosted Story-to-Video pipeline with moving clips (not slideshow), character continuity, and strict credit gating.

## Architecture
- **Frontend**: React + Tailwind CSS + Shadcn UI
- **Backend**: FastAPI + MongoDB + Redis
- **AI (Cloud)**: OpenAI GPT-4o-mini via Emergent LLM Key (planning proxy)
- **AI (Self-Hosted Target)**: Qwen2.5-14B-Instruct, Wan2.1-T2V/I2V-14B, Kokoro-82M
- **Payments**: Cashfree | **Auth**: JWT + Google Auth | **Storage**: Cloudflare R2 | **Email**: Resend

## Implemented Phases

### Phase 1-5.5: Complete Growth Loop
- Zero-friction entry, compulsion loops, retention engine, K-factor engine, attribution, email nudges

### Phase 6: Compete + Social Proof (2026-03-25)
- Compete Mechanics (trending, most continued, fastest growing character)
- Animated Social Proof (real viewer counts with pulse)
- Force Share Gate (share OR continue after generation)
- K-Factor Admin Dashboard (viral coefficient, funnel, top content)

### Phase 7: Content Seeding Engine (2026-03-25)
- AI story hook generation (GPT-4o-mini) with HOOK→BUILD→CLIFFHANGER format
- Quality filtering, 5 categories, social media scripts, auto-publish pipeline
- Admin control panel at /app/admin/content-engine

### Phase 8: Private Story-to-Video Engine (2026-03-25 — LATEST)
- **11-step pipeline**: Credit check → Job → Plan → Character → Motion → Keyframes → Clips → Audio → Assembly → Validate → Ready
- **Structured schemas**: EpisodePlan, SceneMotionPlan, CharacterContinuityPackage — no free-form text
- **Truth-based states**: INIT → PLANNING → ... → READY / PARTIAL_READY / FAILED
- **Atomic credit gating**: 21 credits/job, pre-flight check, refund on failure
- **Safety**: Copyright blocking, celebrity blocking, rate limits, abuse detection
- **Universal negative prompt**: Non-removable, applied to all visual generation
- **Continuity validation**: Asset existence, character drift, style drift checks
- **Model adapters**: Planning (Qwen/GPT), Video (Wan2.1), TTS (Kokoro), Assembly (FFmpeg)
- **Admin controls**: Pipeline health, job management, retry failed jobs
- **GPU worker ready**: Set WAN_T2V_ENDPOINT, WAN_I2V_ENDPOINT, KEYFRAME_GEN_ENDPOINT, KOKORO_TTS_ENDPOINT to connect

## Self-Hosted Stack Spec
Full deployment guide at `/app/memory/SELF_HOSTED_STACK.md`

## API Endpoints (Story Engine)
- `GET /api/story-engine/credit-check` — Pre-flight cost check
- `POST /api/story-engine/create` — Create job + run pipeline
- `GET /api/story-engine/status/{job_id}` — Poll progress
- `GET /api/story-engine/my-jobs` — User's jobs
- `GET /api/story-engine/chain/{chain_id}` — Story chain episodes
- `GET /api/story-engine/admin/pipeline-health` — GPU status + stats
- `GET /api/story-engine/admin/jobs` — All jobs with filters
- `POST /api/story-engine/admin/retry/{job_id}` — Retry failed jobs

## Prioritized Backlog
### P0 (Deploy)
- Connect GPU workers (Wan2.1, Kokoro) to make pipeline produce real videos
- Domain verification for Resend email delivery

### P1 (Growth)
- A/B test hook text variations
- Character-driven auto-share prompts

### P2 (Platform)
- Story Chain leaderboard
- Admin WebSocket upgrade
- Mobile app wrapper

## Key Files
- `/app/backend/services/story_engine/` — Full engine (schemas, state machine, pipeline, adapters, safety)
- `/app/backend/routes/story_engine_routes.py` — API endpoints
- `/app/backend/routes/content_engine.py` — Content seeding engine
- `/app/backend/routes/compete_routes.py` — Trending + live viewers
- `/app/frontend/src/components/ForceShareGate.js` — Forced share modal
- `/app/frontend/src/components/TrendingCompete.js` — Compete UI
- `/app/frontend/src/pages/ContentEngine.js` — Admin content panel
