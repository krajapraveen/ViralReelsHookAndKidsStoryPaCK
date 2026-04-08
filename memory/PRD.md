# Visionary Suite - Product Requirements Document

## Original Problem Statement
Build a full-stack AI Creator Suite with compulsion-driven growth engine, monetization, activation, conversion funnel, retention engine, content protection, and production-grade scale readiness. Latest mandate: Build the "sticky product" layer — re-engagement loops, credit psychology, time estimates, and trust-building UX.

## Architecture
```
/app/
├── backend/
│   ├── routes/
│   │   ├── instant_story.py                 # Zero-friction generation + multi-signal first-time detection
│   │   ├── story_video_generation.py        # Image/voice/video generation + admission control + idempotency + time-estimates endpoint
│   │   ├── story_video_studio.py            # Project CRUD with idempotent creation + strict auth
│   │   ├── funnel_tracking.py               # Funnel events
│   │   ├── system_health_api.py             # System health + Load Guard
│   │   └── pricing_api.py                   # Dynamic pricing
│   ├── services/
│   │   ├── admission_controller.py          # Load Guard
│   │   └── load_guard_alerts.py             # Slack alerts
│   └── security.py                          # Global rate limits
├── frontend/src/
│   ├── pages/
│   │   ├── InstantStoryExperience.jsx       # Demo + continuation + free-view + tooltip + paywall
│   │   ├── StoryPaywall.jsx                 # Full-screen paywall modal
│   │   ├── StoryVideoStudio.js              # Video creation with idempotency + admission control + refresh-safe resume
│   │   ├── MySpacePage.js                   # Full conversion UX with re-engagement, credit psychology, time estimates, failure recovery
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
6. Video Wait-Time Messaging
7. Onboarding Tooltip — Contextual conversion
8. Idempotent Project Creation — Prevents duplicate project rows
9. Proper list_projects — Auth-based user filtering
10. Admission Control — Per-user (2) and system-wide (10) job limits
11. Idempotent Generation + Structured 429 Responses
12. MySpace Plain-English UX Overhaul — Status-to-copy mapping, 4 info sections, progress timeline, asset explanations, "How this works" collapsible
13. Backend Auth Hardening — All test_user fallbacks eliminated
14. Refresh-Safe Job Resume — StoryVideoStudio polls /active-jobs on mount

### Latest: Conversion & Retention Layer (Completed 2026-04-08)
15. **Re-engagement Buttons** — "Make it funnier", "Change style", "Turn into reel", "Turn into storybook" on every completed card. Navigates to Studio with pre-filled remix state. Turns 1 generation → 3-5 generations.
16. **Credit Psychology** — "X credits" badge on completed card headers + "Generate another for just X credits · You have Y left" nudge below re-engagement buttons. Drives reuse.
17. **Dynamic Time Estimates** — Backend `/time-estimates` endpoint with rolling averages from last 50-100 jobs. Frontend shows fuzzy labels: "Almost ready", "About 1 minute left", "A few more minutes". Reduces refresh anxiety.
18. **Failure Recovery UX** — Amber encouragement box: "This usually works on retry. Tip: shorter stories generate faster and are less likely to fail." Reduces panic and drop-offs.
19. **Skeleton Loading** — Animated placeholder cards replace blank spinner during initial fetch. Eliminates perceived slowness.
20. **Completion Pulse** — Just-completed cards get pulse animation + bounce badge + auto-scroll. Draws attention.

## Key Endpoints
- `GET /api/story-video-studio/generation/time-estimates` — Rolling average durations per stage (public)
- `GET /api/story-video-studio/generation/active-jobs` — Resume active jobs (auth required)
- `GET /api/story-engine/user-jobs` — List user projects (auth required)
- `GET /api/credits/balance` — User credit balance (auth required)

## Backlog
### P0 (Immediate)
- Push Instagram traffic to /experience and collect 100+ paywall_shown events

### P1
- Paywall conversion analytics & optimization
- A/B test hook text variations

### P2
- Explore Feed (TikTok-style scroll) with "Remix This" buttons
- Viral Story re-engagement hook (comeback notifications & streaks)
- WebSocket admin dashboard
- Story Chain leaderboard

## Test Credentials
- Test User: test@visionary-suite.com / Test@2026#
- Admin: admin@creatorstudio.ai / Cr3@t0rStud!o#2026
