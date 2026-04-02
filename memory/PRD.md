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

### P0.5 Smart Repair Pipeline (Apr 2, 2026) ✅
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

**Pipeline Constraints:**
- Max 1 primary attempt, 1 repair attempt, 1 fallback attempt (3 total per panel)
- Zero blind retries — every retry has explicit failure classification + repair mode + tier
- All routing decisions are config-driven and explainable

**Failure Taxonomy:**
- Hard: hard_fail, empty_output, corrupt_asset, provider_timeout, safety_block
- Soft: face_drift, style_drift, low_source_similarity, composition_clutter
- Structural: story_mismatch, continuity_break, character_count_mismatch

**Model Tiers (logical abstractions, swappable):**
- Tier 1: Quality (gemini-3-pro) — clean inputs
- Tier 2: Stable Character (gemini-3-pro + face anchors) — identity preservation
- Tier 3: Deterministic (gemini-2.0-flash) — stronger instruction following
- Tier 4: Safe Degraded (gemini-2.0-flash + simplified) — last resort

**Admin Metrics Added:**
- Primary pass rate, repair success rate, fallback acceptance rate
- Failure type frequency breakdown
- Risk bucket quality breakdown (LOW/MEDIUM/HIGH/EXTREME)
- Per-attempt audit trail in `comic_panel_attempts` collection

### P0 Fallback Quality Validation (Apr 2, 2026) ✅
- 5 Validation Dimensions baked into pipeline
- Admin controlled failure injection tests
- UI Safety Audit endpoint (20/20 texts pass, 0 scary words)

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

### Phase 2 (Next Session)
- [ ] Job-level fallback orchestrator (mixed mode, simplified rerun, emergency)
- [ ] Admin routing config editor (versioned, with rollback)
- [ ] Admin job diagnostics drill-down page
- [ ] Regression alerts
- [ ] Edge Chaos Matrix testing (dark+sunglasses, group+side face, etc.)
- [ ] Wire approved panel bytes for real cross-panel continuity

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
