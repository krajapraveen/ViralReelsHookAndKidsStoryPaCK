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

## Gallery Discovery Engine (BUILT Mar 31 2026) — P0+P1 COMPLETE

### P0: Netflix-style discovery
- Featured hero, 9 category rails, explore grid, search/filters/sort, preview modal
- Seeded demo content ("never-empty" guarantee), Remix on every card

### P1: Immersive Viewer & Personalization
- TikTok-style fullscreen vertical viewer with swipe navigation
- Desktop hover-previews on cards
- User-personalized feeds: Continue Watching, Your Creations, For You

## Reel Creation Engine (BUILT Mar 31 2026) — P0+P1 COMPLETE

### P0: Outcome-Driven Engine
- 12 outcome-driven input controls (Platform, Hook Style, Reel Format, CTA, Objective, Output Type + Advanced)
- 7-tab structured output (Script, Hook Variants, Caption, Hashtags, Shot List, Visual Prompts, Voiceover)
- 8 performance variations, AI Recommendations panel, Video generation config modal

### P1: Reference-Based Generation (BUILT Mar 31 2026)
- Two input modes: "Fresh Create" (standard) and "From Reference" (inspired generation)
- Reference inputs: Reel URL (with auto-extraction), Pasted script/caption/transcript, Optional notes
- Backend extracts structural DNA from reference and generates original content
- New "Reference DNA" output tab showing: hook pattern, pacing structure, emotional arc, CTA approach, format choices, what was preserved vs made original
- Graceful fallback: URL extraction fails → falls back to pasted text → falls back to standard generation
- **Files**: `generation.py` (lines 37-167), `schemas.py` (reference fields), `shared.py` (REEL_REFERENCE prompts)

### P1: Quick Presets (BUILT Mar 31 2026)
- 8 one-click preset chips: Viral Hook, Luxury Reel, Product Promo, UGC Ad, Storytelling, Educational, Kids Story, Faceless Biz
- Each preset intelligently prefills: platform, hookStyle, reelFormat, ctaType, goal, outputType, tone, duration, niche, audience
- Presets remain editable after selection; manual changes clear the active preset indicator
- Visually distinct colored chips with active ring states
- **Files**: `ReelGenerator.js` (QUICK_PRESETS constant, handlePresetSelect)

## Premium Login UX (VERIFIED Mar 31 2026)
- Branded overlay masks auth.emergentagent.com transition (150ms)
- AuthCallback branded loading + error states

## Logout (BUILT Mar 31 2026)
- Dashboard user menu + Profile page Sign out button
- Clears all auth tokens, forces full page reload

## Test Credentials
- Test User: test@visionary-suite.com / Test@2026# (free plan)
- Admin User: admin@creatorstudio.ai / Cr3@t0rStud!o#2026 (admin role)

## Key Files
| File | Purpose |
|------|---------|
| `backend/routes/gallery_routes.py` | Gallery APIs + seeding system |
| `frontend/src/pages/Gallery.js` | Netflix-style gallery page + Immersive Viewer |
| `frontend/src/pages/ReelGenerator.js` | Reel Creation Engine + Presets + Reference Mode |
| `backend/routes/generation.py` | Reel generation with reference analysis + URL extraction |
| `backend/models/schemas.py` | GenerateReelRequest with reference fields |
| `backend/shared.py` | Standard + Reference reel prompts |
| `frontend/src/pages/Dashboard.js` | User menu with logout |
| `frontend/src/pages/Profile.js` | Logout button in header |

## Completed (This Session — Mar 31 2026)
- [x] Premium Login UX — 14/14 tests passed
- [x] Logout button — Dashboard + Profile
- [x] Reel Creation Engine P0 — 11/11 backend + all frontend verified
- [x] Gallery Discovery Engine P0 — 18/18 tests passed
- [x] Gallery P1: Immersive Viewer, Hover Previews, User Feeds — tested iteration_399
- [x] Reel P1: Reference-Based Generation — tested iteration_400 (100% pass, 11/11 backend)
- [x] Reel P1: Quick Presets (8 presets) — tested iteration_400 (100% pass)

## Upcoming (P1)
1. Anti-crop watermark improvements + dynamic per-user watermarks
2. Telemetry pipeline (abnormal preview tracking, multi-IP token reuse, scraping detection)
3. Notification Center improvements (history, read/unread states)

## Future/Backlog (P2) — DO NOT START
- Gallery: Leaderboards, Creator profiles, Advanced analytics
- Reel: History + Compare Versions, Brand Kit / Creator Memory, Output Scoring
- Platform: Invisible forensic watermarking, advanced token binding, admin leak dashboard
