# CreatorStudio AI — PRD

## Original Problem Statement
Full-stack AI creator suite with anti-copy/media-protection hardening, queue-driven content generation, growth engine, and monetization. Phase 1 (current): P0 Final Pricing, Payment Validation, and Error Handling. Phase 2 (next): P0 Copyright-Safe Input, Prompt, Asset, and Output Protection.

## Protection Stack (All Layers Complete)

| # | Layer | Status |
|---|-------|--------|
| 1-12 | URL Blocking, Media Proxy, Watermarks, Browser Friction, DB-Backed Tokens, Anti-Replay, HLS Streaming, Forensic Watermarking, Entitlement Gating, Concurrency Limits, Abuse Response, Admin Dashboard | DONE |

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
- Gateway: Cashfree PRODUCTION (hardcoded, never sandbox)
- State Machine: CREATED → INITIATED → PENDING → SUCCESS → CREDIT_APPLIED / SUBSCRIPTION_ACTIVATED
- Idempotency: Webhook handler checks event_id + order status to prevent double-crediting
- Verify endpoint: Double-checks against terminal states (PAID, CREDIT_APPLIED, SUBSCRIPTION_ACTIVATED)
- Double-click prevention: Backend returns existing session for same user+product if order is pending
- Rate limiting: 5 orders/minute per user

### Frontend Pages Fixed
- `/pricing` (Pricing.js) — 4 plans + 4 topups, safe fallback
- `/app/billing` (Billing.js) — Cancel/fail/timeout detection, no dead-end UX
- `/app/pricing` (PricingPage.js) — Updated from old hardcoded prices
- UpsellModal.js — Safe pricing access with fallback
- SubscriptionManagement.jsx — Full error handling

### Testing Results
- 20/20 backend API tests passed
- 3/3 frontend pages verified
- All 12 features verified (see /app/test_reports/iteration_431.json)

## Phase 2: Copyright Safety Pipeline (UPCOMING — P0)

### Architecture (Not Yet Implemented)
- `rule_rewriter.py` — Centralized rule definitions for IP/trademark rewrites
- `rewrite_service.py` — Input interception and safe rewriting
- `policy_engine.py` — Decision engine for block/rewrite/allow
- `prompt_sanitizer.py` — Prompt-level safety checks
- `output_validator.py` — Post-generation output validation

### Requirements
- All inputs (prompts, titles) must be inspected and safely rewritten
- System-provided assets must be audited
- Output validation mandatory
- Admin visibility via safety_events and output_validation_events collections
- Wire to ALL features: Story Video, Comic, Viral Ideas, Audio, etc.

## DB Schemas

### Existing
- `media_tokens`, `user_media_sessions`, `media_suspensions`, `media_abuse_flags`, `media_access_log`
- `orders` — Payment orders with state machine
- `webhook_events` — Webhook idempotency tracking
- `users` — credits, subscription
- `credit_transactions`, `credit_ledger`

### To Be Created (Phase 2)
- `safety_events` — user_id, feature_name, input_type, original_text_hash, rewritten_text, decision, reason_codes
- `output_validation_events` — job_id, asset_id, validation_result, action_taken

## Key API Endpoints

### Payments
- `GET /api/cashfree/products` — All 8 products with pricing
- `GET /api/cashfree/health` — Gateway health check
- `POST /api/cashfree/create-order` — Create payment order (rate-limited)
- `POST /api/cashfree/verify` — Verify payment and apply entitlement
- `POST /api/cashfree-webhook/handle` — Webhook processing (idempotent)
- `GET /api/cashfree/order/{order_id}/status` — Order status
- `GET /api/cashfree/payments/history` — Payment history

## Backlog
- (P1) Premium tier download quality differentiation
- (P2) Personalization and Precomputed Daily Packs
- (P2) Remix Variants and Story Chain leaderboard
- (P2) Admin Dashboard WebSocket upgrades

## Credentials
- Test: `test@visionary-suite.com` / `Test@2026#`
- Admin: `admin@creatorstudio.ai` / `Cr3@t0rStud!o#2026`
