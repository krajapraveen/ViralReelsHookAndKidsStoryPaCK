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
- Detects stale heartbeats per stage thresholds
- Requeues or marks terminal failure + credit refund

### Runtime Budget Guard
- `enforce_runtime_budget()` called before every external API call
- Raises `BudgetExceededError` if projected cost exceeds 130% of estimate

### Credit Refund
- Idempotent: checks `credits_refunded > 0` before processing
- Atomic: sets flag BEFORE refunding to prevent double-refund

### Structured Error Codes
```
BUDGET_EXCEEDED_PRECHECK | BUDGET_EXCEEDED_RUNTIME | MODEL_TIMEOUT
MODEL_INVALID_RESPONSE | SCENE_GENERATION_FAILED | IMAGE_GENERATION_FAILED
TTS_GENERATION_FAILED | RENDER_FAILED | JOB_HEARTBEAT_EXPIRED
WORKER_CRASH | UNKNOWN_STAGE_FAILURE | INSUFFICIENT_CREDITS
```

### User Controls
- `POST /api/story-engine/retry/{job_id}` — Retry from failed stage
- `POST /api/story-engine/cancel/{job_id}` — Cancel + refund

## Universal Generation Status Page (BUILT Mar 31 2026)

### ETA + Elapsed Time
- Backend computes elapsed_seconds from created_at
- ETA derived from progress rate (progress / elapsed_seconds)
- Updates every 4 seconds via polling

### Safe-to-Leave Messaging
- "You can safely leave this page — we'll notify you when it's ready"
- Shield icon, blue accent, positioned below progress hero

### Wired Notify System
- `POST /api/notifications/generation/{job_id}/subscribe` — stores preference
- Pipeline calls `_send_completion_notification()` on finalize/fail
- Uses existing NotificationService for in-app notifications
- Always notifies on failure, only on success if user opted in

### What's Happening Now
- Stage-by-stage explanation with checkmarks for completed stages
- Active stage highlighted with spinner
- Descriptions: "Breaking down the narrative into scenes", etc.

### Explore While Waiting
- Rotating inspirational quotes (12s rotation, 8 quotes)
- Tool cards: My Space, Create New, Templates, Dashboard, Characters, Browse
- Clean grid layout, hover effects

### Completion Experience
- Full Preview button with Eye icon
- Export Video button with Film icon
- Scene cards with progressive disclosure
- Credits refunded confirmation for failed jobs
- Retry/Cancel buttons for per-stage failures

## Test Credentials
- Test User: test@visionary-suite.com / Test@2026#
- Admin User: admin@creatorstudio.ai / Cr3@t0rStud!o#2026

## Key Files
- `/app/backend/services/story_engine/pipeline.py` — Stage orchestrator
- `/app/backend/services/story_engine/state_machine.py` — State transitions, heartbeat
- `/app/backend/services/story_engine/schemas.py` — JobState, ErrorCode enums
- `/app/backend/services/story_engine/cost_guard.py` — Budget enforcement
- `/app/backend/services/story_engine/recovery_daemon.py` — Watchdog
- `/app/backend/services/story_engine/adapters/planning_llm.py` — Multi-level fallback
- `/app/backend/routes/story_engine_routes.py` — Retry, cancel, status APIs
- `/app/backend/routes/notification_routes.py` — Notify subscribe endpoint
- `/app/frontend/src/pages/StoryVideoPipeline.js` — Retry/Cancel UI, PostGenPhase
- `/app/frontend/src/components/ProgressiveGeneration.js` — Rich status page

## Completed
- [x] CDN bypass fix + Blurhash system
- [x] Netflix autoplay preview (singleton, Safari-safe)
- [x] Behavior engine (session memory, momentum, recovery, variable rewards, infinite scroll)
- [x] Retention Analytics Dashboard (5 key metrics, trends, device segmentation)
- [x] Rate Limit UX Fix (Mar 30 2026)
- [x] Pipeline Architecture Overhaul (Mar 30 2026) — Stage orchestrator, heartbeat, recovery daemon, budget guard, multi-level fallback, structured error codes, per-stage failure states, idempotent refund. 30/30 tests passed.
- [x] Universal Generation Status Page (Mar 31 2026) — ETA + elapsed time, safe-to-leave, wired notify system, What's Happening section, Explore While Waiting (quotes + tool cards), completion routing with Watch/Remix/Share/Download, retry/cancel controls. 13/13 backend + frontend verified.

## Current Phase: STATUS PAGE COMPLETE
- Pipeline architecture rebuilt for fault tolerance
- Rich generation status page eliminates dead spinner UX
- Notify system wired end-to-end

## Upcoming (Next Session Priority)
- (P0) Continue/Remix optimization — reuse prior artifacts for faster generation
- (P1) Cost ledger per stage — track actual vs estimated costs
- (P1) Admin job monitoring dashboard — failure rates, stuck jobs, costs
- (P1) Notification center/history — list, mark-read, deep links
- (P1) Quality mode toggle (Fast/Balanced/High Quality)
- (P2) Mini-games/puzzles/trivia for waiting page
- (P2) Hook + autoplay combo optimization
- (P2) Character-driven auto-share prompts
- (P2) Story Chain leaderboard
- (P2) WebSockets for admin dashboard live updates
