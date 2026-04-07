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
│   │   ├── experience_feedback.py  # Feedback submission + admin endpoints
│   │   └── ... 
│   ├── scripts/
│   │   └── reset_non_admin_credits_to_50.py  # One-time migration
│   ├── services/ (Business logic, AI integrations, pipeline)
│   └── server.py (Entry point)
└── frontend/ (React + Tailwind + Shadcn)
    ├── src/
    │   ├── components/
    │   │   └── FeedbackModal.jsx     # Post-usage feedback capture
    │   ├── contexts/
    │   │   └── FeedbackContext.js     # Logout interception + idle detection
    │   ├── hooks/
    │   │   └── useIdleFeedbackPrompt.js # Idle detection hook
    │   ├── pages/Admin/
    │   │   └── AdminFeedbackPage.js  # Admin feedback dashboard
    │   └── utils/
    │       └── feedbackSession.js    # Session tracking utilities
```

## What's Implemented (as of 2026-04-06)
- Full AI creation suite
- Growth Engine (Share pages, First Video Free, Remix, Watermark, Referrals)
- Cashfree payment integration
- Google OAuth + JWT auth
- Admin dashboard with truth-based metrics
- Credit system (50 credits for new users)
- Legal/Copyright compliance (30+ files cleaned)
- Credit reset migration (all non-admin users set to 50)
- Post-usage feedback system (logout + idle prompts)
- Admin feedback dashboard (with unread badge, filters, mark-read)
- **Responsive Support Widgets** — floating on desktop, bottom dock + bottom sheet on mobile/tablet

## Responsive Support System (2026-04-06)
- Desktop (>=1024px): Floating chatbot, live chat, feedback widgets at bottom-right
- Mobile/Tablet (<1024px): Bottom support dock with Chat/Support/Feedback buttons
- Bottom sheet slides up with inline chatbot or live chat content
- Body padding-bottom: 72px on mobile/tablet prevents dock from covering content
- Drag-to-dismiss, backdrop dismiss, ESC key, close button all supported
- Files: ResponsiveSupportWrapper.jsx, SupportDock.jsx, SupportBottomSheet.jsx, useViewport.js

## Production QA Status (2026-04-06) — ALL PASS
- [x] Section 1: Credits DB — Migration completed, admin=999999999, all 29 non-admins=50
- [x] Section 2: Signup — New email users get exactly 50 credits + correct messaging
- [x] Section 3: Feature Usage Tracking — markFeatureUsed() in 7 generation flows (8 call sites)
- [x] Section 4: Feedback Modal — No modal without feature usage, modal appears with usage, once-per-session enforced
- [x] Section 5: Feedback API — Valid submission, validation, auth check all pass
- [x] Section 6: Admin Dashboard — List, unread count, filter, mark-read, access control all pass
- [x] Section 7: Regression — Login, admin login, profile, health check all pass
- [x] Section 8: Edge Cases — Rate limiting (3/day), migration idempotency, sanitization, bulk mark-read all pass

## Bug Found & Fixed During QA
- Stale message string in email signup response said "10 free credits" instead of "50 free credits" (fixed in auth.py line 413-417)

## P0 Growth Dashboard Fix (2026-04-07) — ALL PASS
Root cause: datetime/string type mismatch in MongoDB queries. pipeline_jobs.created_at is a datetime, but queries compared it with ISO strings → always returned 0.

**Fixed:**
- [x] pipeline_jobs.created_at queries now use datetime objects (admin_metrics.py lines 46-47, 74-79, 243, 1697-1700)
- [x] users.created_at queries also fixed (same type mismatch)
- [x] Story Created: 0 → 60
- [x] Continuation Rate: 0% → 20.0%
- [x] Share Rate: 0% → 68.3%
- [x] Branches/Story: 0 → 0.37
- [x] Top Stories + Story-Level Performance deduplicated (39 unique from 42 raw)
- [x] Variant B set as default production hero (was random A/B/C)
- [x] Admin funnel debug endpoint added (/api/admin/metrics/funnel-debug)
- [x] creation_completed growth event wired in pipeline completion
- [x] Testing: 100% pass (18/18 backend + all UI, iteration_449.json)

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
