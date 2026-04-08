# Visionary Suite - Product Requirements Document

## Original Problem Statement
Build a full-stack AI Creator Suite with compulsion-driven growth engine, monetization, activation, conversion funnel, retention engine, content protection, and production-grade resilience. Core mandate: Build network effects through a remix-driven engagement loop.

## Architecture
```
/app/
├── backend/
│   ├── routes/
│   │   ├── gallery_routes.py                # Remix Gallery feed + remix action + quality filtering + seeding
│   │   ├── remix_routes.py                  # Remix tracking
│   │   ├── story_video_generation.py        # Generation + admission control + time-estimates
│   │   ├── story_video_studio.py            # Project CRUD with strict auth
│   │   └── instant_story.py                 # First-time free viewing
│   ├── services/
│   │   └── story_engine/
│   │       └── pipeline.py                  # Resilient pipeline with character context fallback
│   └── server.py
├── frontend/src/
│   ├── components/
│   │   └── RemixGallery.js                  # Reusable remix gallery (3 placements)
│   ├── pages/
│   │   ├── MySpacePage.js                   # Full conversion UX + Remix Gallery
│   │   ├── StoryVideoStudio.js              # Studio with remix banner + waiting gallery
│   │   └── StoryVideoPipeline.js            # Soft recovery error UX
```

## Completed Systems (Cumulative)
1-14. Backend stability, UX clarity, retention loops, auth hardening (see previous PRD versions)

### Conversion & Retention Layer (2026-04-08)
15. Re-engagement buttons (4 variants on completed cards)
16. Credit psychology (badge + nudge)
17. Dynamic time estimates (rolling averages + fuzzy labels)
18. Failure recovery UX (encouraging copy + tips)
19. Skeleton loading (animated placeholders)
20. Completion pulse (bounce badge + auto-scroll)

### Pipeline Resilience (2026-04-08)
21. Character context fallback (graceful degradation, not fatal failure)
22. Soft error UX (amber "needs a quick fix" instead of red "Generation Issue")
23. Retry as primary CTA (never "Start Fresh" as primary)

### Remix Gallery MVP (2026-04-08)
24. **Gallery Feed API** — `GET /api/gallery/remix-feed` with quality filtering (has thumbnail, non-empty description, title >= 3 chars), sorted by remix_count DESC
25. **Remix Action API** — `POST /api/gallery/{item_id}/remix` increments count, returns pre-filled Studio data
26. **3 Placement Points**:
    - MySpace: "People are remixing these" (8 cards between Completed and Create Another)
    - CompletionPromptModal: "Try what others created" (3 cards after share/download buttons)
    - During Wait: "While you wait… remix a trending story" (4 cards during generation)
27. **Remix Cards** — Thumbnail, title, description, remix count badge, views count, hover "Remix This" overlay
28. **Competitive Nudge** — "Can you make a better version?" below gallery
29. **Remix Banner in Studio** — "You're remixing a trending story" with original title + remix count (shown when source === 'remix_gallery')
30. **Quality-Filtered Seeding** — Auto-seed gallery with 20+ curated items, filtered for quality

## Key Growth Mechanics
```
User generates → Sees result → Sees remix gallery → Clicks "Remix This" 
→ Studio pre-fills → Generates variation → Repeat
```
**Target:** 1 generation → 3-5 generations per session

## Backlog
### P0 (Immediate)
- Push Instagram traffic to /experience, collect 100+ paywall_shown events

### P1
- Paywall conversion analytics & optimization
- A/B test hook text variations
- "Your version vs. popular version" comparison after remix generation
- Streak system ("You created 3 stories today")

### P2
- Character consistency system (embeddings + seed control)
- Explore Feed (TikTok-style scroll)
- Viral Story re-engagement hook
- WebSocket admin dashboard
- Story Chain leaderboard
- User opt-in gallery sharing

## Test Credentials
- Test User: test@visionary-suite.com / Test@2026#
- Admin: admin@creatorstudio.ai / Cr3@t0rStud!o#2026
