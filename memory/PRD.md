# Story Universe Engine — Product Requirements Document

## Original Problem Statement
Build a "Story Universe Engine" — a full-stack AI creator suite with growth engine, monetization, and viral sharing. The core mandate is a production-grade, mobile-first UI with Netflix-level media delivery and a locked-down visual contract.

## Core Architecture
- Frontend: React (CRA + Craco) on port 3000
- Backend: FastAPI on port 8001
- Database: MongoDB
- Storage: Cloudflare R2 (all media via same-origin streaming proxy)
- Payments: Cashfree
- AI: OpenAI GPT-4o-mini, Sora 2, TTS + Gemini 3 via Emergent LLM Key

## Deterministic Media Pipeline (IMPLEMENTED — Mar 30 2026)
- FFmpeg extracts frame, Pillow generates thumbnail_small (400x530) + poster_large (1280x720)
- Stored in nested `media` object in DB
- Feed API returns `media.thumbnail_small_url`, `media.poster_large_url`, `media.preview_short_url`, `media.media_version: "v3"`

## Frontend Component Contract (IMPLEMENTED — Mar 30 2026)
- **HeroMedia.jsx** — Hero poster (eager, high priority, blur-up, fallback)
- **StoryCardMedia.jsx** — Card thumbnail (thumbnail_small -> poster_large -> fallback)
- **MediaPreloader.jsx** — Preloads hero poster + first 4 thumbnails only
- **Dashboard.js** — Uses components via `resolveMedia()` helper

## Visual Contract (IMPLEMENTED — Mar 30 2026)

### Design Tokens
- Page background: `#0B0B0F`
- Card background: `#121218`
- Accent gradient: `#6C5CE7` -> `#00C2FF`
- Fallback gradients: `#2A1E5C`, `#0F5C7A`, `#1D7A45`

### Hero
- Container: `h-[58vh] sm:h-[64vh] lg:h-[72vh] bg-[#0B0B0F]`
- Blur: `blur-2xl opacity-70 scale-105`
- Overlay: `from-black/55 via-black/20 to-transparent` (lighter, not crushing)
- Bottom fade: `h-40 from-black/70 to-transparent`
- Badge: `bg-white/15 backdrop-blur-md border border-white/20`
- Title: `font-extrabold tracking-tight drop-shadow-[0_2px_12px_rgba(0,0,0,0.45)]`
- CTAs: Primary gradient with `shadow-[0_0_24px_rgba(0,194,255,0.28)]`, secondary glass

### Story Cards
- Sizes: `w-[160px] h-[220px] sm:w-[200px] sm:h-[280px] lg:w-[220px] lg:h-[300px]`
- Style: `rounded-2xl border border-white/[0.08] shadow-[0_10px_32px_rgba(0,0,0,0.18)]`
- Hover: `hover:scale-[1.02] hover:shadow-[0_16px_40px_rgba(0,0,0,0.28)]`
- Badge: `bg-black/35 backdrop-blur-md border border-white/15`
- Overlay: `from-black/80 via-black/15 to-transparent`

### Metrics Strip
- Card: `rounded-2xl bg-[#121218] border border-white/[0.08] shadow-[0_8px_30px_rgba(0,0,0,0.18)]`
- Label: `text-[11px] uppercase tracking-[0.14em] text-white/50 font-semibold`

### Features Grid
- Layout: `grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4`
- Card: `rounded-2xl border border-white/[0.08] bg-[#121218] p-5`
- Icon: `rounded-2xl bg-gradient-to-br from-[#6C5CE7]/25 to-[#00C2FF]/25 border border-white/10`

### Utilities
- Shimmer: `@keyframes shimmer { 100% { transform: translateX(200%) } }`
- No-scrollbar: `.no-scrollbar { -ms-overflow-style: none; scrollbar-width: none; }`
- Bottom nav: `bg-[#0B0B0F]/95 backdrop-blur-lg`

## Key Files
- `/app/frontend/src/components/HeroMedia.jsx`
- `/app/frontend/src/components/StoryCardMedia.jsx`
- `/app/frontend/src/components/MediaPreloader.jsx`
- `/app/frontend/src/pages/Dashboard.js`
- `/app/frontend/src/assets/fallbacks/hero-fallback.jpg`
- `/app/frontend/src/assets/fallbacks/card-fallback.jpg`
- `/app/backend/routes/engagement.py`
- `/app/backend/services/story_engine/adapters/media_gen.py`
- `/app/backend/services/story_engine/pipeline.py`
- `/app/backend/scripts/backfill_media_schema.py`

## Test Credentials
- Test User: test@visionary-suite.com / Test@2026#
- Admin User: admin@creatorstudio.ai / Cr3@t0rStud!o#2026

## Completed
- [x] Deterministic media pipeline (Pillow + FFmpeg)
- [x] Nested media DB schema + backfill (61 jobs)
- [x] Feed API nested media object (media_version: v3)
- [x] HeroMedia, StoryCardMedia, MediaPreloader components
- [x] Dashboard rewrite with contract components
- [x] Visual contract — exact Tailwind/CSS class system
- [x] Tested: Backend 20/20, Frontend 100% visual verification
- [x] Deployment health check passed

## Upcoming Tasks
- (P1) Blurhash/thumb_blur generation for instant perception
- (P1) Preview_short video generation for Netflix autoplay
- (P1) CDN-first delivery optimization
- (P2) A/B test hook text variations
- (P2) "Remix Variants" on share pages
- (P2) Admin dashboard WebSocket upgrade
