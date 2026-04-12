# Visionary Suite - Product Requirements Document

## Architecture
- **Frontend**: React (CRA) + TailwindCSS + Shadcn/UI
- **Backend**: FastAPI + MongoDB + Redis
- **URL**: https://trust-engine-5.preview.emergentagent.com

## Credentials
- Test: test@visionary-suite.com / Test@2026#
- Admin: admin@creatorstudio.ai / Cr3@t0rStud!o#2026

---

## Complete Behavior System (Apr 11-12)

### Engine Layer
- Story Multiplayer Engine (graph, battle, chain, ranking)
- Daily Story War (lifecycle, scoring, winner declaration)
- Cross-user visibility (public/unlisted/private) + attribution

### Action Layer
- Episode vs Branch dual flows, ContinuationModal with presets
- All buttons wired (Add Twist, Make Funny, Next Episode, Beat #1, Improve, variations, styles)
- Consumption vs Creation split (StoryViewerPage vs Studio)

### Loop Layer
- CompetitionPulse (live rank + gap-to-#1 + instant re-run CTAs, 20s polling)
- Instant Re-run Engine: POST /api/stories/instant-rerun — zero-friction one-tap regeneration
  - try_again: reuses story text + random variation suffix, generates immediately
  - beat_top: includes #1's story as competitive context in prompt
  - Quality gate: after 3 reruns, shows warning + "Add Twist Instead"
  - Session depth tracking in rerun_tracker collection

### Trigger Layer
- PersonalAlertStrip (return trigger on homepage — rank drops, war overtakes, trending)
- Push Notifications via Service Worker (rank_drop, war_overtake, near_win, war_winner)
  - Rate limited: 3/day, 2h cooldown
  - Deep-links to Battle/War screens

### Feed Layer
- Homepage: Alert Strip → Hero → War → Continue Watching → Trending → Discover → Your Creations
- TrendingPublicFeed (all users' public stories with HOT badges)
- YourCreationsStrip (user stories with rank)

---

## Key Files
- `/app/backend/routes/story_multiplayer.py` — Core multiplayer + feeds + instant-rerun + push triggers
- `/app/backend/routes/daily_war.py` — War lifecycle + push triggers
- `/app/backend/routes/push_notifications.py` — Push engine with rate limits
- `/app/frontend/src/components/CompetitionPulse.jsx` — Session intensity loop with instant re-run
- `/app/frontend/src/components/PersonalAlertStrip.jsx` — Return trigger
- `/app/frontend/src/components/ContinuationModal.jsx` — Episode/Branch/War modal with presets
- `/app/frontend/src/pages/StoryVideoPipeline.js` — Post-gen with all actions wired
- `/app/frontend/src/pages/DailyWarPage.jsx` — War experience
- `/app/frontend/src/pages/StoryBattlePage.jsx` — Battle leaderboard
- `/app/frontend/src/pages/StoryViewerPage.jsx` — Consumption with attribution
- `/app/frontend/src/pages/Dashboard.js` — Feed sections

---

## Backlog

### P0
- Streak tracking (daily habit reinforcement)
- Follow Creator (network layer)

### P1
- Auto-seed daily wars
- Phase C Gamification
- Clean stuck FAILED_RENDER jobs (blocking rate limiter for instant reruns)

### P2
- Resend domain, A/B Week 2, public chain leaderboard
