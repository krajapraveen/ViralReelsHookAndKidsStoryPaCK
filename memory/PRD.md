# Story Universe Engine — Product Requirements Document

## Original Problem Statement
Build a "Story Universe Engine" — a full-stack AI creator suite with growth engine, monetization, and viral sharing. The core mandate is a production-grade, mobile-first UI with Netflix-level media delivery. All homepage media must be deterministic: pipeline generates, DB stores, API returns, frontend renders. NO runtime derivation.

## Core Architecture
- Frontend: React (CRA + Craco) on port 3000
- Backend: FastAPI on port 8001
- Database: MongoDB
- Storage: Cloudflare R2 (all media via same-origin streaming proxy)
- Payments: Cashfree
- AI: OpenAI GPT-4o-mini, Sora 2, TTS + Gemini 3 via Emergent LLM Key

## Deterministic Media Pipeline (IMPLEMENTED — Mar 30 2026)

### Pipeline Stage (`pipeline.py` -> `_stage_assembly`)
- FFmpeg extracts frame at 00:00:01
- Pillow generates:
  - `thumbnail_small`: 400x530 JPEG, quality=75, ~30KB
  - `poster_large`: 1280x720 JPEG, quality=85, ~100KB
- Uploads to R2 under `media/{job_id}/`
- Stores in DB as nested `media` object

### DB Schema
```json
{
  "media": {
    "thumbnail_small": { "url": "https://...", "type": "image/jpeg" },
    "poster_large": { "url": "https://...", "type": "image/jpeg" }
  }
}
```

## Frontend Component Contract (IMPLEMENTED — Mar 30 2026)

### API Response Shape (engagement.py)
```json
{
  "id": "story_123",
  "title": "...",
  "hook_text": "...",
  "media": {
    "thumb_blur": null,
    "thumbnail_small_url": "/api/media/r2/...",
    "poster_large_url": "/api/media/r2/...",
    "preview_short_url": "/api/media/r2/...",
    "media_version": "v3"
  }
}
```

### Components
- **HeroMedia.jsx** — Renders hero poster (eager, high priority). Blur-up placeholder, optional preview enhancement, designed local fallback.
- **StoryCardMedia.jsx** — Renders card thumbnail (thumbnail_small -> poster_large -> fallback). Optional hover preview. No autoplay by default.
- **MediaPreloader.jsx** — Preloads hero poster + first 4 thumbnails only. Preconnect + dns-prefetch to image origin.

### Dashboard.js Integration
- `resolveMedia()` converts API proxy paths to absolute URLs
- HeroMedia: wrapped in absolute container, Dashboard handles title/hook/CTAs/carousel
- StoryCardMedia: wrapped in card container, Dashboard handles badge/hook/play button
- MediaPreloader: receives resolved absolute URLs for hero + first row

### Eager/Lazy Rules
- Hero: always eager
- First visible row (Trending): first 6 cards eager
- Continue row: first 4 cards eager
- Below-fold rows: lazy

### Forbidden Patterns (NEVER DO)
- No raw scene_images in components
- No static mapping by job_id
- No output_full_url on homepage
- No gradient fallbacks as primary state
- No hidden-until-JS-load behavior for hero
- No autoplay card previews by default

## Key Files
- `/app/backend/services/story_engine/adapters/media_gen.py` — Pillow-based media generation
- `/app/backend/services/story_engine/pipeline.py` — Pipeline assembly with media generation
- `/app/backend/routes/engagement.py` — Feed API with nested media object
- `/app/frontend/src/components/HeroMedia.jsx` — Hero media component (exact contract)
- `/app/frontend/src/components/StoryCardMedia.jsx` — Card media component (exact contract)
- `/app/frontend/src/components/MediaPreloader.jsx` — Preloader component (exact contract)
- `/app/frontend/src/pages/Dashboard.js` — Dashboard using contract components
- `/app/frontend/src/assets/fallbacks/hero-fallback.jpg` — Local hero fallback
- `/app/frontend/src/assets/fallbacks/card-fallback.jpg` — Local card fallback
- `/app/backend/scripts/backfill_media_schema.py` — DB migration script

## Test Credentials
- Test User: test@visionary-suite.com / Test@2026#
- Admin User: admin@creatorstudio.ai / Cr3@t0rStud!o#2026

## Completed
- [x] Deterministic media pipeline (Pillow + FFmpeg) — tested 100%
- [x] Nested media DB schema + backfill (61 jobs migrated)
- [x] Feed API nested media object (media_version: v3) — tested 100%
- [x] HeroMedia component (exact contract skeleton)
- [x] StoryCardMedia component (exact contract skeleton)
- [x] MediaPreloader component (exact contract skeleton)
- [x] Dashboard.js rewrite using contract components
- [x] Local fallback images (hero-fallback.jpg, card-fallback.jpg)
- [x] Verified: Backend 20/20 tests passed, Frontend code review verified

## Upcoming Tasks
- (P1) Blurhash/thumb_blur generation in pipeline for instant perception
- (P1) Preview_short video generation in pipeline for Netflix autoplay
- (P1) CDN-first delivery optimization (Cloudflare edge caching)
- (P2) A/B test hook text variations on public pages
- (P2) "Remix Variants" on share pages
- (P2) Admin dashboard WebSocket upgrade
- (P2) Story Chain leaderboard
