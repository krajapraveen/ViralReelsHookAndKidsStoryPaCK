# Visionary Suite — Product Requirements Document

## Original Problem Statement
AI Creator Suite ("Growth Engine") with Photo to Comic as the primary conversion feature. Focus on compulsion-driven growth, monetization discipline, and pipeline resilience. Currently in **VALIDATION MODE** — no new features, only stability/reliability/quality work.

## Core Products
1. **Photo to Comic** (Primary — Active Development, P0.5 Quality Upgrade)
2. **Bedtime Story Builder** (Paused for validation)

## Architecture
- **Frontend**: React (Vite) + Tailwind + Shadcn/UI
- **Backend**: FastAPI + MongoDB + Redis
- **Integrations**: OpenAI/Gemini (Emergent LLM Key), Cloudflare R2, Cashfree, Google Auth
- **Smart Repair Pipeline**: 6 modular services in `/app/backend/services/comic_pipeline/`

## Credentials
- Test User: test@visionary-suite.com / Test@2026#
- Admin User: admin@creatorstudio.ai / Cr3@t0rStud!o#2026

---

## What's Been Implemented

### Phase 1 Smart Repair Pipeline (Apr 2, 2026) ✅
**Complete architectural overhaul of the comic generation pipeline.**
Replaced blind retries with: Diagnose → Smart Repair → Reroute → Validate → Escalate

**New Modules Created:**
1. `/app/backend/enums/pipeline_enums.py` — FailureType (13 types), ModelTier (4 tiers), RepairMode (R1-R4), thresholds, routing configs
2. `/app/backend/services/comic_pipeline/attempt_logger.py` — Per-attempt structured logging to `comic_panel_attempts`
3. `/app/backend/services/comic_pipeline/validator_stack.py` — 6-layer validation (asset, vision, identity, style, story, layout)
4. `/app/backend/services/comic_pipeline/prompt_composer.py` — Layered prompts + failure-specific repair patches
5. `/app/backend/services/comic_pipeline/model_router.py` — Config-driven tiered routing
6. `/app/backend/services/comic_pipeline/character_lock_service.py` — Character identity lock
7. `/app/backend/services/comic_pipeline/panel_orchestrator.py` — Heart of the pipeline: Primary → Validate → Repair → Fallback

### Phase 2A Job-Level Policy Engine (Apr 2, 2026) ✅
- `job_orchestrator.py`: 3-part architecture (Signals → Policy → Execution)
- 6 decision outcomes: ACCEPT_FULL, ACCEPT_WITH_DEGRADATION, TARGETED_PANEL_RERUN, STYLE_DOWNGRADE_RERUN, PARTIAL_USABLE_OUTPUT, FAIL_TERMINAL
- Full audit trail with rejected alternatives and threshold crossings
- Decision logging to `comic_job_decisions` collection

### Phase 2B Curated Continuity Pack (Apr 2, 2026) ✅
- `continuity_pack.py`: Curated panel reference selection (not raw history spam)
- Generation context: max 3 refs (anchor + best face + previous)
- Validation context: max 4 refs (broader relevance-sorted set)
- Prevents context bloat for large panel counts

### Phase 2 Testing — COMPLETE (Apr 3, 2026) ✅
**167 tests, 100% pass rate across 6 test suites:**

| Suite | Tests | Focus |
|-------|-------|-------|
| `test_job_signals.py` | 22 | Signal extraction (borderline, contradictory, cost/latency) |
| `test_job_policy.py` | 30 | Policy decisions (all 6 branches, tie-breaking, worst-signal-wins) |
| `test_continuity_pack.py` | 22 | Reference selection (anchor, confidence ranking, bounded) |
| `test_job_orchestrator_integration.py` | 19 | Full signal→policy→execution (reruns, downgrades, invariants) |
| `test_adversarial_smoke.py` | 31 | Threshold edges, validator disagreement, cost breach, corruption |
| `test_chaos_matrix.py` | 43 | Kill tests: input, economic, state machine, cross-panel, validator, router |

**Evidence produced:**
- Each policy branch executed at least once
- Each terminal path verified
- Each degradation path verified
- Each hard cap proven non-bypassable
- Continuity pack proven bounded and curated

**Policy Edge Case Found:**
- 50% fallback contamination at exact ceiling triggers PARTIAL_USABLE_OUTPUT (not ACCEPT_WITH_DEGRADATION). This is correct behavior — strict `<` boundary.

### Pipeline Constraints:
- Max 1 primary attempt, 1 repair attempt, 1 fallback attempt (3 total per panel)
- Zero blind retries — every retry has explicit failure classification + repair mode + tier
- All routing decisions are config-driven and explainable
- Job-level: targeted rerun max 2 panels, style downgrade uses EXTREME risk

### Earlier Work (Previous Sessions) ✅
- Interactive StylePreviewStrip, ComicDownloads
- Pre-generation Photo Quality Scoring (OpenCV/YuNet)
- Post-generation Character Consistency Validator
- Failure Masking system
- Growth Loop, Monetization, Trust Fixes

---

## Current Status: VALIDATION MODE + QUALITY UPGRADE

### Phase 1 Complete ✅
- [x] Enums + shared contracts
- [x] Attempt logger
- [x] Validator stack + failure classification
- [x] Prompt composer
- [x] Model router
- [x] Character lock service (lightweight)
- [x] Panel orchestrator
- [x] Refactored photo_to_comic.py to delegate to orchestrator
- [x] Admin metrics (smart repair overview)
- [x] Frontend admin dashboard updates

### Phase 2 Complete ✅
- [x] Job-level policy engine (job_orchestrator.py)
- [x] Curated continuity pack (continuity_pack.py)
- [x] Wired into photo_to_comic.py
- [x] **Real approved panel bytes wired for live cross-panel continuity** — `_generate_panel` now feeds curated prior panel images directly to the LLM as visual references alongside the source photo. System message dynamically enhanced when references exist. All 3 stages (PRIMARY, REPAIR, FALLBACK) pass references.
- [x] P0 deterministic policy correctness tests (52 tests)
- [x] P0.5 adversarial smoke pack (31 tests)
- [x] P1 chaos matrix kill tests (43 tests)
- [x] Full regression pass (167/167)

### DEVELOPMENT FROZEN
No further feature work. Deploy, observe real traffic, fix only critical production bugs.

---

## Upcoming Tasks
- (P1) A/B test hook text variations on public pages
- (P1) Character-driven auto-share prompts after creation

## Future/Backlog (P2 — DO NOT implement until quality validated)
- Dynamic style popularity badges ("Trending Now")
- Instagram 4:5 export, WhatsApp share card, GIF teaser
- Real TTS, Image Generation, Video Pipeline for Bedtime Stories
- "Remix Variants" on share pages
- Admin dashboard WebSocket upgrade
- "Story Chain" leaderboard

## Known Issues
- photo_to_comic.py still large (~3100 lines) — further splitting recommended
- Smart repair metrics will be null until real jobs go through the new pipeline
- Policy edge case: 50% fallback contamination = PARTIAL_USABLE_OUTPUT (by design, document for future tuning)
