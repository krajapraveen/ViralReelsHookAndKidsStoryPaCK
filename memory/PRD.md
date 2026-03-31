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

## Upcoming (P1) — Not Started
1. Anti-crop watermark improvements + dynamic per-user watermarks
2. Telemetry pipeline (abnormal preview tracking, multi-IP token reuse, scraping detection)
3. Notification Center improvements (history, read/unread states)

## Future/Backlog (P2) — DO NOT START
- Gallery: Leaderboards, Creator profiles, Advanced analytics
- Reel: History + Compare Versions, Brand Kit, Output Scoring
- Comic: Comic-to-video teaser, narrator voice, character consistency, KDP-ready pack
- Platform: Invisible forensic watermarking, token binding, admin leak dashboard
- Refactor: App.js route protection abstraction
