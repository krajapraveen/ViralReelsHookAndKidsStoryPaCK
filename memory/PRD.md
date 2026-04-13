# Visionary Suite - Product Requirements Document

## Architecture
- **Frontend**: React (CRA) + TailwindCSS + Shadcn/UI
- **Backend**: FastAPI + MongoDB + Redis
- **URL**: https://trust-engine-5.preview.emergentagent.com

## Credentials
- Test: test@visionary-suite.com / Test@2026#
- Admin: admin@creatorstudio.ai / Cr3@t0rStud!o#2026

---

## Core Philosophy: WATCH > ENTER BATTLE > CREATE

---

## WIN/LOSS Moments + Real-Time Pulse — DONE (Apr 13)

### Battle Pulse System (GET /api/stories/battle-pulse/{rootId}):
- Polls every 12s for live battle state
- Returns: total entries, user rank, top 3, recent activity, active rendering count
- **WIN moment**: "YOU'RE #1 RIGHT NOW — You just beat everyone" (gold Crown + animation)
- **Rank up**: "You climbed to #N — Up from #M" (emerald)
- **LOSS pain**: "You dropped to #N — Someone just beat your entry — Share or improve to climb back" (rose)
- Rank change detection via `battle_rank_cache` collection (compares previous vs current)
- 5-second auto-dismiss on moments

### Real-Time Activity Feed:
- "Admin User entered 26m ago" — shows entries from last 60 minutes
- "4 entries generating right now" — active rendering indicator
- Green pulse dot — "LIVE ACTIVITY" header

### Second Action Rate (North Star Metric):
- **40%** — 2 out of 5 creators did 2+ actions
- Verdict: "potential" (>20%, <40% = potential; >40% = strong)
- Formula: users_with_2+_jobs / total_creators * 100
- Added to analytics dashboard

### Files:
- `/app/backend/routes/story_multiplayer.py` — battle-pulse endpoint
- `/app/frontend/src/components/BattlePulse.jsx` — WIN/LOSS + activity feed
- `/app/backend/routes/analytics_dashboard.py` — second_action_rate metric

---

## All Systems (Apr 12-13)
- Queue System, Data Integrity, Export Pipeline
- Consumption-First Loop, Entry Conversion Engine
- Analytics Dashboard + Funnel Integrity
- Auto-play, Social proof, Competitive copy
- Instant dopamine, Continuous tension, Identity/ranking
- WIN/LOSS moments, Real-time battle pulse
- Viral share prompts, Return triggers

---

## Backlog

### P0 (Data-driven)
- Monitor: 2nd action rate, CTR, session time
- Validate WIN/LOSS moments trigger correctly on rank changes

### P1
- Push notification for rank changes
- Auto-Recovery FAILED_PERSISTENCE

### P2
- Resend domain, personalized headlines
