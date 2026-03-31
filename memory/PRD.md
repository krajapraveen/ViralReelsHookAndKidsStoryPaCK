# Story Universe Engine — Product Requirements Document

## Original Problem Statement
Build a "Story Universe Engine" — a full-stack AI creator suite with a behavior-driven growth engine, monetization, and viral sharing. Core mandate: Netflix-level media delivery, deterministic personalization, addictive hook system, and a complete dopamine loop.

## Core Architecture
- Frontend: React (CRA + Craco) on port 3000
- Backend: FastAPI on port 8001
- Database: MongoDB (creatorstudio_production)
- Storage: Cloudflare R2
- Payments: Cashfree
- AI: OpenAI GPT-4o-mini, Sora 2, TTS + Gemini 3 via Emergent LLM Key

## Entitlement-Based Media Access (BUILT Mar 31 2026)

### Business Rules
- **Free users**: Preview only. Cannot download. See "Upgrade to Download" CTA.
- **Active paid subscribers**: Full download via short-lived presigned URLs.
- **Top-up credits alone** WITHOUT active subscription: Does NOT unlock download.
- **Admin/Superadmin**: Full access override.

### Architecture
```
Backend (Source of Truth):
  /api/media/entitlement       — Returns can_download, upgrade_required flags
  /api/media/download-token/   — Returns 60-sec presigned URL (paid) or 403 (free)
  /api/story-engine/status/    — Scrubs output_url for free users
  /api/story-engine/user-jobs  — Scrubs output_url for free users

Frontend (Renders from Backend Truth):
  MediaEntitlementContext       — Caches entitlement flags
  EntitledDownloadButton        — Full download button with gating
  EntitledDownloadIcon          — Compact lock/download icon for cards
```

### All Gated Download Surfaces (10+ surfaces)
StoryVideoPipeline, MySpace, StoryPreview, BrowserVideoExport, VideoExportPanel,
MyDownloads, SmartDownloadButton, SocialShareDownload, ProtectedContent,
ForceShareGate, ShareRewardBar — ALL gated.

## Story Series Button Routing (FIXED Mar 31 2026)

### Problem
All 3 buttons on the Series Timeline page called the same handler with no distinction
between resume vs create mode, dumping users into a blank Story-to-Video page.

### Solution — Distinct Handlers with Explicit Intent

| Button | Handler | Behavior |
|--------|---------|----------|
| Header "Continue Episode N" | `handleSmartContinue()` | If current episode has job_id → resume. Else → create new. |
| Big CTA "Continue Episode N" | `handleSmartContinue()` | Same as above. |
| Episode card "Continue →" | `handleResumeEpisode(ep)` | If ep has job_id → `/app/story-video-studio?job={job_id}`. If ep has slug → `/v/{slug}`. Else → create new. |
| "Create Episode N" | `handleCreateNewEpisode()` | Always calls backend continue endpoint. Stores full series context in remix_data. |

### Series Context Flow
```
SeriesTimeline → handleCreateNewEpisode() → remix_data = {
  prompt, series_id, series_title, episode_number, mode: 'create',
  character_ids, source_tool: 'series-continue'
} → /app/story-video-studio

StoryVideoPipeline reads remix_data → sets seriesContext state → renders:
  - Series banner: "{series_title} — Creating Episode N"
  - Heading: "Episode N" instead of "Create a Story Video"
  - Passes series_id + episode_number to backend create payload
```

### Backend Support
- `CreateEngineRequest` model accepts optional `series_id` and `episode_number`
- `/api/story-engine/create` stores these on the job document for series linkage

## Branding Cleanup (DONE Mar 31 2026)
- All visible "Emergent" / "Powered by Emergent" branding removed
- CSS + MutationObserver suppress platform-injected badges
- PrivacyPolicy.js: "Emergent Auth" → "OAuth 2.0"

## Navigation Structure
```
/app/my-space, /app/create, /app/browse, /app/characters, /app/dashboard
/app/story-video-studio — Unified story video pipeline
```

## Quality Modes
| Mode | Max Scenes | ETA | Use Sora |
|------|-----------|-----|----------|
| Fast | 3 | 1-2 min | No |
| Balanced | 5 | 2-4 min | Yes |
| High Quality | 7 | 4-8 min | Yes |

## Test Credentials
- Test User: test@visionary-suite.com / Test@2026# (free plan)
- Admin User: admin@creatorstudio.ai / Cr3@t0rStud!o#2026 (admin role)

## Key Files
- `/app/frontend/src/pages/SeriesTimeline.js` — Series timeline with 3 distinct handlers
- `/app/frontend/src/pages/StoryVideoPipeline.js` — Unified pipeline with series context support
- `/app/frontend/src/contexts/MediaEntitlementContext.js` — Entitlement provider
- `/app/frontend/src/components/EntitledDownloadButton.js` — Download gating
- `/app/backend/services/entitlement.py` — Entitlement resolver
- `/app/backend/routes/media_routes.py` — Download token & entitlement API
- `/app/backend/routes/story_engine_routes.py` — Story engine with series_id support
- `/app/backend/routes/universe_routes.py` — Series continue endpoint

## Completed (This Session — Mar 31 2026)
- [x] P0 Media Entitlement Gating — 16/16 tests, all download surfaces gated
- [x] Branding removal — 0 Emergent/Powered by visible
- [x] Story Series routing fix — 3 distinct handlers, series context banner, backend series linkage

## Upcoming
- (P1) Anti-crop watermark improvements (dynamic per-user watermarks)
- (P1) Telemetry pipeline for abnormal access patterns
- (P1) Notification Center Improvements
- (P1) Episode auto-registration when generation completes (series_id → story_episodes)

## Future/Backlog
- (P2) Invisible forensic watermarking
- (P2) Admin leak dashboard
- (P2) Remix Variants, Story Chain leaderboard
- (P2) Admin dashboard WebSocket upgrade
