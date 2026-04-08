# Visionary Suite - Product Requirements Document

## Original Problem Statement
Build a full-stack AI Creator Suite with compulsion-driven growth engine, monetization, activation, conversion funnel, retention engine, content protection, and production-grade scale readiness.

## Architecture
```
/app/
├── backend/
│   ├── routes/
│   │   ├── instant_story.py                 # Zero-friction generation + multi-signal first-time detection
│   │   ├── story_video_generation.py        # Image/voice/video generation with admission control + idempotency
│   │   ├── story_video_studio.py            # Project CRUD with idempotent creation + auth-based list
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
│   │   ├── StoryVideoStudio.js              # Video creation with idempotency + admission control UX
│   │   ├── Profile.js                       # User profile with In Progress section (stage labels + delete)
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
5. **First-Time Free Viewing (v2)** — Multi-signal detection, abuse prevention
6. **Video Wait-Time Messaging** — 5-min hardcoded message
7. **Onboarding Tooltip** — Contextual conversion on Parts 2-3
8. **Idempotent Project Creation** — Prevents duplicate project rows
9. **Proper list_projects** — Auth-based user filtering, parent-only, idempotency collapse
10. **Profile In Progress Cleanup** — Friendly stage labels, progress bars, delete buttons
11. **Admission Control** — Per-user (2 active) and system-wide (10 active) job limits
12. **Idempotent Generation** — All generate endpoints (images/voices/video) reject duplicate requests
13. **Structured Error Responses** — 429 with USER_JOB_LIMIT / CAPACITY_EXCEEDED instead of generic 500

## Admission Control System
- **Per-user limit**: MAX_ACTIVE_JOBS_PER_USER = 2 (counts across generation_jobs + render_jobs)
- **System limit**: MAX_TOTAL_ACTIVE_JOBS = 10
- **Structured 429 responses**:
  - USER_JOB_LIMIT: "You already have video generations in progress. Please wait for one to finish."
  - CAPACITY_EXCEEDED: "Video generation is temporarily busy. Please try again in a few minutes."
  - Both include `retry_after_seconds` and actionable message
- Applied to: images, voices, video assembly endpoints

## Idempotency System
- All generation request models have `idempotency_key: Optional[str]`
- Frontend generates UUID per click action via `genIdemKey()`
- Backend checks existing job with same `user_id + idempotency_key` before creating
- If found → returns existing job (no duplicate creation, no duplicate credits)
- Covers: project creation, image gen, voice gen, video assembly

## Frontend Error Handling
- `handleGenerationError()` helper parses structured 429 responses
- Shows specific messages for USER_JOB_LIMIT (8s toast) and CAPACITY_EXCEEDED (10s toast)
- Falls back to generic message for unstructured errors
- Buttons disabled during submission (prevents double-click)

## Backlog
### P0 (Immediate)
- Push Instagram traffic to /experience and collect 100+ paywall_shown events

### P1
- Paywall conversion analytics & optimization
- A/B test hook text variations
- Admin observability dashboard for video generation (queued/active/failed/avg times)

### P2
- Explore Feed, Viral Story re-engagement hook, WebSocket admin dashboard

## Test Credentials
- Admin: admin@creatorstudio.ai / Cr3@t0rStud!o#2026
- Test User: test@visionary-suite.com / Test@2026#
