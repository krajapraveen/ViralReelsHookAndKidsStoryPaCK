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
- Tested: 20/20 backend, 3/3 frontend pages

## Phase 2: Copyright Safety Pipeline (COMPLETE — 2026-04-04)

### Architecture
```
/app/backend/services/rewrite_engine/
├── __init__.py               # Exports: process_safety_check, check_and_rewrite, validate_generation_output
├── rule_rewriter.py           # 200+ term replacement dictionary (existing)
├── rewrite_service.py         # Orchestrator: process_safety_check, check_and_rewrite, validate_generation_output
├── policy_engine.py           # NEW: ALLOW / REWRITE / BLOCK decisions
├── output_validator.py        # NEW: Post-generation output validation
└── safety_logger.py           # NEW: DB logging to safety_events, output_validation_events
```

### Decision Tiers
| Tier | When | Action | Example |
|------|------|--------|---------|
| ALLOW | Clean content | Pass through | "A brave knight saves a village" |
| REWRITE | Trademark/IP detected | Rewrite to safe generic | "Spider-Man" → "agile wall-climbing hero" |
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

### Admin Dashboard
- GET /api/admin/metrics/safety-overview — Aggregate counts + rates + by-feature breakdown
- GET /api/admin/metrics/safety-events — Event list with filtering by decision and feature

### Demo/Sample Asset Audit
- All homepage banner images: original AI-generated content ✅
- Blog content: trademark names used only in educational "what NOT to do" context ✅
- SEO blog: "Marvel and DC" reference rewritten to "classic comic book tradition" ✅
- Frontend blocked terms list: correctly prevents client-side IP input ✅

### DB Collections
- `safety_events` — user_id, feature_name, input_type, original_text_hashes, decision, reason_codes, triggered_rules, rewrite_summary, timestamp
- `output_validation_events` — user_id, feature_name, job_id, asset_id, validation_result, action_taken, leaked_terms, timestamp

### Testing Results
- 23/23 backend API tests passed (iteration_432.json)
- 3/3 frontend pages verified (regression)
- All 10 test categories verified

## Backlog
- (P1) Premium tier download quality differentiation
- (P2) Personalization and Precomputed Daily Packs
- (P2) Remix Variants, Story Chain leaderboard
- (P2) Admin Dashboard WebSocket upgrades

## Credentials
- Test: `test@visionary-suite.com` / `Test@2026#`
- Admin: `admin@creatorstudio.ai` / `Cr3@t0rStud!o#2026`
