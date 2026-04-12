# Visionary Suite - Product Requirements Document

## Architecture
- **Frontend**: React (CRA) + TailwindCSS + Shadcn/UI
- **Backend**: FastAPI + MongoDB + Redis
- **URL**: https://trust-engine-5.preview.emergentagent.com

## Credentials
- Test: test@visionary-suite.com / Test@2026#
- Admin: admin@creatorstudio.ai / Cr3@t0rStud!o#2026

---

## Completed (Apr 11-12)

### Story Multiplayer Engine — Graph, Battle, Chain, Notifications, Feed
### Daily Story War — Lifecycle, scoring, winner declaration, war page + banner
### Consumption vs Creation — StoryViewerPage, card routing split
### Phase 1 — Visibility (public/unlisted/private) + Cross-User Access + Attribution
### Phase 2A — Core Action Integrity — All buttons wired to ContinuationModal
### Phase 2B — CompetitionPulse (session loop) + style/variation rewiring
### Phase 3 — Feed as Return Engine — PersonalAlertStrip, TrendingPublicFeed, YourCreationsStrip

### Push Notifications (Loss-Aversion) — DONE (Apr 12)
- **Service Worker** at `/sw-push.js` — handles push events + click deep-link navigation
- **Backend**: subscribe/unsubscribe endpoints, rate-limited push delivery (max 3/day, 2h cooldown)
- **Only 4 triggers**: rank_drop, war_overtake, near_win (gap ≤ 2), war_winner
- **Integrated**: rank_drop + near_win in `story_multiplayer.py`, war_overtake in `daily_war.py`
- **Frontend**: `usePushNotifications` hook (auto-subscribe), `PushPrompt` component (non-intrusive, 7-day dismiss cooldown)
- Testing: iteration_496 — 37/37 (100%)

---

## Key Files
- `/app/backend/routes/push_notifications.py` — Push engine with rate limits
- `/app/frontend/public/sw-push.js` — Service Worker
- `/app/frontend/src/hooks/usePushNotifications.js` — Push subscription hook
- `/app/frontend/src/components/PushPrompt.jsx` — Permission prompt
- `/app/frontend/src/components/PersonalAlertStrip.jsx` — Return trigger
- `/app/frontend/src/components/CompetitionPulse.jsx` — Session loop
- `/app/frontend/src/components/ContinuationModal.jsx` — Episode/Branch/War modal
- `/app/backend/routes/story_multiplayer.py` — All multiplayer + feeds + push triggers
- `/app/backend/routes/daily_war.py` — War lifecycle + push triggers

---

## Backlog

### P0
- Session depth: "One more try" loop after every action (fast re-run, no modal friction)
- Streak tracking (after return behavior proven)

### P1
- Auto-seed daily wars via scheduler
- Phase C Gamification activation
- Follow Creator system

### P2
- Resend domain verification, A/B Week 2, public chain leaderboard
