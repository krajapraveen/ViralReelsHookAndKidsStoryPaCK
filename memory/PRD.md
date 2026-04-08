# Visionary Suite - Product Requirements Document

## Original Problem Statement
Build a full-stack AI Creator Suite with compulsion-driven growth engine, network effects through remix-driven engagement loops, and addiction mechanics (competitive comparison, instant variants, streaks).

## Architecture
```
/app/
├── backend/routes/
│   ├── gallery_routes.py          # Remix Gallery feed + remix action + quality filtering
│   ├── story_video_generation.py  # Generation + admission control + time-estimates
│   ├── story_video_studio.py      # Project CRUD with strict auth
│   └── instant_story.py           # First-time free viewing
├── backend/services/story_engine/
│   └── pipeline.py                # Resilient pipeline with character context fallback
├── frontend/src/
│   ├── components/
│   │   └── RemixGallery.js        # Reusable remix gallery with trending badges
│   ├── pages/
│   │   ├── MySpacePage.js         # Full conversion UX + Remix Gallery + Session Streak
│   │   ├── StoryVideoPipeline.js  # Post-gen: Competitive Comparison + Instant Remix Variants
│   │   └── StoryVideoStudio.js   # Studio with remix banner + waiting gallery
```

## Completed Systems (Cumulative)

### Foundation (Previous Sessions)
1-14. Backend stability, UX clarity, auth hardening, admission control, idempotency

### Conversion & Retention Layer
15. Re-engagement buttons (4 variants on completed cards)
16. Credit psychology (badge + nudge on cards)
17. Dynamic time estimates (rolling averages + fuzzy labels)
18. Failure recovery UX (encouraging copy)
19. Skeleton loading + Completion pulse

### Pipeline Resilience
20. Character context fallback (graceful degradation)
21. Soft error UX (amber, not red; Retry primary, Start Fresh secondary)

### Remix Gallery MVP
22. Gallery Feed API with quality filtering
23. Remix Action API (increment count + return pre-filled Studio data)
24. 3 Placement Points: MySpace, CompletionModal, During-Wait

### Addiction Layer (Latest — 2026-04-08)
25. **Competitive Comparison** — "Can you beat this version?" with side-by-side thumbnails (Your version vs. Trending), "Try to beat this" + "Improve yours" CTAs
26. **Instant Remix Variants** — 4 one-click buttons: "More dramatic", "Shorter", "Faster-paced", "More emotional" (stores remix data + navigates to Studio)
27. **Trending Badges** — Trending (>=10K), Popular (>=5K), Rising (>=1K) on gallery cards
28. **Time-Bound Copy** — "X remixed today" instead of "X remixes" (creates urgency)
29. **Session Streak** — "You've created X videos today — keep going" (visible when todayCount >= 1)

## Growth Loop Architecture
```
User generates → Sees result → Sees "Can you beat this?" → Clicks Remix/Beat
→ Studio pre-fills → One-click variant → Generates again → Session streak grows
→ Repeat (target: 3-5 generations per session)
```

## Backlog
### P0
- Push Instagram traffic to /experience, collect 100+ paywall_shown events

### P1
- Paywall conversion analytics & optimization
- A/B test hook text variations
- Auto-play preview on gallery hover

### P2
- Character consistency system (embeddings + seed control)
- Explore Feed (TikTok-style scroll)
- Viral Story re-engagement hook
- User opt-in gallery sharing
- WebSocket admin dashboard

## Test Credentials
- Test User: test@visionary-suite.com / Test@2026#
- Admin: admin@creatorstudio.ai / Cr3@t0rStud!o#2026
