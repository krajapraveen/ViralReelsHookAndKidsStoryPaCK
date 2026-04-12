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
Every surface enforces this hierarchy. No direct creation from homepage.

---

## Consumption-First Viral Loop — DONE (Apr 12)

### Phase 0: Baseline Tracking
- Added funnel events: story_viewed, story_card_clicked, watch_started, watch_completed_50, watch_completed_100, cta_clicked, remix_clicked, create_clicked, scroll_depth_50
- Spectator events: spectator_impression, spectator_pressure_shown, spectator_quick_shot, spectator_to_player_conversion
- All events tracked via POST /api/funnel/track

### Phase 1: CTA Restructure
- **Hero**: Watch Now (primary gradient) > Make Your Version (secondary outline) > Create Later (tertiary text)
- **All Cards**: Click → /app/story-viewer/{jobId} (Watch Page). NOT creation studio.
- **Card CTA Labels**: "Watch Now" (trending/fresh/new), "Continue watching" (continue), "Watch Story" (unfinished)
- **"Create your version" ELIMINATED** from entire homepage
- **Floating Create CTA**: Appears bottom-right only after 50% scroll depth or 1+ video watched
- Testing: iteration_502 — 19/19 (100%)

### Phase 2: Watch Page Upgrade
- **Next Episode**: Big primary CTA (violet gradient, full-width)
- **Make Your Version**: Secondary CTA (rose accent, with "Put your own spin" subtext)
- **Engagement Row**: Like, Save, Share buttons (with state tracking)
- **Remix Chain**: "People also remixed this into:" horizontal scroll cards
- **Auto-Play Next**: 3-second countdown overlay after video ends, with Cancel button
- **Video Tracking**: watch_completed_50 at 50% progress, watch_completed_100 at end
- **Attribution**: Shows "Quick shot from" alongside existing derivative labels

---

## Entry Conversion Engine — DONE (Apr 12)
- Quick Shot (1-tap zero-input battle entry)
- Personalized CTA (gap-to-#1, user state)
- Spectator Pressure Timer (6s urgency prompt)
- First-Win Boost (invisible 15% lift for new users)
- Entry Streak Hook ("Streak Started!" toast)
- Testing: iteration_501 — 18/18 (100%)

## System Integrity — DONE (Apr 12)
- Streak boost soft-capped at 10%
- Auto-seed daily wars
- FAILED_RENDER excluded from rate limiter

---

## Key Files
- `/app/frontend/src/pages/Dashboard.js` — Consumption-first homepage (Watch > Remix > Create)
- `/app/frontend/src/pages/StoryViewerPage.jsx` — Watch page with engagement, auto-play, remix chain
- `/app/frontend/src/components/HottestBattle.jsx` — Entry Conversion Engine
- `/app/backend/routes/story_multiplayer.py` — Core multiplayer + quick-shot + feeds
- `/app/backend/routes/funnel_tracking.py` — Full funnel tracking with consumption events
- `/app/backend/routes/daily_war.py` — War lifecycle
- `/app/backend/routes/streaks.py` — Streak system
- `/app/backend/routes/push_notifications.py` — Push engine

---

## Backlog

### P0 (Next: Analytics Engine)
- Conversion Analytics Dashboard (admin): Spectator->Player %, best CTA, avg session time, retention
- CTA variant performance tracking
- Quick Shot quality validation
- Pressure timer bounce validation
- First-win boost retention impact

### P1
- Secondary Action Matrix (Anime, Kids, Comic)
- Follow Creator (network layer)
- Phase C Gamification activation

### P2
- Resend domain verification (blocked on user DNS)
- Personalized headline serving
- Admin WebSocket upgrade
- Hover autoplay preview on cards (micro-interaction)
