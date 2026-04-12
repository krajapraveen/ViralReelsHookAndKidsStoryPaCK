# Visionary Suite - Product Requirements Document

## Architecture
- **Frontend**: React (CRA) + TailwindCSS + Shadcn/UI
- **Backend**: FastAPI + MongoDB + Redis
- **URL**: https://trust-engine-5.preview.emergentagent.com

## Credentials
- Test: test@visionary-suite.com / Test@2026#
- Admin: admin@creatorstudio.ai / Cr3@t0rStud!o#2026

---

## Completed Work

### Story Multiplayer Engine (Phases 1-4) — DONE
### Daily Story War — DONE
### Consumption vs Creation UX Fix — DONE
### Phase 1 — Visibility + Cross-User Access + Attribution — DONE
### Phase 2A — Core Action Integrity — DONE
### Phase 2B — Loop-Based UX + CompetitionPulse — DONE
### Phase 3 — Feed as Return Engine — DONE (Apr 12)

**PersonalAlertStrip** — THE return trigger at top of homepage:
- Priority-ranked alerts: war_overtake(12), rank_drop(10), war_losing(9), outperformed(8), war_won(6), trending_opportunity(3)
- Shows rank changes ("You dropped to #2"), war position ("You're #3, 6h left"), exploding stories ("X is exploding — can you beat it?")
- Each alert has action CTA: "Take Back Rank", "Fight Back", "Compete", "Enter War"
- Max 2 alerts shown, highest urgency first

**TrendingPublicFeed** — Public stories from ALL users:
- Grid of 4 trending cards with thumbnails, creator names, engagement metrics
- HOT badge for high-engagement stories (3+ continues or 50+ battle_score)
- Attribution for derivatives ("Continued from", "Remixed from")

**YourCreationsStrip** — User's stories with competitive position:
- Shows rank + engagement metrics for each story

**Homepage Section Order**:
1. PersonalAlertStrip (return trigger)
2. Hero
3. Daily Story War banner
4. Continue Watching (cross-user)
5. Trending Now (all public)
6. Fresh Stories
7. TrendingPublicFeed (discover)
8. Your Creations
9. Leaderboard

Testing: iteration_495 — 25/25 backend + all frontend (100%)

---

## Key Files
- `/app/frontend/src/components/PersonalAlertStrip.jsx` — Return trigger
- `/app/frontend/src/components/TrendingPublicFeed.jsx` — Public stories grid
- `/app/frontend/src/components/YourCreationsStrip.jsx` — User stories with rank
- `/app/frontend/src/components/CompetitionPulse.jsx` — Session compulsion loop
- `/app/frontend/src/components/ContinuationModal.jsx` — Episode/Branch/War modal
- `/app/frontend/src/components/WarBanner.jsx` — Homepage war banner
- `/app/frontend/src/pages/Dashboard.js` — Integrated all feed sections
- `/app/frontend/src/pages/StoryVideoPipeline.js` — All actions wired
- `/app/frontend/src/pages/StoryViewerPage.jsx` — Consumption with attribution
- `/app/frontend/src/pages/DailyWarPage.jsx` — War experience
- `/app/frontend/src/pages/StoryBattlePage.jsx` — Battle leaderboard
- `/app/frontend/src/pages/StoryChainTimeline.jsx` — Competition-first chain
- `/app/backend/routes/story_multiplayer.py` — All multiplayer endpoints
- `/app/backend/routes/daily_war.py` — War lifecycle

---

## Prioritized Backlog

### P0
- Streak tracking (after feed proves return behavior)
- Follow Creator system (after engagement loops proven)

### P1
- Auto-seed daily wars via scheduler
- Activate Phase C Gamification
- Verify Resend domain

### P2
- A/B Week 2, public chain leaderboard, monthly digest
