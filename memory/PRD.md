# Visionary Suite - Product Requirements Document

## Original Problem Statement
Build a full-stack AI Creator Suite ("Visionary Suite") with a compulsion-driven growth engine, monetization system, and complete legal/copyright compliance.

## Core Product
A React + FastAPI + MongoDB AI-powered creator platform offering:
- Story video generation (with AI narration, scenes, music)
- Reel/short-form video script generation
- Social bio generation
- Comic/coloring book creation
- Photo-to-comic transformation
- Content repurposing tools
- Admin dashboard with truth-based metrics

## Architecture
```
/app/
├── backend/ (FastAPI + MongoDB)
│   ├── routes/ (API endpoints)
│   │   ├── experience_feedback.py  # NEW: Feedback submission + admin endpoints
│   │   └── ... 
│   ├── scripts/
│   │   └── reset_non_admin_credits_to_50.py  # NEW: One-time migration
│   ├── services/ (Business logic, AI integrations, pipeline)
│   └── server.py (Entry point)
└── frontend/ (React + Tailwind + Shadcn)
    ├── src/
    │   ├── components/
    │   │   └── FeedbackModal.jsx     # NEW: Post-usage feedback capture
    │   ├── contexts/
    │   │   └── FeedbackContext.js     # NEW: Logout interception + idle detection
    │   ├── hooks/
    │   │   └── useIdleFeedbackPrompt.js # NEW: Idle detection hook
    │   ├── pages/Admin/
    │   │   └── AdminFeedbackPage.js  # NEW: Admin feedback dashboard
    │   └── utils/
    │       └── feedbackSession.js    # NEW: Session tracking utilities
```

## What's Implemented (as of 2026-04-06)
- Full AI creation suite
- Growth Engine (Share pages, First Video Free, Remix, Watermark, Referrals)
- Cashfree payment integration
- Google OAuth + JWT auth
- Admin dashboard with truth-based metrics
- Credit system (50 credits for new users)
- Legal/Copyright compliance (30+ files cleaned)
- **Credit reset migration** (all non-admin users set to 50)
- **Post-usage feedback system** (logout + idle prompts)
- **Admin feedback dashboard** (with unread badge, filters, mark-read)

## Completed Tasks (Current Session)
- [x] P0 Legal/Copyright cleanup across 30+ frontend files
- [x] P0 Credit reset: All non-admin users set to exactly 50 credits
- [x] P0 Idempotent migration script with dry-run mode
- [x] P0 Feedback modal on logout (only after real feature usage)
- [x] P0 Idle feedback prompt (2-min idle after feature usage)
- [x] P0 Session-scoped tracking (no repeat prompts)
- [x] P1 Admin feedback dashboard at /app/admin/feedback
- [x] P1 Unread badge in admin sidebar (auto-refresh every 60s)
- [x] markFeatureUsed() integrated into 7 generation flows

## Backlog
### P1
- Pipeline Parallelization (Script → Voice + Images in parallel)
- A/B test hook text variations on public pages

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
