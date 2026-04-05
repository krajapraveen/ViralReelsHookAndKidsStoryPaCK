# CreatorStudio AI — PRD

## Original Problem Statement
Full-stack AI creator suite with anti-copy/media-protection hardening, queue-driven content generation, growth engine, and monetization.

## Phase 1: Payment Hardening (COMPLETE — 2026-04-04)

### Pricing (Single Source of Truth)
- Backend: `/app/backend/config/pricing.py`
- Frontend: `/app/frontend/src/utils/pricing.js`

| Type | Product | Price (INR) | Credits |
|------|---------|-------------|---------|
| Subscription | Weekly | ₹149 | 40 |
| Subscription | Monthly | ₹499 | 200 |
| Subscription | Quarterly | ₹1,199 | 750 |
| Subscription | Yearly | ₹3,999 | 3,000 |
| Top-up | topup_40 | ₹99 | 40 |
| Top-up | topup_120 | ₹249 | 120 |
| Top-up | topup_300 | ₹499 | 300 |
| Top-up | topup_700 | ₹999 | 700 |

### Payment System
- Gateway: Cashfree PRODUCTION
- State Machine: CREATED → INITIATED → PENDING → SUCCESS → CREDIT_APPLIED / SUBSCRIPTION_ACTIVATED
- Idempotency: Webhook + verify endpoint both check terminal states
- Double-click prevention: Returns existing session for pending orders

## Phase 2: Copyright Safety Pipeline (COMPLETE — 2026-04-04)

### Architecture
```
/app/backend/services/rewrite_engine/
├── __init__.py               # Exports + request-scoped safety metadata store
├── rule_rewriter.py           # 200+ term replacement dictionary (narrative-rich)
├── rewrite_service.py         # Orchestrator: process_safety_check, check_and_rewrite
├── policy_engine.py           # ALLOW / REWRITE / BLOCK decisions
├── output_validator.py        # Post-generation output validation
├── safety_logger.py           # DB logging to safety_events, output_validation_events
├── semantic_detector.py       # Phase 3B: Indirect reference + fuzzy alias detection
├── output_enforcer.py         # Recursive response scanner
└── output_safety_middleware.py # Phase 3A: Universal output interception middleware
```

### Decision Tiers
| Tier | When | Action | Example |
|------|------|--------|---------|
| ALLOW | Clean content | Pass through | "A brave knight saves a village" |
| REWRITE | Trademark/IP detected | Rewrite to safe generic | "Spider-Man" → narrative-rich replacement |
| BLOCK | Genuinely dangerous | Reject with 400 | Weapon instructions, CSAM |

### Wired Features (25+ routes)
- story_video_studio, story_video_fast, story_engine_routes
- bedtime_story_builder, brand_story_builder
- comic_storybook_v2, comix_ai
- caption_rewriter_pro, comment_reply_bank
- instagram_bio_generator, youtube_thumbnail_generator
- offer_generator, story_hook_generator
- story_episode_creator, story_series
- challenge_generator, tone_switcher
- viral_ideas_v2, creator_tools, creator_pro
- photo_to_comic, reaction_gif, characters
- genstudio (image, gif, video, remix), generation (reel, story)
- coloring_book_v2, gif_maker

## Phase 3: Adaptive Safety & Output Enforcement (COMPLETE — 2026-04-05)

### Phase 3A: Universal Output Enforcement (COMPLETE)
- Starlette middleware intercepts ALL generation route responses
- Recursive JSON scanning via output_enforcer.py
- GZIP decompression handling
- Fail-closed: errors return original response, never crash

### Phase 3B: Indirect Reference Detection (COMPLETE)
- Two detection layers:
  1. Co-occurrence patterns: 24+ pattern packs (Harry Potter, Disney, Marvel, Naruto, Star Wars, Pokemon, LOTR, Pixar, Avatar)
  2. Fuzzy alias matching: leet speak (sp1der→spider), spacing (h a r r y), diacritics (Spïdêr), common typos
- False positive guard: common English words (frozen, avatar) excluded from fuzzy aliases
- Test results: 10/10 indirect bypasses, 10/10 obfuscation, 0 false positives on 14 clean prompts

### Phase 3C: Rewrite Quality Upgrade (COMPLETE)
- All 200+ replacements upgraded from label-style ("web-slinging masked hero") to narrative-rich with increased semantic distance ("a nimble acrobatic vigilante who patrols city rooftops")
- All rewrites 5+ words minimum
- Golden test suite: 54 test cases covering direct rewrites, semantic detection, obfuscation, false positives, end-to-end pipeline
- Test file: `/app/backend/tests/test_rewrite_quality.py`

### Phase 3D: Safety Telemetry / Admin Insights (COMPLETE)
- GET /api/admin/metrics/safety-insights — top rewritten terms, top IP clusters, high-risk routes, output leakage stats, detection type breakdown
- GET /api/admin/metrics/safety-overview — aggregate counts + rates + by-feature breakdown
- GET /api/admin/metrics/safety-events — event list with filtering

### Phase 3E: Frontend Soft Warning UX (COMPLETE)
- Backend middleware injects `_safety_meta` into generation responses when rewrite occurred
- Frontend api.js interceptor shows subtle toast via sonner: "We adjusted a few words to keep your content original and generation-ready."
- No toast for clean prompts; no alarming legal language

### DB Collections
- `safety_events` — user_id, feature_name, decision, reason_codes, triggered_rules, rewrite_summary (with detection_types, semantic_detections), timestamp
- `output_validation_events` — user_id, feature_name, validation_result, action_taken, leaked_terms, timestamp

### Testing Results
- Phase 3 API tests: 20/20 passed (iteration_433.json)
- Golden test suite: 54/54 passed
- Adversarial testing: direct, indirect, obfuscated, mixed, false positive, fail-closed

## Backlog
- (P1) Premium tier download quality differentiation
- (P1) A/B test hook text variations on public pages
- (P1) Character-driven auto-share prompts after creation
- (P2) Remix Variants on share pages
- (P2) Admin Dashboard WebSocket upgrades
- (P2) Personalization and Precomputed Daily Packs
- (P2) Story Chain leaderboard

## Credentials
- Test: `test@visionary-suite.com` / `Test@2026#`
- Admin: `admin@creatorstudio.ai` / `Cr3@t0rStud!o#2026`
