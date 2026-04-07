# Visionary Suite - Product Requirements Document

## Original Problem Statement
Build a full-stack AI Creator Suite with compulsion-driven growth engine, monetization system, feature-guide system for user activation, and production-grade payment verification dashboard.

## Core Product
React + FastAPI + MongoDB AI creator platform with story video generation, reel scripts, social bio, comics, and content repurposing tools.

## Architecture
```
/app/
├── backend/
│   ├── routes/
│   │   ├── admin_payments.py        # NEW: Payment verification & reconciliation API
│   │   ├── user_progress.py         # Guide system progress API
│   │   ├── admin_metrics.py         # Truth-based admin metrics
│   │   ├── auth.py                  # 50-credit signup
│   │   ├── cashfree_payments.py     # Payment processing
│   │   └── cashfree_webhook_handler.py # UPGRADED: payload hash + signature verification stored
│   └── server.py
└── frontend/
    ├── src/
    │   ├── components/guide/
    │   │   ├── FirstActionOverlay.jsx   # Mandatory onboarding (0-gen users)
    │   │   ├── GuideAssistant.jsx       # Action-driven guide with auto-scroll+highlight
    │   │   └── JourneyProgressBar.jsx   # Sticky top bar, desktop+mobile
    │   ├── contexts/
    │   │   └── ProductGuideContext.js    # Success toasts, path-aware fetch
    │   └── pages/admin/
    │       └── PaymentsDashboard.js      # NEW: 5-tab payment verification dashboard
```

## What's Implemented

### Payment Verification Dashboard (2026-04-07) — 100% TESTED
Route: `/app/admin/payments`
- **Stats Strip**: 8 operational cards (Orders Today, Succeeded, Failed, Webhooks, WH Failures, Unreconciled, Settle Pending, Revenue)
- **Orders Tab**: Filterable table (email, order ID, status, date, unreconciled only) with one-row truth per order
- **Webhooks Tab**: Event list with expandable raw payload, signature verification status, payload hash
- **Reconciliation Tab**: Mismatch queue with manual actions (Fetch from Cashfree, Reconcile, Replay Webhook, Inspect)
- **Settlements Tab**: Settlement status, UTR, transfer time
- **Order Drilldown**: 4-panel deep dive (Business View, Cashfree Truth Live, Webhook Trace, Credit Transactions)
- **Mismatch Detection**: Automatically flags PAID_IN_CASHFREE_NOT_IN_DB, ACCESS_GRANTED_WITHOUT_PAYMENT, WEBHOOK_MISSING, SETTLEMENT_PENDING, DUPLICATE_WEBHOOK, SIGNATURE_VERIFICATION_FAILED
- **PRODUCTION/SANDBOX badge** on every screen
- **Admin-only access** (403 for non-admin users)
- **Webhook handler upgraded**: stores raw payload SHA-256 hash and signature verification boolean

### Activation System (2026-04-07) — 100% TESTED
1. **First-Action Overlay**: Full-screen mandatory for 0-generation users, blocks interaction, single "Start Now" CTA
2. **Action-Driven Guide**: Path-aware CTAs with auto-scroll + element highlight (indigo glow)
3. **Progress Bar**: Sticky top, desktop (5 labeled steps + %), mobile (compact bars)
4. **Stuck Recovery**: 15s idle → action-driven hints with CTA buttons

### Payment System Audit (2026-04-07)
- **Staging**: 0 orders (preview DB is separate)
- **Production DB (via backend)**: 78 orders, 24 webhooks, 19 successful
- All orders from test@visionary-suite.com (test account, no real customers yet)
- Cashfree: PRODUCTION credentials, webhook endpoint functional
- Code: idempotent payment processing, duplicate webhook protection

## Backlog
### P0
- Production Cashfree dashboard verification (user must check merchant.cashfree.com manually)

### P1
- Pipeline Parallelization (Script → Voice + Images in parallel)
- Scheduled reconciliation job (every 15 mins)

### P2
- WebSocket admin dashboard
- Story Chain leaderboard
- Remix Variants on share pages
- Health tab charts (will populate with real volume)

## 3rd Party Integrations
- OpenAI & Gemini (Emergent LLM Key)
- Cloudflare R2 (Object Storage)
- Cashfree (Payments — PRODUCTION)
- Google Identity Services (OAuth 2.0)

## Test Credentials
- New User: newuser@test.com / Test@2026#
- Admin: admin@creatorstudio.ai / Cr3@t0rStud!o#2026
- Test User: test@visionary-suite.com / Test@2026#
