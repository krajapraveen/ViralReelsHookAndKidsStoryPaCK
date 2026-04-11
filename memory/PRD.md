# Visionary Suite - Product Requirements Document

## Architecture
- **Frontend**: React (CRA) + TailwindCSS + Shadcn/UI
- **Backend**: FastAPI + MongoDB + Redis
- **URL**: https://trust-engine-5.preview.emergentagent.com

## Credentials
- Test: test@visionary-suite.com / Test@2026#
- Admin: admin@creatorstudio.ai / Cr3@t0rStud!o#2026

---

## Completed Work (Apr 11)

### Story Multiplayer Engine (Phases 1-4)
- Graph data model, Episode vs Branch UI, StoryBattlePage, StoryChainTimeline (competition-first), notifications, trending feed

### Daily Story War
- daily_wars collection, strict states, war-local scoring, branch-only, tie-breaks, winner declaration, DailyWarPage, WarBanner

### Consumption vs Creation UX Fix
- StoryViewerPage, Dashboard card routing split (CONTINUE→viewer, TRENDING→studio)

### Phase 1 — Story Visibility + Cross-User Access + Attribution
- Visibility model: `public | unlisted | private`. Cross-user access enforced. Attribution on all derivatives.
- Discover feed, Continue Watching feed (cross-user), watch history tracking.

### Phase 2A — Core Action Integrity
- Rewired Add Twist, Make Funny, Next Episode, Try to beat, Improve yours, variation chips to ContinuationModal with preset instructions + analytics.

### Phase 2B — Loop-Based UX + CompetitionPulse
- **CompetitionPulse component**: Live rank + gap-to-#1 + re-engagement CTAs. Polls every 20s.
  - Winner state: "YOU ARE #1" celebration + View Battle/View Chain
  - Competitor state: rank number, gap (pts + continues), #1 leader preview, "Try Again" + "Beat #1"
  - Rank change alerts: "You moved up" (emerald) / "You dropped" (rose) with animation
- Style remix cards (Anime, 3D, Watercolor, Comic Book, Claymation) → ContinuationModal with style instructions
- Accordion continuation options → ContinuationModal with presets
- Create Entirely New Story → fires analytics
- CreationActionsBar (Quick Variations, Convert Creation) → functional via trackAndNavigate system

---

## Key Files
- `/app/frontend/src/components/CompetitionPulse.jsx` — Live compulsion loop
- `/app/frontend/src/components/ContinuationModal.jsx` — Episode/Branch/War modal with preset support
- `/app/frontend/src/pages/StoryVideoPipeline.js` — All actions wired, CompetitionPulse integrated
- `/app/frontend/src/pages/StoryViewerPage.jsx` — Consumption with attribution
- `/app/frontend/src/pages/DailyWarPage.jsx` — War experience
- `/app/frontend/src/pages/StoryBattlePage.jsx` — Battle leaderboard
- `/app/frontend/src/pages/StoryChainTimeline.jsx` — Competition-first chain
- `/app/backend/routes/story_multiplayer.py` — Visibility, feeds, battle, attribution
- `/app/backend/routes/daily_war.py` — War lifecycle

---

## Prioritized Backlog

### P0 — Phase 3 (Feed + Discovery Cleanup)
- Homepage sections: Continue Watching (user history + cross-user), Trending Now (all public), Daily Story War, Recommended, Your Creations
- Card creator attribution visible
- Clear CTA separation on cards

### P1
- Auto-seed daily wars via scheduler
- Activate Phase C Gamification
- Follow Creator system (after engagement loops proven)
- Verify Resend domain

### P2
- A/B Week 2, public chain leaderboard, monthly digest
