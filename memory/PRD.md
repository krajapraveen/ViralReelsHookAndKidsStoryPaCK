# Photo to Comic — AI Creator Suite PRD

## Original Problem Statement
Build a "Smart Repair Pipeline" for an AI creator suite (Photo to Comic). Highest priority: Failure Masking — users must NEVER see raw failures. If generation fails, deterministic fallback (Guaranteed Output) ensures the user always gets a comic.

## Current Status: P0 FIX v4 — COMPLETED & VERIFIED (Apr 3, 2026)
- Fixed AI Generation SDK crash (broken import path in panel_orchestrator.py)
- Fixed invalid Tier 3/4 model names (gemini-2.0-flash-preview-image-generation → gemini-3.1-flash-image-preview)
- Added worker performance telemetry to panel_orchestrator.py and job_orchestrator.py
- All 16 backend tests pass, frontend renders without blank screen

## Root Causes Found & Fixed

### RC1: Panel Persistence Bug (Dead-End Screen) — FIXED (earlier)
- Guaranteed output panels generated+uploaded to R2 but DB save was at END of function
- **Fix:** Panels saved to DB IMMEDIATELY after generation

### RC2: Frontend Lying About Failures — FIXED (earlier)
- STATUS_CONFIG.FAILED said "Your Comic is Ready"
- **Fix:** FAILED shows "Generation Issue" with actionable retry

### RC3: Style Filters Not Distinct — FIXED (earlier)
- 8 dedicated renderers: bold_hero, cartoon, retro_pop, manga, noir, sketch, neon, pastel

### RC4: AI Generation SDK Crash — FIXED (Apr 3, 2026)
- `panel_orchestrator.py` imported from non-existent module `emergentintegrations.llm.chat_message`
- Correct module: `emergentintegrations.llm.chat`
- This caused 100% of AI panel generation calls to fail instantly (0ms latency)

### RC5: Invalid Model Names (Tier 3/4) — FIXED (Apr 3, 2026)
- Tier 3/4 used `gemini-2.0-flash-preview-image-generation` which returns 404
- Updated to `gemini-3.1-flash-image-preview` (verified working)

## Model Tier Mapping
| Tier | Model | Provider |
|------|-------|----------|
| TIER1_QUALITY | gemini-3-pro-image-preview | gemini |
| TIER2_STABLE_CHARACTER | gemini-3-pro-image-preview | gemini |
| TIER3_DETERMINISTIC | gemini-3.1-flash-image-preview | gemini |
| TIER4_SAFE_DEGRADED | gemini-3.1-flash-image-preview | gemini |

## Worker Performance Telemetry (Added Apr 3, 2026)
### Panel-Level ([WORKER_TELEMETRY])
- job_id, panel_index, style, risk_bucket
- start_time, end_time, total_duration_ms
- model_time_ms, overhead_ms
- total_attempts, final_status, pipeline_status
- fallback_used, fail_reason, model_tier_used
- Per-stage breakdown ([WORKER_STAGE]): stage, model, latency_ms, success, error

### Job-Level ([JOB_TELEMETRY])
- ready/failed/degraded/repaired/primary_pass counts
- total_attempts, total_latency_ms, avg_latency_ms
- face_consistency, style_consistency
- fallback_contamination, repair_concentration
- eval_overhead_ms

### Persistence
- Stored in MongoDB `worker_telemetry` collection

## Logging Points
- [STYLE_TRACE] JOB_START: requested_style, resolved_style, photo_hash
- [STYLE_TRACE] PANEL_DONE: style, status, model_tier, imageUrl
- [STYLE_TRACE] GUARANTEED_OUTPUT_ACTIVATED: style, reason, panel counts
- [STYLE_TRACE] GUARANTEED_OUTPUT_DONE: style, panel URLs
- [STYLE_TRACE] GUARANTEED_PANELS_PERSISTED: panels saved to DB
- [WORKER_TELEMETRY] per-panel timing breakdown
- [WORKER_STAGE] per-stage details
- [JOB_TELEMETRY] job-level quality metrics

## Upcoming Tasks
- (P0) Drive real traffic: 100-200 real jobs, monitor production metrics

## Frozen/Paused Tasks (DO NOT START)
- Admin routing config editor
- Smart Repair self-tuning router
- Dynamic style popularity badges
- Photo to Comic: Instagram export, WhatsApp share card, GIF teasers
- Bedtime Stories (TTS, Image Gen)

## Test Credentials
- Test User: test@visionary-suite.com / Test@2026#
- Admin User: admin@creatorstudio.ai / Cr3@t0rStud!o#2026
