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
### Write Point
`pipeline.py → _stage_validation()` — when job completes in SUCCESS_STATES AND `job.series_id` exists:
- Calls `_register_series_episode(job)`, upserts on `(series_id, episode_number)`
- Updates `story_series.episode_count`

### Read Point
`universe_routes.py → get_series_episodes()` — reads from `story_episodes` with orphan job fallback

## Branding Cleanup (DONE Mar 31 2026)
- All visible "Emergent" branding removed from UI
- CSS + MutationObserver suppress platform-injected badges

## Premium Login UX (VERIFIED Mar 31 2026)
### What We Control
- Full-screen branded overlay (AuthLaunchOverlay) renders IMMEDIATELY on Google sign-in click
- Overlay masks the transition before the browser navigates to auth.emergentagent.com
- 150ms delay ensures overlay paints before redirect fires
- Button enters disabled state, preventing double-click
- Overlay shows rotating messages: "Signing you in…", "Preparing your creative workspace…", etc.
- AuthCallback shows branded loading screen ("Syncing your studio…") while processing auth
- AuthCallback error state is branded with "Try Again" and "Back to Login" CTAs
- Return-path preserved via `localStorage.auth_return_path`
- No blank white intermediate screen from our app side
- No "Emergent" text on any app-controlled screen

### What Remains (Outside Our Control)
- `auth.emergentagent.com` URL visible in browser address bar during Google OAuth
- The hosted auth page's own branding (Google + Emergent logo) is displayed while user is on that page
- Exact exposure duration depends on network speed and Google/Emergent provider latency
- We minimize exposure but cannot guarantee exact timing

## Logout (BUILT Mar 31 2026)
### Locations
- **Dashboard**: User menu toggle (top-right) → dropdown with Profile, Billing, Sign out
- **Profile page**: Sign out button in header next to credits display
- **Mobile**: Same user menu accessible on mobile viewport + Profile via bottom nav

### Behavior
1. Clears `token`, `user`, `user_id`, `auth_return_path`, `remix_return_url` from localStorage
2. Forces full page reload to `/login` via `window.location.href` (resets React auth state)
3. Protected routes enforce login requirement — navigating to `/app` after logout redirects to `/login`
4. No stale authenticated UI remains

### Note on Provider Session
JWT-based auth — no backend logout endpoint. Token is client-side only. The Emergent-managed Google Auth session may persist on `auth.emergentagent.com`; this is by design for the hosted auth provider.

## Test Credentials
- Test User: test@visionary-suite.com / Test@2026# (free plan)
- Admin User: admin@creatorstudio.ai / Cr3@t0rStud!o#2026 (admin role)

## Key Files
- `/app/frontend/src/components/AuthLaunchOverlay.js` — Premium login overlay
- `/app/frontend/src/pages/AuthCallback.js` — Branded bootstrap + error states
- `/app/frontend/src/pages/Login.js` — Google sign-in with overlay + return-path
- `/app/frontend/src/pages/Signup.js` — Google sign-up with overlay + return-path
- `/app/frontend/src/pages/Dashboard.js` — User menu with logout dropdown
- `/app/frontend/src/pages/Profile.js` — Logout button in header
- `/app/backend/services/story_engine/pipeline.py` — Episode auto-registration
- `/app/backend/routes/universe_routes.py` — Episode queries with fallback
- `/app/frontend/src/contexts/MediaEntitlementContext.js` — Entitlement provider
- `/app/frontend/src/components/EntitledDownloadButton.js` — Download gating
- `/app/frontend/public/index.html` — MutationObserver for Emergent badge suppression

## Completed (This Session — Mar 31 2026)
- [x] P0 Media Entitlement Gating — 16/16 tests passed
- [x] Branding removal — 0 Emergent/Powered by visible
- [x] Story Series routing fix — 3 distinct handlers, series context banner
- [x] Series Episode Auto-Registration — 17/17 tests passed
- [x] Premium Login UX — 14/14 tests passed, overlay + callback branded, no Emergent text
- [x] Logout button — Dashboard + Profile, desktop + mobile, protected routes enforced

## Upcoming (P1)
1. Anti-crop watermark improvements (dynamic per-user watermarks)
2. Telemetry pipeline for abnormal access patterns
3. Notification Center improvements (history, read/unread)

## Future/Backlog (P2)
- Invisible forensic watermarking
- Admin leak dashboard
- Remix Variants, Story Chain leaderboard
- Admin dashboard WebSocket upgrade
