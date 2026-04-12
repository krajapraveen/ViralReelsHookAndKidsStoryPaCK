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

### Engine: Story Multiplayer + Daily War + Cross-User Visibility + Attribution
### Actions: Episode/Branch flows, ContinuationModal with presets, all buttons wired
### Session Loop: CompetitionPulse (rank + gap + instant re-run, 20s polling)
### Intensity: Instant Re-run Engine (zero-friction one-tap, quality gate at 3)
### Return: PersonalAlertStrip + Push Notifications (rank_drop, war_overtake, near_win, war_winner)
### Feed: Alert Strip → HottestBattle → Hero → War → Continue Watching → Trending → Discover → Your Creations

### Spectator Mode — DONE (Apr 12)
- **Backend**: `GET /api/stories/hottest-battle` — aggregation finds root with most branches, returns top 3 contenders with scores, near_win flag, gap_to_first
- **Frontend**: `HottestBattle.jsx` — live battle spectator on homepage
  - Red pulse "LIVE BATTLE" indicator + battle title + 3 competing
  - Top 3 leaderboard with crown/rank, creator names, scores
  - Rank movement animations (emerald up, rose down) on 12s polling
  - Near-win highlight when gap ≤ 5 pts
  - "Jump Into Battle" CTA → upgrades to "You can beat this — Jump In" after 5s viewing
  - spectator_to_player_conversion analytics tracked
- Testing: iteration_498 — 19/19 (100%)

---

## Key Files
- `/app/frontend/src/components/HottestBattle.jsx` — Spectator mode (acquisition)
- `/app/frontend/src/components/CompetitionPulse.jsx` — Session loop with instant re-run
- `/app/frontend/src/components/PersonalAlertStrip.jsx` — Return trigger
- `/app/frontend/src/components/ContinuationModal.jsx` — Episode/Branch/War modal
- `/app/backend/routes/story_multiplayer.py` — All multiplayer + feeds + instant-rerun + hottest-battle
- `/app/backend/routes/daily_war.py` — War lifecycle
- `/app/backend/routes/push_notifications.py` — Push engine

---

## Backlog

### P0
- Streak tracking (daily habit reinforcement)
- Auto-seed daily wars via scheduler

### P1
- Follow Creator (network layer)
- Phase C Gamification activation
- Clean stuck FAILED_RENDER jobs

### P2
- Resend domain, A/B Week 2, public chain leaderboard
