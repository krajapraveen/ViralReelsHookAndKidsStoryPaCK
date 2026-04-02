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

## Gallery Discovery Engine (COMPLETE)

### P0: Netflix-style discovery
- Featured hero, 9 category rails, explore grid, search/filters/sort, preview modal
- Seeded demo content ("never-empty" guarantee), Remix on every card

### P1: Immersive Viewer & Personalization
- TikTok-style fullscreen vertical viewer with swipe navigation
- Desktop hover-previews on cards
- User-personalized feeds: Continue Watching, Your Creations, For You

### P0-A: Story Preview Fallback (BUILT Mar 31 2026)
- Items WITHOUT video show rich preview modal: thumbnail, title, description, stats, story excerpt
- "Video preview not available" badge with amber styling
- Dual CTA: "Remix This" + "Create Similar" — never a dead-end
- Items WITH video still play normally with all controls
- Mute/Volume button only shown for video items
- **Root cause**: ImmersiveViewer previously showed only a static SafeImage for non-video items with no actionable UI
- **Files**: `Gallery.js` lines 365-440

## Reel Creation Engine (COMPLETE)

### P0: Outcome-Driven Engine
- 12 outcome-driven input controls + 7-tab structured output
- 8 performance variations, AI Recommendations, Video generation config

### P1: Reference-Based Generation (BUILT Mar 31 2026)
- Two modes: "Fresh Create" / "From Reference"
- Reference inputs: Reel URL (auto-extraction), pasted text, optional notes
- "Reference DNA" output tab with structural analysis
- **Files**: `generation.py`, `schemas.py`, `shared.py`

### P1: Quick Presets (BUILT Mar 31 2026)
- 8 reel presets: Viral Hook, Luxury Reel, Product Promo, UGC Ad, Storytelling, Educational, Kids Story, Faceless Biz
- **Files**: `ReelGenerator.js`

## Comic Story Builder (UPGRADED Mar 31 2026)

### P0-B: Full Builder Upgrade
1. **Step 5 Improvements** (DONE)
   - Deliverables summary: Comic PDF, Cover Image, Page Images ZIP
   - Dynamic add-on items: Print-Ready PDF, Activity Pages, Dedication Page, Commercial License
   - Book summary with language, audience, age group display
   - Estimated generation time based on page count
   - Generation stage indicators: Planning → Cover → Pages → Layout → Packaging → Ready

2. **Auto-save / Restore Progress** (DONE)
   - Persists to localStorage: genre, story, title, author, pages, add-ons, language, age group, reading level, bilingual
   - Restores on page load (within 24 hours) with toast notification
   - Clears on successful generation or wizard reset

3. **Step 2 Improvements** (DONE)
   - Story Builder Assist: 5 chip categories (Hero, Setting, Conflict, Style, Moral) × 5 options each
   - "Improve My Idea" button → calls `/api/comic-storybook-v2/improve-idea` → AI expands weak prompts
   - Also returns suggested title if none set

4. **Generation Stages** (DONE)
   - 6 visual stage indicators during generation with active/complete/pending states
   - Replaces generic spinner with meaningful progress

5. **Quick Presets** (DONE)
   - 10 presets: Kids Adventure, Bedtime Story, Superhero Origin, Fantasy Quest, School Story, Animal Friendship, Mystery Puzzle, Funny Comic, Educational Comic, Bilingual Kids Book
   - Each sets genre + language + age group + reading level

6. **Language / Localization Controls** (DONE)
   - Language selector: English, Hindi, Telugu, Spanish, French, Arabic, German, Portuguese, Japanese, Korean, Chinese, Italian
   - Age Group: 3-6, 4-7, 6-10, 8-12, 12+
   - Reading Level: Beginner, Intermediate, Advanced
   - Bilingual toggle with secondary language selector
   - All fields passed to backend pipeline and used in story outline generation

