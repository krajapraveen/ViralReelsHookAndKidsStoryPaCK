# Story Universe Engine — Product Requirements Document

## Original Problem Statement
Build a "Story Universe Engine" — a full-stack AI creator suite with growth engine, monetization, and viral sharing. The core mandate is a production-grade, mobile-first UI with Netflix-level media delivery, a locked-down visual contract, and deterministic homepage personalization.

## Core Architecture
- Frontend: React (CRA + Craco) on port 3000
- Backend: FastAPI on port 8001
- Database: MongoDB
- Storage: Cloudflare R2 (all media via same-origin streaming proxy)
- Payments: Cashfree
- AI: OpenAI GPT-4o-mini, Sora 2, TTS + Gemini 3 via Emergent LLM Key

## Deterministic Media Pipeline (IMPLEMENTED — Mar 30 2026)
- FFmpeg extracts frame, Pillow generates thumbnail_small (400x530) + poster_large (1280x720)
- Stored in nested `media` object in DB
- Feed API returns `media.thumbnail_small_url`, `media.poster_large_url`, `media.preview_short_url`, `media.media_version: "v3"`

## Frontend Component Contract (IMPLEMENTED — Mar 30 2026)
- **HeroMedia.jsx** — Hero poster (eager, high priority, blur-up, fallback)
- **StoryCardMedia.jsx** — Card thumbnail (thumbnail_small -> poster_large -> fallback)
- **MediaPreloader.jsx** — Preloads hero poster + first 4 thumbnails only
- **Dashboard.js** — DUMB RENDERER: maps over API-provided rows[] and features[]

## Visual Contract (IMPLEMENTED — Mar 30 2026)

### Design Tokens
- Page background: `#0B0B0F`
- Card background: `#121218`
- Accent gradient: `#6C5CE7` -> `#00C2FF`
- Fallback gradients: `#2A1E5C`, `#0F5C7A`, `#1D7A45`

### Hero
- Container: `h-[58vh] sm:h-[64vh] lg:h-[72vh] bg-[#0B0B0F]`
- Blur: `blur-2xl opacity-70 scale-105`
- Overlay: `from-black/55 via-black/20 to-transparent`
- Bottom fade: `h-40 from-black/70 to-transparent`
- Badge: `bg-white/15 backdrop-blur-md border border-white/20`
- Title: `font-extrabold tracking-tight drop-shadow-[0_2px_12px_rgba(0,0,0,0.45)]`
- CTAs: Primary gradient with `shadow-[0_0_24px_rgba(0,194,255,0.28)]`, secondary glass

### Story Cards
- Sizes: `w-[160px] h-[220px] sm:w-[200px] sm:h-[280px] lg:w-[220px] lg:h-[300px]`
- Style: `rounded-2xl border border-white/[0.08] shadow-[0_10px_32px_rgba(0,0,0,0.18)]`
- Hover: `hover:scale-[1.02] hover:shadow-[0_16px_40px_rgba(0,0,0,0.28)]`

## Deterministic Homepage Personalization (IMPLEMENTED — Mar 30 2026)

### Architecture
- Backend owns ALL ordering — frontend is a dumb renderer
- Pure deterministic math — NO ML, NO embeddings, NO LLM recommenders
- Event-driven profile updates with 0.98 decay multiplier
- Cold start threshold: 5 events minimum for personalization

### Story Scoring Formula
```
story_score = (0.30 × category_affinity) + (0.20 × continue_rate)
            + (0.15 × completion_rate) + (0.10 × share_rate)
            + (0.10 × freshness_score) + (0.10 × momentum_score)
            + (0.05 × global_trending_score)
```

### Event Weights
```
card_click=1  watch_start=2  continue_click=5  watch_complete=8
share_click=10  generation_start=6  generation_complete=12
```

### Feature Scoring Formula
```
feature_score = (0.50 × feature_affinity) + (0.25 × recent_usage)
              + (0.15 × success_rate) + (0.10 × monetization_priority)
```

### Row Priority Rules
- IF user has active stories → continue_stories = rank 1
- ELSE IF high continue_rate → trending = rank 1
- ELSE → fresh = rank 1

### API Contract (GET /api/engagement/story-feed)
```json
{
  "personalization": { "enabled": bool, "profile_strength": float, "event_count": int },
  "hero": { ...story object },
  "rows": [{ "key": str, "title": str, "icon": str, "icon_color": str, "stories": [...] }],
  "features": [{ "name": str, "desc": str, "icon": str, "path": str, "key": str, "score": float }],
  "live_stats": { "stories_today": int, "total_stories": int }
}
```

### DB Schema: user_homepage_profile
- user_id (indexed, unique)
- category_affinity: dict (e.g., {"watercolor": 0.96, "cartoon_2d": 0.23})
- feature_affinity: dict (e.g., {"story-video-studio": 0.96})
- behavior_metrics: dict (total_clicks, total_continues, continue_rate, completion_rate, share_rate)
- recent_activity: list (last 100 events with weights)
- counts: dict (total_events, last_updated)

## Key Files
- `/app/frontend/src/components/HeroMedia.jsx`
- `/app/frontend/src/components/StoryCardMedia.jsx`
- `/app/frontend/src/components/MediaPreloader.jsx`
- `/app/frontend/src/pages/Dashboard.js`
- `/app/frontend/src/utils/growthTracker.js`
- `/app/backend/routes/engagement.py`
- `/app/backend/routes/growth_analytics.py`
- `/app/backend/services/personalization_service.py`
- `/app/backend/services/story_engine/adapters/media_gen.py`

## Test Credentials
- Test User: test@visionary-suite.com / Test@2026#
- Admin User: admin@creatorstudio.ai / Cr3@t0rStud!o#2026

## Completed
- [x] Deterministic media pipeline (Pillow + FFmpeg)
- [x] Nested media DB schema + backfill (61 jobs)
- [x] Feed API nested media object (media_version: v3)
- [x] HeroMedia, StoryCardMedia, MediaPreloader components
- [x] Dashboard rewrite with contract components
- [x] Visual contract — exact Tailwind/CSS class system
- [x] Deterministic homepage personalization (scoring engine, profile updates, ranked rows/features)
- [x] Event-driven profile ingestion via growth_events hooks
- [x] Cold start fallback logic
- [x] MongoDB indexes for user_homepage_profile
- [x] Frontend updated to dumb renderer (maps over API rows[] and features[])
- [x] Tested: Backend 17/17, Frontend 100% (iteration 381)

## Upcoming Tasks
- (P1) A/B rollout flag (10% personalized, 90% default)
- (P1) Blurhash/thumb_blur generation for instant perception
- (P1) Preview_short video generation for Netflix autoplay
- (P1) CDN-first delivery optimization
- (P2) "Remix Variants" on share pages
- (P2) Admin dashboard WebSocket upgrade
- (P2) Story Chain leaderboard
