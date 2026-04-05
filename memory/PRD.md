# CreatorStudio AI — PRD

## Original Problem Statement
Full-stack AI creator suite with anti-copy/media-protection hardening, queue-driven content generation, growth engine, and monetization.

## Phase 1: Payment Hardening (COMPLETE — 2026-04-04)

### Pricing (Single Source of Truth)
- Backend: `/app/backend/config/pricing.py`
- Frontend: `/app/frontend/src/utils/pricing.js`

| Type | Product | Price (INR) | Credits |
|------|---------|-------------|---------|
| Subscription | Weekly | 149 | 40 |
| Subscription | Monthly | 499 | 200 |
| Subscription | Quarterly | 1199 | 750 |
| Subscription | Yearly | 3999 | 3000 |
| Top-up | topup_40 | 99 | 40 |
| Top-up | topup_120 | 249 | 120 |
| Top-up | topup_300 | 499 | 300 |
| Top-up | topup_700 | 999 | 700 |

### Payment System
- Gateway: Cashfree PRODUCTION
- State Machine: CREATED -> INITIATED -> PENDING -> SUCCESS -> CREDIT_APPLIED / SUBSCRIPTION_ACTIVATED
- Idempotency: Webhook + verify endpoint both check terminal states
- Double-click prevention: Returns existing session for pending orders

## Phase 2: Copyright Safety Pipeline (COMPLETE — 2026-04-04)

### Architecture
```
/app/backend/services/rewrite_engine/
  __init__.py          # Exports + request-scoped safety metadata store
  rule_rewriter.py     # 200+ term replacement dictionary (narrative-rich)
  rewrite_service.py   # Orchestrator: process_safety_check, check_and_rewrite
  policy_engine.py     # ALLOW / REWRITE / BLOCK decisions
  output_validator.py  # Post-generation output validation
  safety_logger.py     # DB logging to safety_events, output_validation_events
  semantic_detector.py # Indirect reference + fuzzy alias detection
  output_enforcer.py   # Recursive response scanner
  output_safety_middleware.py # Universal output interception middleware
```

### Decision Tiers
| Tier | When | Action |
|------|------|--------|
| ALLOW | Clean content | Pass through |
| REWRITE | Trademark/IP detected | Rewrite to safe generic |
| BLOCK | Genuinely dangerous | Reject with 400 |

### Wired into 25+ generation routes

## Phase 3: Adaptive Safety & Output Enforcement (COMPLETE — 2026-04-05)

### Phase 3A: Universal Output Enforcement (COMPLETE)
- Starlette middleware intercepts ALL generation route responses
- Recursive JSON scanning via output_enforcer.py
- GZIP decompression handling
- Fail-closed on errors

### Phase 3B: Indirect Reference Detection (COMPLETE)
- Two detection layers:
  1. Co-occurrence patterns: 24+ pattern packs (Harry Potter, Disney, Marvel, Naruto, Star Wars, Pokemon, LOTR, Pixar, Avatar)
  2. Fuzzy alias matching: leet speak, spacing, diacritics, common typos
- Zero false positives on clean prompts

### Phase 3C: Rewrite Quality Upgrade (COMPLETE)
- 200+ narrative-rich replacements with increased semantic distance
- Golden test suite: 54 test cases at /app/backend/tests/test_rewrite_quality.py

### Phase 3D: Safety Telemetry (COMPLETE)
- GET /api/admin/metrics/safety-insights — top terms, IP clusters, high-risk routes, output leakage, detection types

### Phase 3E: Frontend Soft Warning UX (COMPLETE)
- Middleware injects _safety_meta into generation responses
- Frontend api.js interceptor shows subtle sonner toast

## Safety Playground (COMPLETE — 2026-04-05)

### P0 Admin Internal Tool
- POST /api/admin/metrics/safety-playground — Real-time pipeline analysis
- Shows: Decision (ALLOW/REWRITE/BLOCK), Detection Layers (Rule Rewriter, Semantic Detector, Policy Engine), Rewrite Output with diff, Semantic Distance score, Per-layer timing, "Why This Triggered" explanation
- Save Test Case: Saves prompts to safety_test_cases collection
- Saved Cases: Browse and replay previously saved test prompts
- Preset buttons: Semantic bypass, Obfuscated name, Clean prompt, Dangerous, Indirect Disney, Mixed
- Under 1ms average latency (target was 500ms)
- Frontend: /app/admin -> Safety Lab tab

### Test Results
- Phase 3: 20/20 API tests + 54/54 golden suite (iteration_433.json)
- Safety Playground: 17/17 backend tests + full frontend verification (iteration_434.json)

## DB Collections (Safety)
- safety_events — user_id, feature_name, decision, reason_codes, triggered_rules, rewrite_summary, timestamp
- output_validation_events — user_id, feature_name, validation_result, action_taken, leaked_terms, timestamp
- safety_test_cases — prompt, expected_detection, feature, saved_at, saved_by

## Backlog (Priority Order)
- (P1) A/B test hook text variations on public pages
- (P1) Character-driven auto-share prompts after creation
- (P1) Viral loop: Continue story -> share -> remix -> loop
- (P1) Premium tier download quality differentiation
- (P2) Remix Variants on share pages
- (P2) Admin Dashboard WebSocket upgrades
- (P2) Personalization and Precomputed Daily Packs
- (P2) Story Chain leaderboard

## Credentials
- Test: test@visionary-suite.com / Test@2026#
- Admin: admin@creatorstudio.ai / Cr3@t0rStud!o#2026
