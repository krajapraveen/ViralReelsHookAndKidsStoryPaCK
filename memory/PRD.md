# Visionary Suite - Product Requirements Document

## Original Problem Statement
Build an AI Creator Suite with a compulsion-driven "Growth Engine" — a full-stack application featuring AI video generation, social sharing loops, and monetization via credits and payments.

## Architecture
- **Frontend**: React (CRA) + TailwindCSS + Shadcn/UI
- **Backend**: FastAPI + MongoDB + Redis
- **Integrations**: OpenAI, Gemini, Cloudflare R2, Cashfree, Google Auth, Resend
- **URL**: https://trust-engine-5.preview.emergentagent.com

## Credentials
- Test: test@visionary-suite.com / Test@2026#
- Admin: admin@creatorstudio.ai / Cr3@t0rStud!o#2026

---

## What's Been Implemented

### Core Platform — DONE
- P0 Growth Loop, Monetization, MySpace UX, Pipeline Resilience, Remix Gallery, Addiction Layer, Trust Fixes

### Retention/Digest/Prestige/A/B/Viral Flywheel — ALL DONE (Apr 9-10)

### Story Multiplayer Engine — DONE (Apr 11)
- Phase 1: Graph data model (root_story_id, chain_depth, continuation_type, battle_score). Ranking: (continues*5+shares*3+views*1)*depth*recency with anti-gaming. 7 new API endpoints.
- Phase 2: "Next Episode" + "Fork Story" dual CTA replacing generic "Continue". ContinuationModal.jsx.
- Phase 3: StoryBattlePage (leaderboard, ranks, "Create Better Version"). StoryChainTimeline (competition-first).
- Phase 4: rank_drop, version_outperformed, story_branched notifications with deep-links. Trending feed.

### Daily Story War — DONE (Apr 11)
- Phase A: `daily_wars` collection, strict states (scheduled→active→ended→winner_declared), war-local scoring, branch-only entries, deterministic tie-breaks, winner eligibility, overtake notifications.
- Phase B: DailyWarPage (/app/war), 24h countdown, Enter the War CTA, live-updating leaderboard, yesterday-rank re-entry. WarBanner on homepage.

### StoryChain Competition-First Redesign — DONE (Apr 11)
- Winner spotlight above-the-fold, Player vs Viewer modes, timeline below fold. "Beat This Version" opens pre-filled ContinuationModal.

### Consumption vs Creation UX Fix — DONE (Apr 11)
- **Problem**: "Continue watching" cards routed to editor/remix (creation), breaking user intent.
- **Fix**: Built StoryViewerPage.jsx at /app/story-viewer/:jobId — consumption-first page with video player, story text, episode navigation, and secondary creation CTAs.
- Dashboard card routing: CONTINUE → /app/story-viewer (consumption), TRENDING/NEW → /app/story-video-studio (creation).
- Public viewer API: GET /api/stories/viewer/{story_id} — no ownership check.
- CTA text: CONTINUE → "Continue watching", others → "Create your version".
- Testing: iteration_492 — 8/8 backend + 100% frontend + no regressions.

---

## Key Files

### Story Viewer (Consumption)
- `/app/frontend/src/pages/StoryViewerPage.jsx` — Consumption-first viewer
- `/app/backend/routes/story_multiplayer.py` — GET /api/stories/viewer/{id}

### Daily Story War
- `/app/backend/routes/daily_war.py` — War engine, lifecycle, scoring
- `/app/frontend/src/pages/DailyWarPage.jsx` — War experience
- `/app/frontend/src/components/WarBanner.jsx` — Homepage banner

### Story Multiplayer
- `/app/backend/routes/story_multiplayer.py` — Multiplayer routes, ranking, battle, feed
- `/app/frontend/src/components/ContinuationModal.jsx` — Episode/Branch/War modal
- `/app/frontend/src/pages/StoryBattlePage.jsx` — Battle leaderboard
- `/app/frontend/src/pages/StoryChainTimeline.jsx` — Competition-first chain viz

### Core
- `/app/frontend/src/pages/Dashboard.js` — Card routing fix, WarBanner
- `/app/frontend/src/pages/StoryVideoPipeline.js` — Post-gen Episode/Branch flows
- `/app/frontend/src/components/NotificationBell.js` — All notification types

---

## Prioritized Backlog

### P0
- Verify Resend domain for live email delivery (user action)

### P1
- Auto-seed daily wars via scheduler
- Activate Phase C Gamification (pending GREENLIGHT)
- Optimize viral loop conversion rates

### P2
- A/B Week 2 (Variant C)
- Public story chain leaderboard
- Monthly creator digest
- Admin WebSocket upgrade

---

## Demo Data
- Battle chain: `battle-demo-root` (3 episodes + 3 branches)
- Active war: "The Starship Paradox"
- Past war: "The Lost Temple of Echoes"
- URLs: /app/war, /app/story-battle/battle-demo-root, /app/story-chain-timeline/battle-demo-root, /app/story-viewer/battle-demo-root
