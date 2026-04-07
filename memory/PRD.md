# Visionary Suite - Product Requirements Document

## Original Problem Statement
Build a full-stack AI Creator Suite ("Visionary Suite") with a compulsion-driven growth engine, monetization system, and complete legal/copyright compliance. Latest mandate: implement a Complete Feature-Guide System with 4 layers.

## Core Product
A React + FastAPI + MongoDB AI-powered creator platform offering:
- Story video generation (with AI narration, scenes, music)
- Reel/short-form video script generation
- Social bio generation
- Comic/coloring book creation
- Photo-to-comic transformation
- Content repurposing tools
- Admin dashboard with truth-based metrics
- Product Guide System for onboarding and feature discovery

## Architecture
```
/app/
├── backend/ (FastAPI + MongoDB)
│   ├── routes/
│   │   ├── user_progress.py     # Guide system progress API
│   │   ├── admin_metrics.py     # Truth-based admin metrics
│   │   ├── auth.py              # Standardized 50-credit signup
│   │   ├── public_routes.py     # Social proof + Live Activity
│   │   ├── cashfree_payments.py # Payment with idempotent credit delivery
│   │   └── cashfree_webhook_handler.py # Webhook with duplicate protection
│   ├── services/
│   │   └── anti_abuse_service.py # Disabled delayed credits (50-credit policy)
│   └── server.py
└── frontend/ (React + Tailwind + Shadcn)
    ├── src/
    │   ├── components/
    │   │   ├── guide/
    │   │   │   ├── GuideAssistant.jsx    # Context-aware guide bubble + panel + stuck hint
    │   │   │   └── JourneyProgressBar.jsx # Mobile journey progress bar
    │   │   ├── support/
    │   │   │   └── SupportDock.jsx        # Mobile support dock
    │   │   └── CookieConsent.js           # GDPR banner (z-9000)
    │   ├── contexts/
    │   │   └── ProductGuideContext.js     # Guide state, stuck detection, feature walkthroughs
    │   └── pages/
    │       ├── Dashboard.js
    │       ├── StoryVideoStudio.js       # data-guide attributes wired
    │       ├── ReelGenerator.js          # data-guide attributes + tracking wired
    │       └── StoryGenerator.js         # data-guide attributes + tracking wired
```

## What's Implemented (as of 2026-04-07)
- Full AI creation suite
- Growth Engine (Share pages, First Video Free, Remix, Watermark, Referrals)
- Cashfree payment integration (idempotent, duplicate-protected)
- Google OAuth + JWT auth
- Admin dashboard with truth-based metrics
- Credit system (50 credits for new users, all paths audited)
- Legal/Copyright compliance
- Post-usage feedback system
- Responsive Support Widgets (floating on desktop, dock on mobile)
- **Product Guide System** (4 layers implemented):
  1. Master Journey Tracking (Create -> Customize -> Generate -> Result -> Share)
  2. Feature Walkthroughs (StoryVideoStudio, ReelGenerator, StoryGenerator)
  3. Context-Aware Guidance (smart prompts based on user progress)
  4. Stuck User Recovery (15s idle detection with contextual hints)

## Product Guide System (2026-04-07)
- **GuideAssistant**: Fixed-position bubble (z-10000) with expandable panel showing next step, CTA, journey mini-map, dismiss option
- **JourneyProgressBar**: Mobile-only (lg:hidden) top progress bar showing 5-step journey
- **Stuck Hint**: Amber floating prompt after 15s idle, page-contextual messages
- **Feature Tooltips**: Anchored tooltips highlighting specific UI elements with step-by-step progression
- **data-guide attributes**: Added to key interactive elements across StoryVideoStudio, ReelGenerator, StoryGenerator
- **Z-index hierarchy**: Guide (10000) > Cookie banner (9000)
- **Backend API**: GET/POST /api/user/progress (create/read/update/dismiss)

## Payment Audit (2026-04-07) - CLEAN
- Credit deduction enforced on all generation endpoints
- Double-credit protection: both verify endpoint and webhook have idempotency guards
- No free-access leaks (demo endpoint returns static templates only)
- Server startup auto-topup removed
- Anti-abuse delayed credits disabled (aligned with 50-credit policy)
- Fixed: Demo reel message "100 free credits" -> "50 free credits"

## Backlog
### P1
- Pipeline Parallelization (Script -> Voice + Images in parallel)
- A/B test hook text variations on public pages
- Character-driven auto-share prompts

### P2
- Upgrade admin dashboard from polling to WebSockets
- "Story Chain" leaderboard
- "Remix Variants" on share pages
- UI polish and style preset thumbnails

## 3rd Party Integrations
- OpenAI & Gemini (Emergent LLM Key)
- Cloudflare R2 (Object Storage)
- Cashfree (Payments)
- Google Identity Services (OAuth 2.0)

## Test Credentials
- Test User: test@visionary-suite.com / Test@2026#
- Admin: admin@creatorstudio.ai / Cr3@t0rStud!o#2026