7. **Story Quality Score** (BUILT Mar 31 2026)
   - AI-powered analysis of story ideas across 8 dimensions: clarity, protagonist, setting, conflict, emotional appeal, age appropriateness, visual richness, lesson potential
   - Overall score 0-100 with 4 scoring bands (Strong 85+ / Good 70-84 / Usable 50-69 / Too vague <50)
   - Strengths section with prompt-specific feedback
   - Opportunities section with actionable suggestions
   - One-Click Improvement chips that apply fixes via the Improve My Idea API
   - Score auto-clears when user edits story (stale prevention)
   - Re-analyze and Dismiss buttons
   - Non-blocking, encouraging tone
   - **Backend**: `/api/comic-storybook-v2/analyze-story` endpoint using Gemini
   - **Files**: `comic_storybook_v2.py` (analyze-story endpoint), `ComicStorybookBuilder.js` (StoryQualityScore UI)

**Files changed**: `ComicStorybookBuilder.js`, `comic_storybook_v2.py`

## Premium Login UX (VERIFIED)
- Branded overlay masks auth.emergentagent.com transition (150ms)

## Logout (BUILT)
- Dashboard user menu + Profile page Sign out button

## Test Credentials
- Test User: test@visionary-suite.com / Test@2026# (free plan)
- Admin User: admin@creatorstudio.ai / Cr3@t0rStud!o#2026 (admin role)

## Completed (This Session — Mar 31 2026)
- [x] Reel P1: Reference-Based Generation — iteration_400 (100%)
- [x] Reel P1: Quick Presets (8 presets) — iteration_400 (100%)
- [x] P0-A: Gallery Story Preview Fallback — iteration_401 (100%)
- [x] P0-B: Comic Builder Step 5 Deliverables Summary — iteration_401 (100%)
- [x] P0-B: Auto-save / Restore Progress — iteration_401 (100%)
- [x] P0-B: Step 2 AI Helper Chips + Improve My Idea — iteration_401 (100%)
- [x] P0-B: Generation Stages Pipeline — iteration_401 (100%)
- [x] P0-B: Quick Presets (10 presets) — iteration_401 (100%)
- [x] P0-B: Language / Localization Controls — iteration_401 (100%)
- [x] P1: Story Quality Score (8-dimension AI analysis + one-click fixes) — iteration_402 (100%, 8/8 backend)

## Bedtime Experience Engine (BUILT Apr 2 2026)

### P0: Complete Rewrite — Bedtime Story Builder → Experience Engine
1. **Backend AI Generation** (DONE)
   - Replaced template-only logic with AI structured JSON scenes via Gemini LLM
   - Template fallback with `fill_placeholders` for reliability
   - `normalize_story` guarantees every response has structured `scenes` array
   - **Endpoints**: `GET /api/bedtime-story-builder/config`, `POST /api/bedtime-story-builder/generate`
   - **Files**: `bedtime_story_builder.py`

2. **1-Screen Smart Input** (DONE)
   - Child name (optional), age group, mood, voice style, duration, theme, moral
   - Single "Create Magic Story" CTA — no wizard, no multi-step
   - Dark immersive background

3. **Web Speech API Playback** (DONE — MOCKED audio via browser SpeechSynthesis)
   - Play/Pause/Resume/Stop controls
   - Auto-scroll to current scene during playback
   - `voiceschanged` event handling for reliable voice loading
   - Marker stripping ([PAUSE], [SLOW], [WHISPER], [SFX]) before speech

