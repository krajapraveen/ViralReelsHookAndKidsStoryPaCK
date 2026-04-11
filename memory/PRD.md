# Visionary Suite - Product Requirements Document

## Architecture
- **Frontend**: React (CRA) + TailwindCSS + Shadcn/UI
- **Backend**: FastAPI + MongoDB + Redis
- **Integrations**: OpenAI, Gemini, Cloudflare R2, Cashfree, Google Auth, Resend
- **URL**: https://trust-engine-5.preview.emergentagent.com

## Credentials
- Test: test@visionary-suite.com / Test@2026#
- Admin: admin@creatorstudio.ai / Cr3@t0rStud!o#2026

---

## Completed Work

### Story Multiplayer Engine — DONE (Apr 11)
- Graph data model, Episode vs Branch UI, StoryBattlePage, StoryChainTimeline, notifications, trending feed

### Daily Story War — DONE (Apr 11)
- daily_wars collection, strict states, war-local scoring, branch-only, tie-breaks, winner declaration

### StoryChain Competition-First Redesign — DONE (Apr 11)
- Winner spotlight above-fold, Player vs Viewer modes, "Beat This Version" → pre-filled ContinuationModal

### Consumption vs Creation UX Fix — DONE (Apr 11)
- StoryViewerPage, Dashboard card routing split (CONTINUE→viewer, TRENDING→studio)

### Phase 1 — Story Visibility + Cross-User Access + Attribution — DONE (Apr 11)
- **Visibility model**: `public | unlisted | private` on every story. Default: `public`. Drafts: `private`.
- **Cross-user access**: Any logged-in user can view, continue, remix, fork any public story. Private blocked for non-owners.
- **Attribution**: `derivative_label` (continued_from, remixed_from, styled_from, converted_from), `source_story_title`, `source_creator_name` on all derivatives. Visible in StoryViewerPage as badge.
- **Discover feed**: `GET /api/stories/feed/discover` — ALL public stories from ALL users, paginated, sortable (latest/trending/most_continued)
- **Continue Watching feed**: `GET /api/stories/feed/continue-watching` — cross-user watch history (stories user has viewed, regardless of creator)
- **Watch history tracking**: Viewer endpoint auto-tracks in `watch_history` collection
- **Visibility management**: `POST /api/stories/set-visibility` (owner only), `POST /api/stories/backfill-visibility` (admin)
- Testing: iteration_493 — 29/29 (100%)

### Phase 2A — Core Action Integrity — DONE (Apr 11)
- **Rewired all dead buttons** to use ContinuationModal with preset instructions (not dead studio navigation):
  - Add Twist → branch mode, "Add unexpected plot twist" instruction
  - Make Funny → branch mode, "Convert to comedy version" instruction
  - Next Episode → episode mode, "Continue storyline forward" instruction
  - Try to beat this → branch mode, "Create stronger competing version" instruction
  - Improve yours → branch mode, "Refine and improve your version" instruction
  - More dramatic / Shorter / Faster-paced / More emotional → branch mode with tone-specific instructions
- **Share buttons**: Copy Link fires `copied_link` analytics, all share buttons fire `share_clicked`. Instagram/Story uses native `navigator.share` API with clipboard fallback.
- **Analytics**: Every action fires tracking event via `/api/funnel/track`
- Testing: iteration_493 — included in Phase 1 test, 100%

---

## Key Files

### Visibility + Attribution
- `/app/backend/routes/story_multiplayer.py` — visibility enforcement, discover/continue-watching feeds, set-visibility, viewer with attribution
- `/app/backend/services/story_engine/pipeline.py` — visibility='public' default, attribution fields

### Action Integrity
- `/app/frontend/src/pages/StoryVideoPipeline.js` — rewired Add Twist, Make Funny, Next Episode, variation chips, battle buttons
- `/app/frontend/src/components/ContinuationModal.jsx` — preset prop for pre-filled title+instruction
- `/app/frontend/src/pages/StoryViewerPage.jsx` — attribution badge, creator_name display

### Daily War + Battle
- `/app/backend/routes/daily_war.py`, `/app/frontend/src/pages/DailyWarPage.jsx`, `/app/frontend/src/components/WarBanner.jsx`
- `/app/frontend/src/pages/StoryBattlePage.jsx`, `/app/frontend/src/pages/StoryChainTimeline.jsx`

---

## Prioritized Backlog

### P0 — Phase 2B (Secondary Action Matrix)
- Style remix cards (Anime, 3D Animation, Watercolor, Comic Book, Claymation)
- Quick Variations (Funny, Dramatic, Anime Style, Short Version, Regenerate)
- Second-row actions (Change Style, Create Part 2, Different Animation Style, Funny/Kids Version, Remix Prompt)
- Convert Creation (Short Reel Version, Turn Into Comic)

### P1 — Phase 3 (Feed + Discovery Cleanup)
- Homepage sections: Continue Watching, Trending Now, Daily Story War, Recommended, Your Creations
- Card creator attribution visible
- Clear CTA separation on cards

### P2 — Maintenance
- Auto-seed daily wars via scheduler
- Activate Phase C Gamification
- Verify Resend domain
- A/B Week 2

---

## Demo Data
- Battle chain: `battle-demo-root` (3 episodes + 3 branches)
- Past war: "The Lost Temple of Echoes" (winner declared)
- Active war: "The Starship Paradox" (24h timer)
- URLs: /app/war, /app/story-battle/battle-demo-root, /app/story-chain-timeline/battle-demo-root, /app/story-viewer/battle-demo-root
