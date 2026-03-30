# Story Universe Engine — Product Requirements Document

## Original Problem Statement
Build a "Story Universe Engine" — a full-stack AI creator suite with a behavior-driven growth engine, monetization, and viral sharing. Core mandate: Netflix-level media delivery, deterministic personalization, addictive hook system, and a complete dopamine loop.

## Core Architecture
- Frontend: React (CRA + Craco) on port 3000
- Backend: FastAPI on port 8001
- Database: MongoDB
- Storage: Cloudflare R2 (images via CDN, videos via same-origin proxy for CORS safety)
- Payments: Cashfree
- AI: OpenAI GPT-4o-mini, Sora 2, TTS + Gemini 3 via Emergent LLM Key

## Pipeline Architecture (REBUILT Mar 30 2026)

### Stage Orchestrator
Replaced monolithic `run_pipeline()` with independently retryable stages:
```
INIT → PLANNING → BUILDING_CHARACTER_CONTEXT → PLANNING_SCENE_MOTION 
→ GENERATING_KEYFRAMES → GENERATING_SCENE_CLIPS → GENERATING_AUDIO 
→ ASSEMBLING_VIDEO → VALIDATING → READY / PARTIAL_READY
```

### Per-Stage Failure States
```
FAILED_PLANNING | FAILED_IMAGES | FAILED_TTS | FAILED_RENDER | FAILED
```

### Multi-Level Scene Generation Fallback
```
Level 0: GPT-4o-mini, full prompt, temp 0.7
Level 1: GPT-4o-mini, reduced prompt, temp 0.4
Level 2: gemini-2.0-flash, reduced prompt, temp 0.3
Level 3: Deterministic text splitter (no LLM)
```

### Recovery Daemon
- Runs every 2 minutes
- Detects stale heartbeats per stage
- Requeues or marks terminal failure + credit refund

### Runtime Budget Guard
- `enforce_runtime_budget()` called before every external API call
- Raises `BudgetExceededError` if projected cost exceeds 130% of estimate
- Hard stop prevents cost explosion

### Credit Refund
- Idempotent: checks `credits_refunded > 0` before processing
- Atomic: sets flag BEFORE refunding to prevent double-refund
- Triggered on any terminal failure

### Structured Error Codes
```
BUDGET_EXCEEDED_PRECHECK | BUDGET_EXCEEDED_RUNTIME | MODEL_TIMEOUT
MODEL_INVALID_RESPONSE | SCENE_GENERATION_FAILED | IMAGE_GENERATION_FAILED
TTS_GENERATION_FAILED | RENDER_FAILED | JOB_HEARTBEAT_EXPIRED
WORKER_CRASH | UNKNOWN_STAGE_FAILURE | INSUFFICIENT_CREDITS
```

### User Controls (Retry/Cancel)
- `POST /api/story-engine/retry/{job_id}` — Retry from failed stage
- `POST /api/story-engine/cancel/{job_id}` — Cancel + refund

### Honest UI Status
- Shows real stage: "Generating scenes", "Retrying (2/3)", "Recovering stuck job"
- Shows retry/cancel buttons when job is in per-stage failure state
- Shows credit refund confirmation when applicable

## Behavior Engine (THE ADDICTION LOOP)
```
Autoplay → Hook → Preview → Click → Reward → Personalization → Infinite Scroll → Variable Reward → Repeat
```

### Session Memory
- `momentum_score`: 0.0-10.0
- `last_5_clicked_categories`, `last_3_hooks_clicked`, `consecutive_skips`
- Recovery at 3+ skips, variable reward spikes at random 3-9 intervals

## Rate Limit UX (Fixed)
- Concurrency cap enforced, friendly messaging
- "All rendering slots are busy" with active jobs list + "View Progress"
- Contextual help tips in error messages

## Test Credentials
- Test User: test@visionary-suite.com / Test@2026#
- Admin User: admin@creatorstudio.ai / Cr3@t0rStud!o#2026

## Key Files
- `/app/backend/services/story_engine/pipeline.py` — Stage orchestrator, process_next_stage, refund
- `/app/backend/services/story_engine/state_machine.py` — State transitions, heartbeat, progress
- `/app/backend/services/story_engine/schemas.py` — JobState, ErrorCode, PER_STAGE_FAILURE_STATES
- `/app/backend/services/story_engine/cost_guard.py` — Budget enforcement
- `/app/backend/services/story_engine/recovery_daemon.py` — Watchdog for stuck jobs
- `/app/backend/services/story_engine/adapters/planning_llm.py` — Multi-level fallback
- `/app/backend/routes/story_engine_routes.py` — Retry, cancel, status endpoints
- `/app/frontend/src/pages/StoryVideoPipeline.js` — Honest UI, retry/cancel controls
- `/app/frontend/src/components/ProgressiveGeneration.js` — Real-time retry/recovery display

## Completed
- [x] CDN bypass fix + Blurhash system
- [x] Netflix autoplay preview (singleton, Safari-safe)
- [x] Behavior engine (session memory, momentum, recovery, variable rewards, infinite scroll)
- [x] Retention Analytics Dashboard (5 key metrics, trends, device segmentation)
- [x] Rate Limit UX Fix (Mar 30 2026)
- [x] **Pipeline Architecture Overhaul** (Mar 30 2026): Replaced monolithic run_pipeline() with independently retryable stage orchestrator. Added heartbeat + recovery daemon, runtime budget guard, multi-level scene fallback (primary → retry → fallback model → deterministic splitter), structured error codes, per-stage failure states, idempotent credit refund, honest UI status with retry/cancel controls. 30/30 tests passed.

## Current Phase: RELIABILITY VALIDATED
- Pipeline architecture rebuilt for fault tolerance
- Recovery daemon active
- Observe real user pipeline completion rates

## Upcoming (After Reliability Validation)
- (P0) Monitor real pipeline runs — verify recovery daemon catches stale jobs
- (P1) Cost ledger per stage (track actual vs estimated costs)
- (P1) Admin job monitoring dashboard (failure rates, stuck jobs, costs)
- (P1) Backfill hooks for existing stories
- (P2) Hook + autoplay combo optimization
- (P2) Character-driven auto-share prompts
- (P2) Story Chain leaderboard
- (P2) WebSockets for admin dashboard live updates
