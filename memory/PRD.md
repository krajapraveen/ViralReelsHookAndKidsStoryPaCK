# Visionary Suite - Product Requirements Document

## Original Problem Statement
Build a full-stack AI Creator Suite with compulsion-driven growth engine, monetization, activation, conversion funnel, retention engine, content protection, and production-grade scale readiness.

## Architecture
```
/app/
├── backend/
│   ├── routes/
│   │   ├── instant_story.py                 # Zero-friction story generation + first-time free viewing check
│   │   ├── funnel_tracking.py               # All funnel events (fire-and-forget writes)
│   │   ├── story_video_studio.py            # Video creation pipeline
│   │   ├── system_health_api.py             # System health + Load Guard
│   │   └── pricing_api.py                   # Dynamic pricing
│   ├── services/
│   │   ├── admission_controller.py          # Load Guard
│   │   └── load_guard_alerts.py             # Slack alerts
│   └── security.py                          # Global rate limits (slowapi)
├── frontend/src/
│   ├── pages/
│   │   ├── InstantStoryExperience.jsx       # Demo + continuation loop + paywall + first-time free viewing
│   │   ├── StoryPaywall.jsx                 # Full-screen paywall modal
│   │   ├── StoryVideoStudio.js              # Video creation with 5-min wait messaging
│   │   └── Landing.js                       # CTAs → /experience
│   ├── components/
│   │   ├── WaitingExperience.js             # Progress card with video wait-time banner
│   │   └── GlobalUserBar.jsx               # Sticky profile dropdown
│   └── App.js                               # Routes
└── load-tests/
    ├── phase1-real-llm.js
    ├── phase2-mock-infra.js
    ├── phase3-spike.js
    └── results/LOAD_TEST_REPORT.md
```

## Completed Systems
1. Conversion Funnel (all events)
2. Smart Inline Paywall (dynamic pricing)
3. Retention Engine
4. Content Protection
5. Production Scale Readiness (queues + observability)
6. Load Guard / Kill Switch + Slack Alerts
7. **Instant Demo Experience** — zero-friction activation
8. **Continue Story Loop** — Part 2 generation addiction loop
9. **Smart Paywall** — story hostage paywall with exit offer + discount
10. **Load Testing** — 3-phase (real LLM, mock infra, spike)
11. **First-Time Free Viewing** — New users get Parts 1-3 free at /experience, persisted via backend IP check
12. **Video Wait-Time Messaging** — Hardcoded 5-min message in toast, progress card, and estimated time

## First-Time Free Viewing Details
- Backend: `allow_free_view` flag returned by `POST /api/public/quick-generate`
- Logic: Checks `instant_stories` collection for records from other session IDs with same IP hash
- New IP (no previous sessions) → `allow_free_view: true`
- Returning IP → `allow_free_view: false`
- Frontend: `allowFreeView` state in InstantStoryExperience.jsx
- Parts 1-3 free for first-time users, Part 4+ shows paywall
- Soft upgrade CTA banner after Part 3 (not modal)
- Download/video/share remain gated (require login)
- DB-persisted (not frontend memory), survives refresh/reload

## Video Wait-Time Messaging
- Exact copy: "Your story video is being created. This usually takes at least 5 minutes. While it's processing, feel free to explore other features."
- Applied in: Toast (10s duration), WaitingExperience banner, estimatedTime prop
- Safe-to-leave messaging: "Your video is safely processing in the background — you can leave this page."

## Load Test Results Summary
- **Safe capacity (1 worker)**: 10-20 concurrent users
- **Degradation starts**: 50+ concurrent users
- **System never crashes** — graceful degradation
- **Production recommendation**: Scale to 4-8 uvicorn workers = 200-800 concurrent users
- Full report: `/app/load-tests/results/LOAD_TEST_REPORT.md`

## Backlog
### P0 (Immediate)
- Push Instagram traffic to /experience and collect 100+ paywall_shown events

### P1
- Paywall conversion analytics & optimization (price split, hook testing, drop-off analysis)
- A/B test hook text variations on public pages
- Separate tracking microservice
- CloudFlare CDN deployment

### P2
- Explore Feed: TikTok-style infinite scroll at /explore with "Remix This" buttons
- "Viral Story" re-engagement hook (comeback notifications & streak reminders)
- WebSocket admin dashboard
- LLM request queue (Redis-backed)

## Test Credentials
- Admin: admin@creatorstudio.ai / Cr3@t0rStud!o#2026
- Test User: test@visionary-suite.com / Test@2026#
