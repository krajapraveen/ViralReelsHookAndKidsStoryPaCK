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
### Acquisition: HottestBattle Spectator Mode (live battle -> "Jump In")
### Feed: Alert Strip -> Streak -> HottestBattle -> Hero -> War -> Continue Watching -> Trending -> Discover -> Your Creations

### Streak System — DONE (Apr 12)
- **Competition-based**: increments on battle/war/continuation participation (NOT login)
- **28h window** before reset (24h + 4h grace)
- **Boost**: +2%/day on battle_score, capped at 10% (5 days)
- **Milestones**: Rising(3), Legendary(5), Unstoppable(7), Mythic(14), Immortal(30)
- **Wired into**: continue-episode, continue-branch, instant-rerun, war-enter, quick-shot
- **Notifications**: milestone reached + streak-at-risk (push + in-app)
- **Frontend**: StreakBadge (full on homepage, compact on battle page)
- **Analytics**: streak_started, streak_incremented, streak_broken

### Entry Conversion Engine — DONE (Apr 12)
- **Quick Shot**: POST /api/stories/quick-shot — 1-tap zero-input entry into battle
  - Auto-generates competitive branch from root with random twist
  - Returns job_id, streak_started, current_streak
  - Records analytics (quick_shot_entry event)
- **Personalized CTA**: hottest-battle returns gap_continues_to_first, user_is_new, user_already_in_battle
  - "View Your Battle" (already in), "You can beat #1" (close race), "Try your first battle" (new user)
- **Spectator Pressure Timer**: After 6s of viewing, shows "Battle is heating up — Don't miss your chance"
  - IntersectionObserver-gated (only counts visible time)
  - Dismissible, fires quick-shot on "Jump In Now"
- **First-Win Boost**: Invisible 15% lift for users with 0-1 prior branch entries
  - In compute_battle_score via is_first_win_eligible param
  - refresh_battle_score checks prior_count against story_engine_jobs
- **Entry Streak Hook**: After first quick-shot, toast "Streak Started! Come back tomorrow"
- **Tracking**: spectator_impression, spectator_pressure_shown, spectator_quick_shot, spectator_to_player_conversion
- Testing: iteration_501 — 18/18 backend + all frontend verified (100%)

---

## System Integrity (Apr 12) — DONE
- Streak boost soft-capped at 10% (fairness rule)
- Auto-seed daily wars (never empty)
- FAILED_RENDER jobs excluded from rate limiter

---

## Key Files
- `/app/backend/routes/streaks.py` — Streak logic, participation recording, milestones
- `/app/frontend/src/components/StreakBadge.jsx` — Full + compact streak display
- `/app/frontend/src/components/HottestBattle.jsx` — Entry Conversion Engine (spectator -> player)
- `/app/frontend/src/components/CompetitionPulse.jsx` — Session loop with instant re-run
- `/app/frontend/src/components/PersonalAlertStrip.jsx` — Return trigger
- `/app/backend/routes/story_multiplayer.py` — Core multiplayer + feeds + instant-rerun + quick-shot
- `/app/backend/routes/daily_war.py` — War lifecycle + auto-seed
- `/app/backend/routes/push_notifications.py` — Push engine

---

## Backlog

### P0 (Completed)
- ~~Auto-seed daily wars via scheduler~~ DONE
- ~~Clean stuck FAILED_RENDER jobs~~ DONE
- ~~Apply streak_boost to battle_score~~ DONE
- ~~Entry Conversion Engine~~ DONE

### P1
- Secondary Action Matrix (Anime, Kids, Comic — deferred to avoid clutter)
- Follow Creator (network layer — deferred until competition density proven)
- Phase C Gamification activation (dark-launched, gated behind GREENLIGHT)
- Schedule check_streak_at_risk via periodic task

### P2
- Resend domain verification (blocked on user DNS action)
- Personalized headline serving by channel
- Admin WebSocket upgrade
- Public chain leaderboard
