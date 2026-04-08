# Visionary Suite - Product Requirements Document

## Original Problem Statement
Build a full-stack AI Creator Suite with compulsion-driven growth engine, monetization, activation, conversion funnel, retention engine, content protection, and production-grade scale readiness.

## Architecture
```
/app/
├── backend/
│   ├── routes/
│   │   ├── system_health_api.py             # System health + Load Guard + Alert endpoints
│   │   ├── funnel_tracking.py               # Conversion funnel (updated with instant story events)
│   │   ├── instant_story.py                 # Zero-friction public story generation endpoint
│   │   └── pricing_api.py                   # Dynamic pricing
│   ├── services/
│   │   ├── worker_queues.py                 # 8 queues, fairness, dead-letter
│   │   ├── admission_controller.py          # Load Guard: trend-aware, queue-class, graded, hysteresis
│   │   └── load_guard_alerts.py             # Alert engine: Slack + DB persistence + dedup
│   └── server.py                            # Load Guard startup
├── frontend/src/
│   ├── pages/
│   │   ├── InstantStoryExperience.jsx       # Zero-friction demo-first landing experience (P0 COMPLETE)
│   │   ├── Dashboard.js                     # Admin top bar (z-[10001], always visible)
│   │   ├── Landing.js                       # CTAs wired to /experience route
│   │   ├── PublicCreation.js                # Continue CTAs wired to /experience route
│   │   └── AdminDashboard.js                # Full admin panel at /app/admin
│   ├── components/
│   │   ├── ProtectedContent.jsx             # Anti-copy deterrence
│   │   └── guide/JourneyProgressBar.jsx     # Hidden for admin users
│   └── App.js                               # Routes including /experience
└── load-tests/
    ├── mixed-workload.js                    # k6 mixed traffic
    └── RUNBOOK.md                           # Production runbook
```

## Instant Demo Experience (P0 - COMPLETE)
- **Problem**: 0% Story Created rate despite 13% landing conversion — users bounce at CTA click
- **Solution**: Zero-friction demo-first experience at /experience route
- **Flow**: CTA click → 800ms loading animation → hardcoded demo story renders → background LLM generation → auto-transition to real story with fade animation
- **Tracking**: demo_viewed, story_generation_started, story_generated_success/failed/timeout, cta_continue/video/share_clicked, login_prompt_shown
- **Failure Handling**: Demo stays visible, banner shows "Still personalizing your story...", 20s timeout
- **CTA**: Desktop inline + mobile sticky bottom, no scroll needed
- **Backend**: POST /api/public/quick-generate (no auth, rate limited 5/hr/IP)
- **Validation**: story_generated_success > 0 confirmed in production DB

## Load Guard System
- **Guard Modes**: NORMAL -> STRESSED -> SEVERE -> CRITICAL
- **Signals**: Queue wait time, depth trend, worker saturation, dead-letter growth, admission rate
- **Queue-Class Aware**: heavy/medium/light per-queue degradation
- **Hysteresis**: 3 min recovery hold, 2-3 min escalation sustain
- **Admin API**: GET/POST /api/admin/system-health/load-guard

## Alert System
- **Triggers**: mode escalation, recovery, flapping, dead-letter growth, stuck jobs, queue wait critical, manual override
- **Channels**: Slack webhook (SLACK_WEBHOOK_URL env var) + MongoDB persistence
- **Deduplication**: Per alert type + queue + mode, with cooldown bypass for worsening severity
- **Endpoints**: GET /alerts, /alerts/active, /alerts/summary
- **Testing**: 20/20 tests passed (iteration_459)

## Completed Systems
1. Conversion Funnel (11-step + micro-conversions + instant story events)
2. Smart Inline Paywall (dynamic pricing)
3. Retention Engine (Remix, Streak, Sticky CTA, Exit Interception)
4. Content Protection (deterrence + signed URLs + abuse detection)
5. Production Scale Readiness (queues + observability + k6)
6. Load Guard / Kill Switch (trend-aware, queue-class, graded, hysteresis)
7. Load Guard Alert System (Slack + DB + dedup + recovery alerts)
8. Admin Panel Visibility Fix (prominent admin bar, journey bar hidden for admins)
9. **Instant Demo Experience** (zero-friction activation, proven with tracking data)

## Backlog
### P0
- Execute production ramp tests (100->500->1K->3K->5K->10K)
- Time-limited discount overlay (20% off after 2+ paywall views)

### P1
- A/B test hook text on public pages
- Paywall Trust Signals (social proof strip)
- "Viral Story" re-engagement hook
- Comeback Notifications (streak reminders)
- Explore Feed (TikTok-style infinite scroll)

### P2
- Soft Loss Aversion on paywall close
- WebSocket admin dashboard upgrade

## Test Credentials
- Admin: admin@creatorstudio.ai / Cr3@t0rStud!o#2026
- Test User: test@visionary-suite.com / Test@2026#
