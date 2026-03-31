# Story Universe Engine — Product Requirements Document

## Original Problem Statement
Build a "Story Universe Engine" — a full-stack AI creator suite with a behavior-driven growth engine, monetization, and viral sharing.

## Core Architecture
- Frontend: React (CRA + Craco) on port 3000
- Backend: FastAPI on port 8001
- Database: MongoDB (creatorstudio_production)
- Storage: Cloudflare R2
- Payments: Cashfree
- AI: OpenAI GPT-4o-mini, Sora 2, TTS + Gemini 3 via Emergent LLM Key

## Entitlement-Based Media Access (BUILT Mar 31 2026)
- Free users: Preview only, "Upgrade to Download" CTA
- Paid subscribers: Short-lived presigned URLs via `/api/media/download-token/`
- Backend scrubs output_url for free users in all API responses
- 10+ download surfaces gated via MediaEntitlementContext + EntitledDownloadButton

## Story Series Button Routing (FIXED Mar 31 2026)
| Button | Handler | Behavior |
|--------|---------|----------|
| Header "Continue Episode N" | `handleSmartContinue()` | Resume by job_id if exists, else create |
| Big CTA "Continue Episode N" | `handleSmartContinue()` | Same |
| Episode card "Continue →" | `handleResumeEpisode(ep)` | Resume specific episode's job |
| "Create Episode N" | `handleCreateNewEpisode()` | Create new with full series context |

## Series Episode Auto-Registration (BUILT Mar 31 2026)

### Schema: story_episodes
```
{
  episode_id: string (uuid),
  series_id: string,
  episode_number: int,
  title: string,
  job_id: string,
  status: "ready" | "in_progress" | "failed",
  output_asset_url: string,
  thumbnail_url: string,
  output_type: "video",
  tool_used: "story_video",
  scene_count: int,
  user_id: string,
  character_ids: string[],
  cliffhanger: string,
  summary: string,
  story_prompt: string,
  created_at: ISO string,
  updated_at: ISO string
}
```

### Write Point
`pipeline.py → _stage_validation()` — when job completes in SUCCESS_STATES (READY/PARTIAL_READY) AND `job.series_id` exists:
- Calls `_register_series_episode(job)`
- Upserts on `(series_id, episode_number)` to prevent duplicates
- Updates `story_series.episode_count`

### Read Point
`universe_routes.py → get_series_episodes()`:
- Primary: reads from `story_episodes` collection
- Fallback: finds orphan `story_engine_jobs` with matching `series_id` not yet in `story_episodes`
- Merges and sorts by episode_number
- Computes `is_current`, `is_completed`, `locked` status

### Backend Model
`CreateEngineRequest` accepts optional `series_id` and `episode_number`. The create endpoint stores them on the job document.

## Branding Cleanup (DONE Mar 31 2026)
- All visible "Emergent" branding removed from UI
- CSS + MutationObserver suppress platform-injected badges

## Premium Login UX (VERIFIED Mar 31 2026)
- Full-screen branded overlay (AuthLaunchOverlay) masks external auth redirect
- Renders on both Login and Signup pages when Google sign-in is clicked
- Button enters disabled state immediately, preventing double-click
- Overlay shows rotating messages: "Signing you in…", "Preparing your creative workspace…", etc.
- AuthCallback shows branded loading screen ("Syncing your studio…") while processing
- AuthCallback error state is branded with "Try Again" and "Back to Login" CTAs
- Return-path behavior preserved via `localStorage.auth_return_path`
- No blank white intermediate screen — dark gradient background throughout
- No "Emergent" text in any app-controlled screens
- Remaining: `auth.emergentagent.com` URL visible in browser address bar (hosted externally, outside our control)

## Test Credentials
- Test User: test@visionary-suite.com / Test@2026# (free plan)
- Admin User: admin@creatorstudio.ai / Cr3@t0rStud!o#2026 (admin role)

## Key Files
- `/app/frontend/src/components/AuthLaunchOverlay.js` — Premium login overlay
- `/app/frontend/src/pages/AuthCallback.js` — Branded bootstrap + error states
- `/app/frontend/src/pages/Login.js` — Google sign-in with overlay + return-path
- `/app/frontend/src/pages/Signup.js` — Google sign-up with overlay + return-path
- `/app/backend/services/story_engine/pipeline.py` — _register_series_episode()
- `/app/backend/routes/universe_routes.py` — get_series_episodes with fallback
- `/app/backend/routes/story_engine_routes.py` — CreateEngineRequest with series fields
- `/app/frontend/src/pages/SeriesTimeline.js` — 3 distinct action handlers
- `/app/frontend/src/pages/StoryVideoPipeline.js` — Series context display + payload
- `/app/frontend/src/contexts/MediaEntitlementContext.js` — Entitlement provider
- `/app/frontend/src/components/EntitledDownloadButton.js` — Download gating
- `/app/frontend/public/index.html` — MutationObserver to hide injected Emergent badges

## Completed (This Session — Mar 31 2026)
- [x] P0 Media Entitlement Gating — 16/16 tests passed
- [x] Branding removal — 0 Emergent/Powered by visible
- [x] Story Series routing fix — 3 distinct handlers, series context banner
- [x] Series Episode Auto-Registration — 17/17 tests passed, upsert logic, fallback read
- [x] Premium Login UX — Runtime verified (overlay renders, callback branded, return-path works)

## Upcoming (P1)
- Anti-crop watermark improvements (dynamic per-user watermarks)
- Telemetry pipeline for abnormal access patterns
- Notification Center improvements (history, read/unread)

## Future/Backlog (P2)
- Invisible forensic watermarking
- Admin leak dashboard
- Remix Variants, Story Chain leaderboard
- Admin dashboard WebSocket upgrade
