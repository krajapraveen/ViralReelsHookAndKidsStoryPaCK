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

## Pipeline Architecture

### Stage Orchestrator
```
INIT → PLANNING → BUILDING_CHARACTER_CONTEXT → PLANNING_SCENE_MOTION 
→ GENERATING_KEYFRAMES → GENERATING_SCENE_CLIPS → GENERATING_AUDIO 
→ ASSEMBLING_VIDEO → VALIDATING → READY / PARTIAL_READY
```

### Multi-Level Fallback
```
Level 0: GPT-4o-mini, full prompt, temp 0.7
Level 1: GPT-4o-mini, reduced prompt, temp 0.4
Level 2: gemini-2.0-flash, reduced prompt, temp 0.3
Level 3: Deterministic text splitter (no LLM)
```

### Recovery Daemon + Assembly Fallback
- Watchdog monitors heartbeats every 2 min
- Assembly stage has auto-recovery with fallback rendering
- Worker class: `critical_story_video` for Story to Video jobs

## Navigation Structure (BUILT Mar 31 2026)

### Routes
```
/app/my-space         — Personal creations hub
/app/my-space/:assetId — Deep link to specific asset
/app/create           — Tool launcher (4 tools)
/app/browse           — Content discovery
/app/characters       — Character studio
/app/dashboard        — User analytics
/app/story-video-studio — Story to Video
/app/comic-storybook  — Photo to Comic
/app/reel-generator   — AI Reels
/app/bedtime-story-builder — Kids Stories
```

### Page Purposes
| Page | Purpose | Distinct Content |
|------|---------|-----------------|
| My Space | See my work | Grid of all creations with filters, search, status |
| Create | Make something new | 4 tool cards → tool-specific pages |
| Browse | Explore ideas/content | Public content grid, trending/new/featured |
| Characters | Manage characters | Character library, create/edit with style/voice |
| Dashboard | See my stats | Total creations, credits, success rate, activity |

## Entitlement-Based Media Access (BUILT Mar 31 2026)

### Business Rules
- **Free users**: Preview only. Cannot download. See "Upgrade to Download" CTA.
- **Active paid subscribers** (starter/pro/premium with active subscription): Full download via short-lived presigned URLs.
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

### Gated Surfaces (ALL download points)
| Surface | Component | Gated |
|---------|-----------|-------|
| Story Video Pipeline | EntitledDownloadButton | Yes |
| My Space cards | EntitledDownloadIcon | Yes |
| Story Preview | EntitledDownloadButton | Yes |
| Browser Video Export | useMediaEntitlement | Yes |
| Video Export Panel | useMediaEntitlement | Yes |
| My Downloads | useMediaEntitlement | Yes |
| Smart Download | useMediaEntitlement | Yes |
| Social Share Download | useMediaEntitlement | Yes |
| Protected Content | useMediaEntitlement | Yes |
| Force Share Gate | No downloadUrl passed | Yes |
| Share Reward Bar | No downloadUrl passed | Yes |

### CTA Copy
- Button: "Upgrade to Download"
- Tooltip: "Downloads are available on paid plans"

## Action Resolver System (BUILT Mar 31 2026)

Backend `_resolve_allowed_actions(job)` provides single source of truth for UI buttons:

| Job State | allowed_actions | resume_supported | recovery_state |
|-----------|----------------|-----------------|----------------|
| READY | watch, download, share, remix, continue | false | NONE |
| PARTIAL_READY | watch, download, retry, start_over | true | WAITING_FOR_USER |
| FAILED (with checkpoints) | retry, start_over | true | WAITING_FOR_USER |
| FAILED (no checkpoints) | start_over | false | WAITING_FOR_USER |
| AUTO_RECOVERING | notify, leave_safely | false | AUTO_RECOVERING |
| Active processing | notify, leave_safely, cancel | false | NONE |

Frontend renders ONLY backend-approved actions. No hardcoded buttons.

## Quality Modes
| Mode | Max Scenes | ETA | Use Sora | Image Quality |
|------|-----------|-----|----------|---------------|
| Fast | 3 | 1-2 min | No | Standard |
| Balanced | 5 | 2-4 min | Yes | Standard |
| High Quality | 7 | 4-8 min | Yes | HD |

## Continue/Remix Optimization
- Dependency-aware checkpoint reuse
- Style remix: 57% stages skipped
- Voice remix: 71% stages skipped
- Pipeline auto-skips stages whose outputs already exist

## Timeout Strategy
- Soft timeout (5 min): "Taking longer than usual" message
- Hard timeout (15 min): Background completion + notify

## Test Credentials
- Test User: test@visionary-suite.com / Test@2026# (free plan)
- Admin User: admin@creatorstudio.ai / Cr3@t0rStud!o#2026 (admin role)

## Key Files
- `/app/frontend/src/contexts/MediaEntitlementContext.js` — Entitlement provider
- `/app/frontend/src/components/EntitledDownloadButton.js` — Download gating
- `/app/frontend/src/pages/MySpacePage.js` — Personal creations hub
- `/app/frontend/src/pages/CreatePage.js` — Tool launcher
- `/app/frontend/src/pages/BrowsePage.js` — Content discovery
- `/app/frontend/src/pages/CharactersPage.js` — Character studio
- `/app/frontend/src/pages/UserDashboardPage.js` — User analytics
- `/app/frontend/src/pages/StoryVideoPipeline.js` — Story to Video flow
- `/app/frontend/src/pages/StoryPreview.js` — Story preview with gated downloads
- `/app/backend/services/entitlement.py` — Entitlement resolver
- `/app/backend/routes/media_routes.py` — Download token & entitlement API
- `/app/backend/routes/story_engine_routes.py` — All story engine endpoints

## Completed (This Session — Mar 31 2026)
- [x] P0 Media Entitlement Gating — Complete implementation across ALL download surfaces (16/16 tests passed)
- [x] Backend: /api/media/entitlement returns correct flags per user plan
- [x] Backend: /api/media/download-token returns 403 for free, presigned URL for paid
- [x] Backend: Status/user-jobs endpoints scrub output_url for free users
- [x] Frontend: MediaEntitlementContext caches entitlement flags
- [x] Frontend: EntitledDownloadButton/Icon used on all 10+ download surfaces
- [x] Frontend: No raw R2 URLs exposed to free users anywhere

## Prior Completed
- [x] P1.1 Continue/Remix Optimization (checkpoint reuse)
- [x] P1.2 Quality Mode Strategy (Fast/Balanced/High Quality)
- [x] P1.3 Analytics & Observability (admin endpoint)
- [x] P0 Fix: Failure UX — allowed_actions, single error panel, no contradictory buttons
- [x] P0 Fix: Navigation — 5 distinct pages (My Space, Create, Browse, Characters, Dashboard)
- [x] P0 Fix: Explore cards now route to correct distinct destinations
- [x] Worker priority: Story to Video = critical_story_video
- [x] Assembly fallback: auto-recovery with simple concat fallback
- [x] Soft timeout: 5min warning → 15min background completion

## Upcoming
- (P1) Anti-crop watermark improvements (dynamic per-user watermarks)
- (P1) Telemetry pipeline for abnormal access patterns
- (P1) Notification Center Improvements — history, read/unread, deep links
- (P1) A/B test hook text on public pages
- (P1) Character-driven auto-share prompts

## Future/Backlog
- (P2) Invisible forensic watermarking and advanced token binding
- (P2) Admin leak dashboard to identify high-risk accounts
- (P2) Remix Variants on share pages
- (P2) Admin dashboard WebSocket upgrade
- (P2) Story Chain leaderboard
- (P2) Separate workers from API server (Celery/Redis)
