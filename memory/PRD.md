# Visionary Suite - Product Requirements Document

## Architecture
- **Frontend**: React (CRA) + TailwindCSS + Shadcn/UI
- **Backend**: FastAPI + MongoDB
- **Payments**: Cashfree (production + sandbox)
- **URL**: https://trust-engine-5.preview.emergentagent.com

## Credentials
- Test: test@visionary-suite.com / Test@2026#
- Admin: admin@creatorstudio.ai / Cr3@t0rStud!o#2026

---

## Core Philosophy: WATCH > ENTER BATTLE > GENERATE > COMPETE > PAY

## All Completed Systems (Latest First)

### User Traffic Readiness Sprint (Apr 14)
- **Funnel Tracking V3**: Added 7 critical events (`typing_started`, `generate_clicked`, `generation_completed`, `postgen_cta_clicked`, `battle_enter_clicked`, `session_started`, `session_ended`) to backend whitelist and frontend wiring.
- **Session Time Tracking**: `useSessionTracker` hook fires `session_started` on mount, `session_ended` via `sendBeacon` on tab close/visibility change with `duration_seconds`.
- **Dedup Guards**: `typingStartedRef` prevents duplicate `typing_started` events on React rerenders. `createLockRef` prevents duplicate generation.
- **R2 Media Proxy**: Created `/api/media/r2/{path}` route that generates presigned URLs for R2 assets (bucket not publicly accessible). Presigned URLs cached for 1 hour. All hero videos and thumbnails now load correctly.
- **Landing CTA Update**: Changed "Create Your First Video — Free" to "Create Your Story & Take #1 Spot" for competitive positioning on Instagram cold traffic.
- **Media URL Safety**: Applied `safeMediaUrl()` to all direct R2 URLs in LiveBattleHero (video/poster) and Dashboard (winner thumbnail, leaderboard thumbnails).

### Master QA Execution (Apr 14)
- 114 tests across 4 layers: Smoke (20/20), Regression (69/69), Negative/Failure (25/25 after fix).
- Found & fixed XSS in `/api/drafts/save` — applied `sanitize_input()`.
- Verdict: CONDITIONALLY READY.

### Content Seeding Sprint (Apr 14)
- 30 real videos with output URLs and thumbnails (26 seeded + 4 from testing).
- Hero video: "The Countdown Begins" (200 battle score).

### Previous Sprints
- Emotional Copy + Battle Hero Autoplay (Apr 14)
- Studio Creation Engine V2 (Apr 14)
- P0.5 Performance Hardening (Apr 14): 7 API calls -> 1, load 5s -> 1.8s
- P0 Performance Sprint: Code splitting, TTL caching
- CTA Route Separation, UX Trust Fixes, Google Sign-In Fix (Apr 13)
- All psychology layers, WIN/LOSS moments, BattlePulse, Push Notifications
- Battle Paywall Modal (Cashfree inline)
- Free Entry Limit Enforcement

---

## Funnel Tracking (V3 — Production Ready)

### Critical 7 Events
| Event | Where Fired | Dedup | Storage |
|-------|-------------|-------|---------|
| `session_started` | App.js (mount) | useRef | funnel_events |
| `session_ended` | App.js (beforeunload/visibilitychange) | sendBeacon | funnel_events |
| `typing_started` | StoryVideoPipeline.js (first keystroke) | typingStartedRef | funnel_events |
| `generate_clicked` | StoryVideoPipeline.js (handleGenerate) | createLockRef | funnel_events |
| `generation_completed` | StoryVideoPipeline.js (COMPLETED status) | poll-based | funnel_events |
| `postgen_cta_clicked` | StoryVideoPipeline.js (post-gen CTAs) | click-based | funnel_events |
| `battle_enter_clicked` | LiveBattleHero + StoryVideoPipeline.js | click-based | funnel_events |

### How to Query (DB)
```javascript
db.funnel_events.aggregate([
  { $match: { timestamp: { $gte: "2026-04-14" } } },
  { $group: { _id: "$step", count: { $sum: 1 } } },
  { $sort: { count: -1 } }
])
```

### How to Query (Admin API)
```
GET /api/funnel/metrics?days=7
Authorization: Bearer <admin_token>
```

---

## Key Files
- `/app/backend/routes/funnel_tracking.py` — Event tracking API
- `/app/backend/routes/r2_proxy.py` — R2 media proxy (NEW)
- `/app/frontend/src/utils/useSessionTracker.js` — Session tracking hook (NEW)
- `/app/frontend/src/utils/funnelTracker.js` — Client-side funnel tracker
- `/app/frontend/src/components/SafeImage.jsx` — `safeMediaUrl()` for R2 URL proxying

---

## Backlog

### P0 (Immediate)
- Push 20-50 real users via Instagram reel
- Observe: % typing start, % generate, % post-gen CTA, % battle entry, avg session time

### P1
- Optimize thresholds based on traffic data (near-win gap, ₹19 tier)
- WebP/AVIF image optimization
- Auto-Recovery for FAILED_PERSISTENCE jobs

### P2
- Category-specific AI hook selection
- Replace asyncio with Celery
- Admin WebSocket upgrade
- Resend domain verification (blocked on DNS)
- QA Health Dashboard (after 100+ users)
