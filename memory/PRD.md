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
- Test User: test@visionary-suite.com / Test@2026#
- Admin User: admin@creatorstudio.ai / Cr3@t0rStud!o#2026

## Key Files
- `/app/frontend/src/pages/MySpacePage.js` — Personal creations hub
- `/app/frontend/src/pages/CreatePage.js` — Tool launcher
- `/app/frontend/src/pages/BrowsePage.js` — Content discovery
- `/app/frontend/src/pages/CharactersPage.js` — Character studio
- `/app/frontend/src/pages/UserDashboardPage.js` — User analytics
- `/app/frontend/src/components/ProgressiveGeneration.js` — Generation status
- `/app/frontend/src/pages/StoryVideoPipeline.js` — Story to Video flow
- `/app/backend/routes/story_engine_routes.py` — All story engine endpoints
- `/app/backend/services/story_engine/pipeline.py` — Stage orchestrator

## Completed (This Session — Mar 31 2026)
- [x] P1.1 Continue/Remix Optimization (checkpoint reuse, 16/16 tests)
- [x] P1.2 Quality Mode Strategy (Fast/Balanced/High Quality, 21/21 tests)
- [x] P1.3 Analytics & Observability (admin endpoint)
- [x] P0 Fix: Failure UX — allowed_actions, single error panel, no contradictory buttons (20/20 tests)
- [x] P0 Fix: Navigation — 5 distinct pages (My Space, Create, Browse, Characters, Dashboard)
- [x] P0 Fix: Explore cards now route to correct distinct destinations
- [x] Worker priority: Story to Video = critical_story_video
- [x] Assembly fallback: auto-recovery with simple concat fallback
- [x] Soft timeout: 5min warning → 15min background completion

## Upcoming
- (P1) Notification Center Improvements — history, read/unread, deep links
- (P1) A/B test hook text on public pages
- (P1) Character-driven auto-share prompts

## Future/Backlog
- (P2) Wait-page mini-games (deferred)
- (P2) Remix Variants on share pages
- (P2) Admin dashboard WebSocket upgrade
- (P2) Story Chain leaderboard
- (P2) Separate workers from API server (Celery/Redis)
