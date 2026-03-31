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
- **Reused stages** show SkipForward icon + "Reused" badge + "Carried from previous video"

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

## P1.1 Continue/Remix Optimization (BUILT Mar 31 2026)

### Dependency-Aware Checkpoint Reuse
When user remixes or continues a video, the system analyzes what changed and only reruns affected stages.

### Dependency Graph
```
story_text → PLANNING → all downstream
style_id → KEYFRAMES, CLIPS, ASSEMBLY (skips planning, character, motion, audio)
voice_preset → AUDIO, ASSEMBLY (skips planning, character, motion, keyframes, clips)
age_group → all downstream
```

### Reuse Modes
- **style_remix**: 57% stages reused (skip planning, character, motion, audio)
- **voice_remix**: 71% stages reused (skip planning, character, motion, keyframes, clips)
- **continue**: Character continuity inherited, but new planning needed
- **full_reuse**: 100% (no changes detected)

### Key Functions
- `analyze_reuse(parent_job, new_params)` — determines what can be reused
- `apply_reuse_checkpoints(job_id, parent_job_id, new_params)` — copies data, advances state
- `process_next_stage()` — checks `reuse_info.reused_stages` and skips already-done stages

### API Endpoints
- `GET /api/story-engine/analyze-reuse?parent_job_id=X&animation_style=Y` — preview reuse analysis
- `POST /api/story-engine/create` — now returns `reuse_mode`, `stages_reused`, `stages_to_generate`
- `GET /api/story-engine/status/{job_id}` — now returns `reuse_info` field

## P1.2 Quality Mode Strategy (BUILT Mar 31 2026)

### Three Modes
| Mode | Max Scenes | ETA | Use Sora | Image Quality |
|------|-----------|-----|----------|---------------|
| Fast | 3 | 1-2 min | No | Standard |
| Balanced | 5 | 2-4 min | Yes | Standard |
| High Quality | 7 | 4-8 min | Yes | HD |

### Implementation
- `quality_mode` field on job document
- `quality_config` dict stored with full mode settings
- Planning LLM prompt adjusted with `min_scenes`/`max_scenes` params
- Deterministic splitter also respects `max_scenes`
- Frontend selector with 3 buttons: Fast, Balanced, High Quality
- ETA and messaging differ by mode truthfully

### API
- `GET /api/story-engine/quality-modes` — returns all modes with properties

## P1.3 Analytics & Observability (BUILT Mar 31 2026)

### Admin Analytics Endpoint
`GET /api/story-engine/admin/generation-analytics?days=30`

Returns:
- **totals**: total_jobs, completed, partial_ready, failed, completion_rate, failure_rate
- **retries**: total_retries, jobs_with_retries, retry_rate
- **reuse**: total_reuse_jobs, fresh_jobs, style_remixes, voice_remixes, continues
- **quality_modes**: fast, balanced, high_quality counts
- **timing**: avg_fresh_completion_seconds, avg_reuse_completion_seconds, speedup_percent

## Test Credentials
- Test User: test@visionary-suite.com / Test@2026#
- Admin User: admin@creatorstudio.ai / Cr3@t0rStud!o#2026

## Key Files
- `/app/backend/services/story_engine/pipeline.py` — Stage orchestrator + reuse logic
- `/app/backend/services/story_engine/state_machine.py` — State transitions, heartbeat
- `/app/backend/services/story_engine/schemas.py` — JobState, ErrorCode enums
- `/app/backend/services/story_engine/cost_guard.py` — Budget enforcement
- `/app/backend/services/story_engine/recovery_daemon.py` — Watchdog
- `/app/backend/services/story_engine/adapters/planning_llm.py` — Multi-level fallback + max_scenes
- `/app/backend/routes/story_engine_routes.py` — All story engine endpoints
- `/app/backend/routes/notification_routes.py` — Notify subscribe endpoint
- `/app/frontend/src/pages/StoryVideoPipeline.js` — Full studio UI
- `/app/frontend/src/components/ProgressiveGeneration.js` — Rich status page + reuse display

## Completed
- [x] CDN bypass fix + Blurhash system
- [x] Netflix autoplay preview (singleton, Safari-safe)
- [x] Behavior engine (session memory, momentum, recovery, variable rewards, infinite scroll)
- [x] Retention Analytics Dashboard (5 key metrics, trends, device segmentation)
- [x] Rate Limit UX Fix (Mar 30 2026)
- [x] Pipeline Architecture Overhaul (Mar 30 2026) — Stage orchestrator, heartbeat, recovery daemon, budget guard, multi-level fallback, structured error codes, per-stage failure states, idempotent refund
- [x] Universal Generation Status Page (Mar 31 2026) — ETA + elapsed time, safe-to-leave, wired notify, explore while waiting, completion routing
- [x] P1.1 Continue/Remix Optimization (Mar 31 2026) — Dependency-aware checkpoint reuse, 4 reuse modes, stage skip logic. 16/16 tests passed.
- [x] P1.2 Quality Mode Strategy (Mar 31 2026) — Fast/Balanced/High Quality with truthful ETAs and scene limits. 21/21 tests passed.
- [x] P1.3 Analytics & Observability (Mar 31 2026) — Admin analytics endpoint with completion, retry, reuse, quality, timing stats.

## Current Phase: P1 OPTIMIZATION COMPLETE

## Upcoming (Next Priority)
- (P1) Notification Center Improvements — notification history, read/unread states, deep links
- (P1) A/B test hook text variations on public pages
- (P1) Character-driven auto-share prompts after creation

## Future / Backlog
- (P2) Wait-page mini-games/puzzles/trivia (deferred per user instruction)
- (P2) Remix Variants on share pages
- (P2) Admin dashboard WebSocket upgrade for live updates
- (P2) Story Chain leaderboard
- (P2) General UI polish and style preset preview thumbnails
- (P2) Separate background workers from API server (Celery/Redis) for scale
