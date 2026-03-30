# Story Universe Engine — Product Requirements Document

## Original Problem Statement
Build a "Story Universe Engine" — a full-stack AI creator suite with growth engine, monetization, and viral sharing. The core mandate is a production-grade, mobile-first UI with Netflix-level media delivery.

## Core Architecture
- Frontend: React (CRA + Craco) on port 3000
- Backend: FastAPI on port 8001
- Database: MongoDB
- Storage: Cloudflare R2 (all media via same-origin streaming proxy)
- Payments: Cashfree
- AI: OpenAI GPT-4o-mini, Sora 2, TTS + Gemini 3 via Emergent LLM Key

## Deterministic Media Pipeline (IMPLEMENTED — Mar 30 2026)

### Architecture (Netflix-Level)
Pipeline generates → DB stores → API returns → Frontend renders. **NO runtime derivation. EVER.**

### Pipeline Stage (`pipeline.py` → `_stage_assembly`)
- After video assembly, calls `generate_media_assets()` from `media_gen.py`
- **FFmpeg** extracts a stable frame at 00:00:01
- **Pillow** generates:
  - `thumbnail_small`: 400x530 JPEG, quality=75, ~30KB (center-crop + LANCZOS)
  - `poster_large`: 1280x720 JPEG, quality=85, ~100KB (center-crop + LANCZOS)
- Uploads both to R2 under `media/{job_id}/`

### DB Schema (Nested `media` object)
```json
{
  "media": {
    "thumbnail_small": { "url": "https://...", "type": "image/jpeg" },
    "poster_large": { "url": "https://...", "type": "image/jpeg" }
  }
}
```

### Feed API (`engagement.py` → `_shape_item`)
- Reads from `media.*` first, legacy flat fields as fallback
- Converts all URLs to same-origin proxy: `/api/media/r2/{key}`
- Returns ONLY `thumbnail_small_url` and `poster_url` — no old fields

### Frontend (`Dashboard.js`)
- Hero uses `poster_url` from API
- Story cards use `thumbnail_small_url` from API
- No gradient fallback chains, no scene_images derivation

### Backfill Script
- `scripts/backfill_media_schema.py` — migrated 61 existing jobs to new schema

## Media Delivery (Production-Grade)
- ALL media via same-origin proxy `/api/media/r2/{key}` — Safari-safe
- Content-Type from R2 metadata (authoritative). nosniff safe. ETag.
- Videos streamed 64KB chunks. Range <2MB buffered.
- Hero poster: eager + fetchPriority="high". First 6 cards: loading="eager"

### Platform Constraints (K8s Ingress)
- Strips Content-Length from GET (HEAD preserves it)
- Overrides Cache-Control to no-store (Surrogate-Control survives)

## Key Files
- `/app/backend/services/story_engine/adapters/media_gen.py` — Pillow-based media generation
- `/app/backend/services/story_engine/pipeline.py` — Pipeline assembly with media generation
- `/app/backend/routes/engagement.py` — Feed API with strict media schema
- `/app/frontend/src/pages/Dashboard.js` — Frontend consuming only API-provided media
- `/app/backend/scripts/backfill_media_schema.py` — DB migration script

## Test Credentials
- Test User: test@visionary-suite.com / Test@2026#
- Admin User: admin@creatorstudio.ai / Cr3@t0rStud!o#2026

## Completed (P0)
- [x] Deterministic media pipeline (Pillow + FFmpeg)
- [x] Nested media DB schema
- [x] Feed API strict media resolution
- [x] Frontend simplified rendering
- [x] DB backfill for existing jobs (61 migrated)
- [x] Verified: 100% test pass rate (23/23 tests)

## Upcoming Tasks
- (P1) A/B test hook text variations on public pages
- (P1) Character-driven auto-share prompts
- (P1) CDN-first delivery (post-proxy optimization)
- (P2) Remix Variants on share pages
- (P2) Admin dashboard WebSocket upgrade
- (P2) Story Chain leaderboard
- (P2) Blurhash placeholders for instant perception
- (P2) Preview_short Netflix autoplay
