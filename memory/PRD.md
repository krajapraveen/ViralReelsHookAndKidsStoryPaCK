# Visionary Suite - Product Requirements Document

## Architecture
- **Frontend**: React (CRA) + TailwindCSS + Shadcn/UI
- **Backend**: FastAPI + MongoDB + Redis
- **URL**: https://trust-engine-5.preview.emergentagent.com

## Credentials
- Test: test@visionary-suite.com / Test@2026#
- Admin: admin@creatorstudio.ai / Cr3@t0rStud!o#2026

---

## Core Philosophy: WATCH > MAKE YOUR VERSION > CREATE

---

## Conversion Analytics Dashboard — DONE (Apr 12)

### Route: /app/admin/conversion (admin only)
### Backend: GET /api/analytics/conversion-dashboard?period=24h|7d|30d

**Metrics (all from real events/state transitions):**
- Spectator → Player % (formula: spectator_conversions + quick_shots / impressions * 100)
- Watch Start Rate (watch_started / story_card_clicked * 100)
- Watch 50% / 100% Completion
- Stories per Session
- Make Your Version CTR, Quick Shot CTR, Next Episode CTR
- Queue Rate (QUEUED / total_created * 100)
- Queue → Complete Rate

**Funnel (with drop-off %):**
impression → card_click → watch_start → watch_50 → watch_100 → create_click → entry_created → queued → completed

**Breakdowns:**
- CTA variant clicks (watch_now, make_your_version, quick_shot, next_episode, etc.)
- Source section clicks (TRENDING, CONTINUE, FRESH, UNFINISHED)
- Session stats (unique sessions, unique users)

**Files:**
- `/app/backend/routes/analytics_dashboard.py` — Backend analytics endpoint
- `/app/frontend/src/pages/ConversionDashboard.jsx` — Admin dashboard UI

---

## Completed Systems (All Apr 12)
- Queue System (hardened): QUEUED state, FIFO, drain on success+failure, no double billing
- Unfinished Worlds fix (viewer checks pipeline_jobs)
- Post-Launch-Branch flow (battle entry experience)
- Data Integrity (completed = persisted)
- Export Pipeline fix
- Consumption-First Viral Loop
- Entry Conversion Engine
- System Integrity (streaks, wars, rate limiter)

---

## Backlog

### P1
- Auto-Recovery FAILED_PERSISTENCE
- Secondary Action Matrix (Anime, Kids, Comic)
- Follow Creator / Network Graph

### P2
- Resend domain verification
- Personalized headlines by channel
- Hover autoplay previews
- Admin WebSocket upgrade
