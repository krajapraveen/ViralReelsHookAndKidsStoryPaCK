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

### P0 Failed Job Recovery — DONE (Apr 9)
- Server-authoritative view_mode routing, FailedRecoveryScreen, deep-link support

### Retention Layer (Releases 1 & 2) — DONE (Apr 9)
- In-App Notifications, Ownership Messaging, Daily Challenges, Soft Leaderboard, Mock Email, Resend email, auto-play hover preview, challenge badges

### Creator Digest — DONE (Apr 9)
- Weekly digest, smart skip, personalized CTA, admin controls

### Prestige + Quality Loop — DONE (Apr 9)
- Featured Challenge Winner Hero Slot, Improve Consistency CTA

### A/B Hero Headline Optimization — DONE (Apr 9)
- Experiment: hero_headline (Week 1), sticky assignment, traffic source tracking

### Traffic Source Segmentation + Auto-Share Prompts — DONE (Apr 9)

### Viral Flywheel Engine v1 — Phases A, B, C — DONE (Apr 9)
- Attribution tracking, remix lineage, rewards, leaderboard, emotional creator notifications, milestone badges, dark launch infrastructure

### P0 Dashboard Hero Story-Context Bug Fix — DONE (Apr 10)
### P1 Global Click Integrity Sweep — DONE (Apr 10)
### P1.5 UX Failure Recovery Sweep — DONE (Apr 10)
### P1.7 Payment & Billing Edge-Case Hardening Sweep — DONE (Apr 10)
### P1 Viral Optimization Sprint — DONE (Apr 10)
### GREENLIGHT Recovery Sprint — DONE (Apr 10)

### Story Multiplayer Engine — DONE (Apr 11)
**Goal:** Transform the platform from a standard AI content generator into an addictive "Story Multiplayer Engine" with viral network effects.

**Phase 1 — Data Model (Foundation)**
- Extended `story_engine_jobs` collection with graph fields: `root_story_id`, `chain_depth`, `continuation_type` ("original"|"episode"|"branch"), `total_children`, `total_views`, `total_shares`, `battle_score`
- Battle ranking formula: `(continues*5 + shares*3 + views*1) * depth_multiplier * recency_boost` with anti-gaming penalty
- New API endpoints: `POST /api/stories/continue-episode`, `POST /api/stories/continue-branch`, `GET /api/stories/{id}/chain`, `GET /api/stories/{id}/branches`, `GET /api/stories/battle/{id}`, `POST /api/stories/increment-metric`, `POST /api/stories/backfill-multiplayer`
- DB indexes for graph queries
- Testing: iteration_487 — 29/29 (100%)

**Phase 2 — Episode vs Branch UI Flows**
- Replaced generic "Continue Story" button with two distinct paths: "Next Episode" (violet/blue) + "Fork Story" (rose/orange)
- Built `ContinuationModal.jsx` — pre-generation confirmation modal for episode vs branch
- Auto-next trigger section updated with dual buttons
- Both flows call Phase 1 API endpoints
- Testing: iteration_488 — 100%

**Phase 3 — StoryChain Visualizer & Story Battle Screen**
- `StoryChainTimeline.jsx` — Hybrid timeline + branch visualizer at `/app/story-chain-timeline/:storyId`
  - Horizontal scrollable episode timeline
  - Vertical branch expansion on click
  - Branch ranking by battle_score
  - "Open Battle" and "View All Battles" deep-links
- `StoryBattlePage.jsx` — Competitive comparison at `/app/story-battle/:storyId`
  - #1 contender highlight with crown badge
  - User rank card with ego-driven messaging ("You're ranked #2 — can you take the top spot?")
  - Full leaderboard with scores, stats, creator names
  - "Create Better Version" CTA throughout
- Routes registered in App.js
- Testing: iteration_489 — 26/26 backend + all frontend (100%)

**Phase 4 — Notification & Feed Engine**
- Notification triggers: `rank_drop` ("You just lost #1 spot"), `version_outperformed` ("Your version is falling behind"), `story_branched` ("Someone forked your story")
- Throttling: rank_drop = 6h cap, version_outperformed = 24h cap
- Deep-links to Story Battle screen in all notifications
- NotificationBell updated with battle notification types, icons, colors, and deep-link navigation
- Trending feed endpoint: `GET /api/stories/feed/trending` — sorted by battle_score
- Testing: iteration_489 — included in Phase 3+4 test (100%)

---

## Email System Status
- **Provider**: Resend (wired, API key configured)
- **Status**: Infrastructure complete. Domain verification needed for non-owner delivery.

---

## Prioritized Backlog

### P0 — Immediate
- Verify Resend domain for live email delivery (user action)

### P1 — Next Features
- Activate Phase C Gamification: Dark Launched; gated behind GREENLIGHT threshold (currently HOLD)
- Optimize viral loop: improve share prompt conversion, share link CTR
- A/B Week 2: Winner of A vs B → test against Variant C (when threshold reached)

### P2 — Growth & Polish
- Monthly creator milestone digest
- "Remix Variants" on share pages
- Admin WebSocket upgrade
- Story Chain leaderboard (public)
- Personalized headline serving by channel

---

## Key Files

### Story Multiplayer Engine
- `/app/backend/routes/story_multiplayer.py` — Core multiplayer routes, ranking, notifications, feed
- `/app/frontend/src/components/ContinuationModal.jsx` — Episode vs Branch confirmation modal
- `/app/frontend/src/pages/StoryBattlePage.jsx` — Competitive battle leaderboard
- `/app/frontend/src/pages/StoryChainTimeline.jsx` — Timeline + branch visualizer

### Core Platform
- `/app/backend/routes/story_engine_routes.py` — Job APIs + view_mode + remix triggers
- `/app/backend/services/story_engine/pipeline.py` — Pipeline with multiplayer graph fields
- `/app/backend/routes/viral_flywheel.py` — Viral attribution, lineage, rewards
- `/app/backend/routes/phase_c_dark_launch.py` — Phase C Dark Launch
- `/app/frontend/src/pages/StoryVideoPipeline.js` — Studio + recovery + Episode/Branch flows
- `/app/frontend/src/components/NotificationBell.js` — Bell with battle notification types
- `/app/frontend/src/pages/Dashboard.js` — Challenge banner + Top Stories leaderboard
- `/app/frontend/src/pages/AdminDashboard.js` — Admin dashboard

### Demo Data
- Battle chain at `battle-demo-root` (3 episodes + 3 branches with varying scores)
- URLs: `/app/story-battle/battle-demo-root`, `/app/story-chain-timeline/battle-demo-root`
