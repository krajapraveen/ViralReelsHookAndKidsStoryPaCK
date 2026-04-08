# Visionary Suite - Product Requirements Document

## Original Problem Statement
Build a full-stack AI Creator Suite with compulsion-driven growth engine, monetization, activation, conversion funnel, retention engine, content protection, and production-grade scale readiness. Latest mandate: Fix conversion drop-off by making the user journey self-explanatory and trust-building.

## Architecture
```
/app/
├── backend/
│   ├── routes/
│   │   ├── instant_story.py                 # Zero-friction generation + multi-signal first-time detection
│   │   ├── story_video_generation.py        # Image/voice/video generation with admission control + idempotency
│   │   ├── story_video_studio.py            # Project CRUD with idempotent creation + strict auth (no test_user)
│   │   ├── funnel_tracking.py               # All funnel events (fire-and-forget writes)
│   │   ├── system_health_api.py             # System health + Load Guard
│   │   └── pricing_api.py                   # Dynamic pricing
│   ├── services/
│   │   ├── admission_controller.py          # Load Guard
│   │   └── load_guard_alerts.py             # Slack alerts
│   └── security.py                          # Global rate limits (slowapi)
├── frontend/src/
│   ├── pages/
│   │   ├── InstantStoryExperience.jsx       # Demo + continuation + free-view + tooltip + paywall
│   │   ├── StoryPaywall.jsx                 # Full-screen paywall modal
│   │   ├── StoryVideoStudio.js              # Video creation with idempotency + admission control + refresh-safe resume
│   │   ├── MySpacePage.js                   # Plain-English UX overhaul with self-explanatory project cards
│   │   ├── Profile.js                       # User profile
│   │   └── Landing.js                       # CTAs → /experience
│   ├── components/
│   │   ├── WaitingExperience.js             # Progress card with video wait-time banner
│   │   └── GlobalUserBar.jsx               # Sticky profile dropdown
│   └── App.js                               # Routes
└── load-tests/
    └── results/LOAD_TEST_REPORT.md
```

## Completed Systems
1. Conversion Funnel, Smart Inline Paywall, Retention Engine, Content Protection
2. Production Scale Readiness + Load Guard + Slack Alerts
3. Instant Demo Experience + Continue Story Loop + Smart Paywall
4. Load Testing — 3-phase
5. First-Time Free Viewing (v2) — Multi-signal detection, abuse prevention
6. Video Wait-Time Messaging — 5-min hardcoded message
7. Onboarding Tooltip — Contextual conversion on Parts 2-3
8. Idempotent Project Creation — Prevents duplicate project rows
9. Proper list_projects — Auth-based user filtering, parent-only, idempotency collapse
10. Profile In Progress Cleanup — Friendly stage labels, progress bars, delete buttons
11. Admission Control — Per-user (2 active) and system-wide (10 active) job limits
12. Idempotent Generation — All generate endpoints reject duplicate requests
13. Structured Error Responses — 429 with USER_JOB_LIMIT / CAPACITY_EXCEEDED
14. **MySpace Plain-English UX Overhaul** — Status-to-copy mapping, 4 info sections per card, 6-step progress timeline, asset explanations, "How this works" collapsible
15. **Backend Auth Hardening** — All 6 test_user fallbacks eliminated, strict Depends(get_current_user) enforced
16. **Refresh-Safe Job Resume** — StoryVideoStudio polls /active-jobs on mount, restores progress UI

## MySpace UX Spec (Implemented)
### Status Copy Mapping
- QUEUED → "Waiting in line"
- PROCESSING → "Creating your video" (with dynamic sub-stage)
- COMPLETED → "Your video is ready"
- FAILED → "Needs attention"

### Card Structure (All Statuses)
- What this is — project description
- What's happening now — current status explanation
- What you need to do — user action guidance
- What happens next — next steps
- CTA buttons per status

### Progress Timeline (Processing Only)
✔ Story received → ● Current stage → ○ Pending stages

### Asset Explanations (Completed Only)
- Script, Scenes, Voiceover, Final Video with descriptions

### "How this works" (Bottom of Page)
7-step collapsible explanation of the full process

## Admission Control System
- Per-user limit: MAX_ACTIVE_JOBS_PER_USER = 2
- System limit: MAX_TOTAL_ACTIVE_JOBS = 10
- Structured 429 responses with error_code, message, retry_after_seconds

## Idempotency System
- All generation request models have idempotency_key
- Frontend generates UUID per click action via genIdemKey()
- Backend checks existing job with same user_id + idempotency_key

## Backlog
### P0 (Immediate)
- Push Instagram traffic to /experience and collect 100+ paywall_shown events

### P1
- Paywall conversion analytics & optimization
- A/B test hook text variations
- Character-driven auto-share prompts after creation

### P2
- Explore Feed (TikTok-style scroll)
- Viral Story re-engagement hook
- WebSocket admin dashboard
- Story Chain leaderboard

## Test Credentials
- Admin: admin@creatorstudio.ai / Cr3@t0rStud!o#2026
- Test User: test@visionary-suite.com / Test@2026#
