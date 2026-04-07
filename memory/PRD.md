# Visionary Suite - Product Requirements Document

## Original Problem Statement
Build a full-stack AI Creator Suite with compulsion-driven growth engine, monetization system, feature-guide system for user activation, production-grade payment verification dashboard, and high-converting funnel analytics + smart paywall system.

## Architecture
```
/app/
├── backend/
│   ├── config/
│   │   └── pricing.py                 # Single source of truth for all plans & pricing
│   ├── routes/
│   │   ├── pricing_api.py             # GET /api/pricing-catalog/plans (exposes pricing to frontend)
│   │   ├── funnel_tracking.py         # POST /api/funnel/track + GET /api/funnel/metrics
│   │   ├── admin_payments.py          # Payment verification & reconciliation API
│   │   ├── cashfree_webhook_handler.py # Stores payload hash + signature verification
│   │   ├── user_progress.py           # Guide system progress API
│   │   ├── admin_metrics.py           # Truth-based admin dashboard metrics
│   │   └── ... (other routes)
│   └── server.py
└── frontend/
    ├── src/
    │   ├── components/
    │   │   ├── UpgradeModal.js            # PRIMARY inline smart paywall (fetches from backend)
    │   │   └── guide/
    │   │       ├── FirstActionOverlay.jsx  # Mandatory onboarding (0-gen users)
    │   │       ├── PostValueOverlay.jsx    # Post-value push → paywall connector
    │   │       ├── GuideAssistant.jsx      # Action-driven guide
    │   │       └── JourneyProgressBar.jsx  # Sticky top bar
    │   ├── utils/
    │   │   └── funnelTracker.js           # Fires funnel events with rich context
    │   ├── pages/
    │   │   ├── PricingPage.js             # SECONDARY pricing (fetches from backend, not hardcoded)
    │   │   └── admin/
    │   │       └── PaymentsDashboard.js   # 5-tab payment verification
    │   └── App.js                         # Wires PostValueOverlay + UpgradeModal
```

## What's Implemented

### Conversion Funnel System — COMPLETE (2026-04-07)
100% tested (iteration_454, 18/18 backend + all frontend verified)
1. **Funnel Analytics Backend**: POST /api/funnel/track (11 steps), GET /api/funnel/metrics (admin)
   - Rich context: user_id, session_id, source_page, device, generation_count, plan_shown, plan_selected
   - Conversion/drop-off %, device breakdown, source breakdown, paywall micro-funnel
2. **Smart Paywall (Inline)**: UpgradeModal is PRIMARY paywall — no page navigation
   - Fetches plans from backend /api/pricing-catalog/plans (NOT hardcoded)
   - "MOST POPULAR" plan highlighted, emotional CTAs, "Continue with limited access" soft exit
   - Integrates directly with Cashfree for payment
   - Fires micro-conversion events (paywall_viewed, plan_selected, payment_started, payment_abandoned, payment_success)
3. **Post-Value Overlay**: Shows after each generation
   - 1st gen: "Your story is ready!" with Continue/Video/Share
   - 2nd gen: "Unlock Unlimited" + "Continue with limited access" → triggers paywall
4. **Dynamic PricingPage**: Fetches plans from backend (Free + 4 subscriptions + 4 topups)
5. **Funnel Event Firing**: Landing (landing_view), CTA clicks (first_action_click), generation start/complete, result viewed, billing page events

### Payment Verification Dashboard — COMPLETE (2026-04-07)
Route: `/app/admin/payments` | 100% tested (iteration_453)

### Activation System — COMPLETE (2026-04-07)
100% tested (iteration_452, 22/22 tests)

### Payment Audit Result — CONFIRMED WORKING
Cashfree production payments processing correctly.

## Backlog
### P1
- Analyze funnel drop-off data once collected
- A/B test hook text variations on public pages
- Character-driven auto-share prompts after creation

### P2
- Dynamic pricing tests (active vs new users)
- Pipeline Parallelization (Script → Voice + Images in parallel)
- WebSocket admin dashboard upgrade
- Story Chain leaderboard
- Remix Variants on share pages

## Test Credentials
- Admin: admin@creatorstudio.ai / Cr3@t0rStud!o#2026
- Test User: test@visionary-suite.com / Test@2026#
