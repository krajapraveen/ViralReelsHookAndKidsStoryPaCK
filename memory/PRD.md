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
│   │   ├── story_video_studio.py            # Video creation with 5-min wait messaging
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
│   │   ├── StoryVideoStudio.js              # Video creation with 5-min wait messaging
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
3. Retention Engine
4. Content Protection
5. Production Scale Readiness (queues + observability)
6. Load Guard / Kill Switch + Slack Alerts
7. **Instant Demo Experience** — zero-friction activation
8. **Continue Story Loop** — Part 2 generation addiction loop
9. **Smart Paywall** — story hostage paywall with exit offer + discount
10. **Load Testing** — 3-phase (real LLM, mock infra, spike)
11. **First-Time Free Viewing (v2 - Hardened)** — Multi-signal detection (device_token + user_id + IP), abuse prevention
12. **Video Wait-Time Messaging** — 5-min hardcoded message in toast, progress, estimated time
13. **Onboarding Tooltip** — Contextual conversion prompt on Parts 2-3 for first-time users

## First-Time Free Viewing (v2 - Hardened)
### Detection: Multi-Signal (not IP-only)
- **Primary**: `device_token` (generated in localStorage, persists across sessions)
- **Secondary**: `user_id` (extracted from JWT if user is logged in)
- **Tertiary**: `ip_hash` (catches VPN/device-change abuse)
- Stored in `first_time_benefits` MongoDB collection

### Abuse Prevention
- ONE free story per device (Parts 1-3 only)
- Same session + continue mode → allowed (continuing free story)
- Same session + fresh mode (2nd story) → BLOCKED
- Different session → BLOCKED
- New device, same IP → BLOCKED (IP secondary signal)
- VPN/new IP, same device → BLOCKED (device_token primary)
- Benefit record created IMMEDIATELY on first fresh generation (prevents concurrent abuse)

### Soft Monetization
- Soft upgrade CTA banner after Part 3 (non-modal)
- Primary: "Upgrade to download, create more, and unlock premium quality"
- Secondary: "Continue exploring for free"
- Download, video, share remain gated (require login/payment)

## Onboarding Tooltip
- **Trigger**: allowFreeView=true AND viewing Part 2 or 3 AND 5-10 seconds on screen
- **Copy**: "You're seeing this for free / Upgrade to download, create more, and unlock premium quality"
- **Behavior**: Non-blocking, auto-dismiss after 7 seconds, CTA gets enhanced pulse animation
- **Tracked**: free_view_tooltip_shown funnel event

## Video Wait-Time Messaging
- Exact copy: "Your story video is being created. This usually takes at least 5 minutes. While it's processing, feel free to explore other features."
- Applied in: Toast (10s duration), WaitingExperience banner, estimatedTime prop
- Safe-to-leave: "Your video is safely processing in the background — you can leave this page."

## Key DB Collections
- `first_time_benefits`: device_token, user_id, ip_hash, benefit_session_id, created_at
- `instant_stories`: story records with ip_hash, session_id
- `funnel_events`: journey tracking
- `instant_story_requests`: rate limiting (5/hour/IP)

## Backlog
### P0 (Immediate)
- Push Instagram traffic to /experience and collect 100+ paywall_shown events

### P1
- Paywall conversion analytics & optimization (price split, hook testing, drop-off)
- A/B test hook text variations on public pages

### P2
- Explore Feed: TikTok-style infinite scroll at /explore with "Remix This"
- "Viral Story" re-engagement hook (comeback notifications & streak)
- WebSocket admin dashboard

## Test Credentials
- Admin: admin@creatorstudio.ai / Cr3@t0rStud!o#2026
- Test User: test@visionary-suite.com / Test@2026#
