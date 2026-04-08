# Visionary Suite - Product Requirements Document

## Original Problem Statement
Build a full-stack AI Creator Suite with compulsion-driven growth engine, monetization, activation, conversion funnel, retention engine, content protection, and production-grade scale readiness.

## Architecture
```
/app/
├── backend/
│   ├── routes/
│   │   ├── instant_story.py                 # Zero-friction generation + multi-signal first-time detection
│   │   ├── funnel_tracking.py               # All funnel events (fire-and-forget writes)
│   │   ├── story_video_studio.py            # Video creation + idempotent project creation + proper list_projects
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
│   │   ├── StoryVideoStudio.js              # Video creation with idempotency + 5-min wait
│   │   ├── Profile.js                       # User profile with improved In Progress section
│   │   └── Landing.js                       # CTAs → /experience
│   ├── components/
│   │   ├── WaitingExperience.js             # Progress card with video wait-time banner
│   │   └── GlobalUserBar.jsx               # Sticky profile dropdown
│   └── App.js                               # Routes
└── load-tests/
    └── results/LOAD_TEST_REPORT.md
```

## Completed Systems
1. Conversion Funnel (all events)
2. Smart Inline Paywall (dynamic pricing)
3. Retention Engine, Content Protection
4. Production Scale Readiness (queues + observability)
5. Load Guard / Kill Switch + Slack Alerts
6. Instant Demo Experience — zero-friction activation
7. Continue Story Loop + Smart Paywall
8. Load Testing — 3-phase (real LLM, mock infra, spike)
9. **First-Time Free Viewing (v2 - Hardened)** — Multi-signal detection, abuse prevention
10. **Video Wait-Time Messaging** — 5-min hardcoded message
11. **Onboarding Tooltip** — Contextual conversion on Parts 2-3
12. **Idempotent Project Creation** — Prevents duplicate project rows
13. **Proper list_projects** — Auth-based user filtering, parent-only, idempotency collapse
14. **Profile In Progress Cleanup** — Friendly stage labels, progress bars, delete buttons

## Idempotent Project Creation
- Frontend generates `idempotency_key` (crypto.randomUUID) per creation click
- Backend checks `story_projects` for existing record with same `user_id + idempotency_key`
- If found → returns existing project (no duplicate created)
- If not found → creates new project with the key
- DB index: `user_idempotency_idx` on (user_id, idempotency_key) for fast lookups
- Backward compatible: old projects without key treated as unique

## list_projects Improvements
- Extracts `user_id` from JWT auth token (was defaulting to "test_user")
- Filters to `parent_project_id: None` (parent-only, no branches)
- Collapses duplicates sharing same non-null `idempotency_key` (keeps most progressed)
- Pagination with `total` count in response

## First-Time Free Viewing (v2)
- Primary: device_token (localStorage), Secondary: user_id (JWT), Tertiary: IP hash
- ONE free story per device (Parts 1-3), then paywall
- Benefit record created immediately, persisted in `first_time_benefits` collection

## Backlog
### P0 (Immediate)
- Push Instagram traffic to /experience and collect 100+ paywall_shown events

### P1
- Paywall conversion analytics & optimization
- A/B test hook text variations on public pages

### P2
- Explore Feed: TikTok-style infinite scroll at /explore
- "Viral Story" re-engagement hook
- WebSocket admin dashboard

## Test Credentials
- Admin: admin@creatorstudio.ai / Cr3@t0rStud!o#2026
- Test User: test@visionary-suite.com / Test@2026#
