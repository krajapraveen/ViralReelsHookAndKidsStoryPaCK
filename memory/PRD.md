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
### Session Loop: CompetitionPulse + Instant Re-run Engine (zero-friction)
### Return: PersonalAlertStrip + Push Notifications (loss-aversion)
### Acquisition: HottestBattle Spectator Mode (live battle → "Jump In")
### Feed: Alert Strip → Streak → HottestBattle → Hero → War → Continue Watching → Trending → Discover → Your Creations

### Streak System — DONE (Apr 12)
- **Competition-based**: increments on battle/war/continuation participation (NOT login)
- **28h window** before reset (24h + 4h grace)
- **Boost**: +2%/day on battle_score, capped at 10% (5 days)
- **Milestones**: Rising(3), Legendary(5), Unstoppable(7), Mythic(14), Immortal(30)
- **Wired into**: continue-episode, continue-branch, instant-rerun, war-enter
- **Notifications**: milestone reached + streak-at-risk (push + in-app)
- **Frontend**: StreakBadge (full on homepage, compact on battle page)
- **Analytics**: streak_started, streak_incremented, streak_broken
- Testing: iteration_499 — 31/31 (100%)

---

## Key Files
- `/app/backend/routes/streaks.py` — Streak logic, participation recording, milestones
- `/app/frontend/src/components/StreakBadge.jsx` — Full + compact streak display
- `/app/frontend/src/components/HottestBattle.jsx` — Spectator mode (acquisition)
- `/app/frontend/src/components/CompetitionPulse.jsx` — Session loop with instant re-run
- `/app/frontend/src/components/PersonalAlertStrip.jsx` — Return trigger
- `/app/backend/routes/story_multiplayer.py` — Core multiplayer + feeds + instant-rerun
- `/app/backend/routes/daily_war.py` — War lifecycle
- `/app/backend/routes/push_notifications.py` — Push engine

---

## Backlog

### P0
- Auto-seed daily wars via scheduler
- Clean stuck FAILED_RENDER jobs (blocking instant reruns)
- Apply streak_boost to actual battle_score calculation

### P1
- Follow Creator (network layer)
- Phase C Gamification activation
- Schedule check_streak_at_risk via periodic task

### P2
- Resend domain, A/B Week 2, public chain leaderboard
