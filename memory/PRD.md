# Visionary Suite - Product Requirements Document

## Original Problem Statement
Build an AI Creator Suite with a compulsion-driven "Growth Engine" — a full-stack application featuring AI video generation, social sharing loops, and monetization via credits and payments. The platform must create irresistible user journeys with a multi-day retention engine that pulls creators back through notifications, email, challenges, and social proof.

## Architecture
- **Frontend**: React (CRA) + TailwindCSS + Shadcn/UI
- **Backend**: FastAPI + MongoDB + Redis
- **Integrations**: OpenAI (GPT-4o-mini, GPT Image 1, Sora 2, TTS), Gemini, Cloudflare R2, Cashfree, Google Auth, Resend (email)
- **Key URL**: https://trust-engine-5.preview.emergentagent.com

## Credentials
- Test: test@visionary-suite.com / Test@2026#
- Admin: admin@creatorstudio.ai / Cr3@t0rStud!o#2026

---

## What's Been Implemented

### Core Platform — DONE
- P0 Growth Loop, P1 Monetization, MySpace UX, Pipeline Resilience, Remix Gallery, Addiction Layer, Trust Fixes

### Retention, Digest, Prestige, A/B, Viral Flywheel Phases A/B/C — ALL DONE (Apr 9-10)

### Story Multiplayer Engine — DONE (Apr 11)
**Phase 1 — Data Model**: Graph fields on story_engine_jobs (root_story_id, chain_depth, continuation_type, battle_score). Ranking formula: (continues*5 + shares*3 + views*1) * depth_multiplier * recency_boost + anti-gaming. Testing: 29/29.

**Phase 2 — Episode vs Branch UI**: Replaced "Continue Story" with "Next Episode" + "Fork Story" dual CTAs. ContinuationModal.jsx. Testing: 100%.

**Phase 3 — StoryChain + Battle Screen**: StoryBattlePage (leaderboard, ranks, "Create Better Version"). StoryChainTimeline (timeline + branches). Testing: 100%.

**Phase 4 — Notifications + Feed**: rank_drop, version_outperformed, story_branched notifications with deep-links. Trending feed. Testing: 100%.

### Daily Story War — DONE (Apr 11)
**Phase A — Backend Engine**: `daily_wars` collection with strict states (scheduled→active→ended→winner_declared). War-local scoring (war_views, war_shares, war_continues — NOT lifetime metrics). Branch-only entries from daily root. Deterministic tie-break (war_score > continues > shares > earlier entered_at). Winner eligibility (20+ views AND 1+ engagement). War-specific overtake notifications (30min throttle). Endpoints: /api/war/current, /api/war/enter, /api/war/history, /api/war/yesterday, /api/war/increment-metric, /api/war/admin/seed, /api/war/admin/end. Testing: 28/28.

**Phase B — Frontend**: DailyWarPage at /app/war (war header, 24h countdown, Enter the War CTA, live-updating leaderboard with gap-to-#1, winner declaration, yesterday-rank re-entry). WarBanner on homepage with LIVE badge + countdown. NotificationBell handles war_overtake/war_won/war_ended. Testing: 100%.

### StoryChain Competition-First Redesign — DONE (Apr 11)
**Phase C**: Redesigned StoryChainTimeline to lead with competition. Above-the-fold: Player rank card (win/loss) + Winner Spotlight (#1 Version with metrics + "Beat This Version"). Below-the-fold: episode timeline + branches. Two modes: Player (rank + action) vs Viewer (social proof + Compete). "Beat This Version" opens pre-filled ContinuationModal. ContinuationModal isWar prop routes to /api/war/enter for war entries. Testing: 100%.

---

## Key Files

### Daily Story War
- `/app/backend/routes/daily_war.py` — War engine, lifecycle, scoring, notifications
- `/app/frontend/src/pages/DailyWarPage.jsx` — War experience page
- `/app/frontend/src/components/WarBanner.jsx` — Homepage war banner

### Story Multiplayer Engine
- `/app/backend/routes/story_multiplayer.py` — Core multiplayer routes, ranking, battle, feed
- `/app/frontend/src/components/ContinuationModal.jsx` — Episode/Branch/War confirmation modal
- `/app/frontend/src/pages/StoryBattlePage.jsx` — Competitive battle leaderboard
- `/app/frontend/src/pages/StoryChainTimeline.jsx` — Competition-first chain visualizer

### Core Platform
- `/app/backend/routes/story_engine_routes.py` — Story engine with multiplayer fields in status
- `/app/backend/services/story_engine/pipeline.py` — Pipeline with graph fields on create
- `/app/frontend/src/pages/StoryVideoPipeline.js` — Post-gen with Episode/Branch flows
- `/app/frontend/src/components/NotificationBell.js` — All notification types including war

---

## Prioritized Backlog

### P0 — Immediate
- Verify Resend domain for live email delivery (user action)

### P1 — Next
- Activate Phase C Gamification (pending GREENLIGHT threshold)
- Auto-seed daily wars (cron/scheduler instead of admin manual)
- Optimize viral loop conversion rates

### P2 — Growth & Polish
- A/B Week 2: test Variant C
- Public story chain leaderboard
- Monthly creator milestone digest
- Admin WebSocket upgrade

---

## Demo Data
- Battle chain: `battle-demo-root` (3 episodes + 3 branches)
- Active war: "The Starship Paradox" (seeded, 24h timer)
- Past war: "The Lost Temple of Echoes" (winner declared)
- URLs: `/app/war`, `/app/story-battle/battle-demo-root`, `/app/story-chain-timeline/battle-demo-root`