4. **Bedtime Mode** (DONE)
   - Toggleable dark immersive mode (#060A14 background)
   - Body class `bedtime-mode` hides navbar/sidebar
   - Larger scene text (text-lg/xl), hidden SFX/voice notes
   - Active scene border highlight during playback

5. **Local Streak System** (DONE)
   - localStorage-driven daily streak counter
   - Auto-increment on story creation (once per day)
   - Yesterday check for streak continuation, reset on gap
   - Badge in hero section and story result

6. **Remix Variants** (DONE)
   - Animal, Space, Funny, Extra Sleepy — instant remix without page reload
   - Sends `remix_type` to backend, re-generates with variant instruction

7. **Download/Copy** (DONE)
   - .txt download with story + voice notes + SFX
   - Copy to clipboard with confirmation

**Testing**: iteration_403 — 100% backend (17/17), 100% frontend (12/12)
**Files**: `BedtimeStoryBuilder.js`, `bedtime_story_builder.py`

## Completed (This Session — Apr 2 2026)
- [x] Bedtime Experience Engine P0 — iteration_403 (100%, 29/29 tests)

## Photo to Comic P0 Upgrades (BUILT Apr 2 2026)

### 5 Production Improvements:
1. **Parallel Panel Generation** (DONE) — `asyncio.gather` for all panels simultaneously, 3-5x speed boost, per-panel retry (2 attempts, 120s timeout)
2. **Real Backend-Driven Progress Stages** (DONE) — `stages` array in job document, tracked per-stage (face_analysis → story_generation → panel_generation → composition)
3. **Smart Story Presets** (DONE) — 8 presets: Hero Journey, Comedy Gold, Love Story, Mystery Case, Rise Up, Epic Adventure, Spooky Tale, Future World
4. **Output Bundle** (DONE) — PNG download + Story Script (TXT) via `/api/photo-to-comic/script/{job_id}`
5. **Dynamic Time Estimation** (DONE) — Queue-aware estimate via `/api/photo-to-comic/estimate` + "Guaranteed output or credits refunded" badge

**New Endpoints**: `GET /presets`, `GET /estimate`, `GET /script/{job_id}`
**Testing**: iteration_405 — 100% (20/20 backend, 12/12 frontend)
**Files**: `photo_to_comic.py`, `PhotoToComic.js`

## Bug Fix: False "Generation Failed" Toast (FIXED Apr 2 2026)

### Root Causes Found & Fixed:
1. `setCredits` was destructured from `useCredits()` but CreditContext only exports `refreshCredits` — calling it crashed
2. `credits` starts as `null`, and `(null ?? 0) < 10 = true` silently blocked generation 
3. `try/catch` was too broad — tracking/streak failures inside same block as generation poisoned the success path

### Fixes Applied:
- Replaced `setCredits` with `refreshCredits`
- Fixed credit null check: only blocks when `creditsLoaded === true && credits !== null && credits < 10`
- Split try/catch: main generation has isolated catch ("Generation failed"), post-success side effects (streak, tracking, credit refresh) each have their own isolated error handling
- **Testing**: iteration_404 — 100% (30/30 backend, 16/16 frontend)

## Bedtime Metrics Instrumentation (BUILT Apr 2 2026)

### Validation Tracking Layer (NOT a feature)
- 6 events tracked: `story_generated`, `play_clicked`, `bedtime_mode_enabled`, `remix_clicked`, `session_started`, `session_returned`
- MongoDB collection: `bedtime_events`
- `POST /api/bedtime-story-builder/track` — fire-and-forget from frontend
- `GET /api/bedtime-story-builder/admin/metrics` — admin-only aggregated metrics
- Returns: total unique users, event counts, next-day retention %
- **No UI, no dashboard** — CLI/curl only
- **Files**: `bedtime_story_builder.py` (track + metrics endpoints), `BedtimeStoryBuilder.js` (5 track() calls)

## Upcoming (P1) — Not Started
1. Anti-crop watermark improvements + dynamic per-user watermarks
2. Telemetry pipeline (abnormal preview tracking, multi-IP token reuse, scraping detection)
3. Notification Center improvements (history, read/unread states)

## Future/Backlog (P2) — DO NOT START
- Bedtime: Real TTS, Image gen, Video pipeline (replacing Web Speech API mock)
- Gallery: Leaderboards, Creator profiles, Advanced analytics
- Reel: History + Compare Versions, Brand Kit, Output Scoring
- Comic: Comic-to-video teaser, narrator voice, character consistency, KDP-ready pack
- Platform: Invisible forensic watermarking, token binding, admin leak dashboard
- Refactor: App.js route protection abstraction
