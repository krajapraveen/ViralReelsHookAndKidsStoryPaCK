# Visionary Suite - Product Requirements Document

## Original Problem Statement
Build a full-stack AI Creator Suite ("Visionary Suite") with a compulsion-driven growth engine, monetization system, and complete feature-guide system for user activation and retention.

## Core Product
A React + FastAPI + MongoDB AI-powered creator platform offering story video generation, reel scripts, social bio generation, comic/coloring book creation, and content repurposing tools.

## Architecture
```
/app/
├── backend/ (FastAPI + MongoDB)
│   ├── routes/
│   │   ├── user_progress.py     # Guide system progress API
│   │   ├── admin_metrics.py     # Truth-based admin metrics
│   │   ├── auth.py              # Standardized 50-credit signup
│   │   ├── cashfree_payments.py # Payment with idempotent credit delivery
│   │   └── cashfree_webhook_handler.py # Webhook with duplicate protection
│   └── server.py
└── frontend/ (React + Tailwind + Shadcn)
    ├── src/
    │   ├── components/guide/
    │   │   ├── FirstActionOverlay.jsx  # NEW: Mandatory onboarding overlay
    │   │   ├── GuideAssistant.jsx      # REWRITTEN: Action-driven guide with auto-scroll+highlight
    │   │   └── JourneyProgressBar.jsx  # REWRITTEN: Sticky top bar, desktop+mobile, % completion
    │   ├── contexts/
    │   │   └── ProductGuideContext.js   # UPDATED: Success toasts, path-aware fetch
    │   └── pages/
    │       ├── Dashboard.js
    │       ├── StoryVideoStudio.js     # data-guide attributes wired
    │       ├── ReelGenerator.js        # data-guide + tracking wired
    │       └── StoryGenerator.js       # data-guide + tracking wired
```

## What's Implemented

### Activation System (2026-04-07) — ALL TESTED, 100% PASS
1. **First-Action Overlay** (P0-2)
   - Full-screen darkened overlay for users with 0 generations
   - Cannot be skipped — single CTA "Start Now" navigates to studio
   - Admin users excluded via role check
   - Session-scoped (doesn't reappear after interaction)

2. **Action-Driven Guide** (P0-3)
   - Every guide step has CTA button that auto-scrolls + highlights target
   - Path-aware: "Go to Studio" on Dashboard, "Enter Your Story" on Studio
   - Stuck hints (15s idle) include action buttons ("Scroll to input")
   - Feature tooltips with scroll-to-target and glow highlight

3. **Progress Bar** (P1)
   - Sticky at top of page for all authenticated users
   - Desktop: 5 labeled steps (Create→Customize→Generate→View→Share) with %
   - Mobile: compact colored bars with step count
   - Success toasts on step completion

4. **Stuck User Recovery** (P1)
   - 15s idle detection with action-driven hints
   - Page-contextual messages with CTA buttons
   - Auto-dismisses on user interaction

### Payment System (2026-04-07) — STAGING AUDIT COMPLETE
- All generation endpoints enforce credit deduction
- Idempotent payment processing (verify + webhook both protected)
- No revenue leaks in code
- **NOTE**: Production database audit required for real transaction verification

### Previously Completed
- Growth Engine (Share pages, First Video Free, Remix, Watermark, Referrals)
- Cashfree payment integration
- Google OAuth + JWT auth
- Admin dashboard with truth-based metrics
- Credit system (50 credits for new users)
- Legal/Copyright compliance
- Responsive Support Widgets

## Payment Audit Status
- **Staging**: CLEAN — 0 orders, 0 webhooks, code paths verified
- **Production**: PENDING — requires access to production DB at visionary-suite.com
- Cashfree configured with PRODUCTION credentials
- Webhook URL: https://www.visionary-suite.com/api/cashfree/webhook

## Backlog
### P0
- Production payment audit (requires production DB access)

### P1
- Pipeline Parallelization (Script → Voice + Images in parallel)
- A/B test hook text variations on public pages

### P2
- WebSocket admin dashboard upgrade
- Story Chain leaderboard
- Remix Variants on share pages
- UI polish and style preset thumbnails

## 3rd Party Integrations
- OpenAI & Gemini (Emergent LLM Key)
- Cloudflare R2 (Object Storage)
- Cashfree (Payments)
- Google Identity Services (OAuth 2.0)

## Test Credentials
- New User: newuser@test.com / Test@2026#
- Admin: admin@creatorstudio.ai / Cr3@t0rStud!o#2026
