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

## Gallery Discovery Engine (BUILT Mar 31 2026) — P0 COMPLETE

### Before vs After
**BEFORE**: Empty "No videos found" page. Zero content. Zero engagement. Users leave immediately.
**AFTER**: Netflix-style discovery engine with featured hero, 9 category rails, explore grid, search/filters/sort, preview modal, Remix on every card, seeded demo content. Gallery NEVER shows empty state.

### Backend — New APIs
| Endpoint | Purpose |
|----------|---------|
| `GET /api/gallery/featured` | Returns 3 featured hero items |
| `GET /api/gallery/rails` | Returns 9 categorized horizontal rails |
| `GET /api/gallery/explore?category=X&sort=Y&cursor=Z` | Paginated explore feed with filter/sort |
| `GET /api/gallery/categories` | Category list with counts |

### Seeding System
- `gallery_content` collection seeded on startup via `seed_gallery_if_empty()`
- 23 demo items across 7 categories: Kids Stories, Cinematic AI, Emotional, Reels & Shorts, Business, Luxury, Educational
- Each item: title, description, thumbnail, duration, views/likes/remixes, tags, category
- Real `pipeline_jobs` merged with seeded content in all API responses
- Gallery NEVER empty — seeded content fills gaps when real content is sparse

### Frontend Components
| Component | Purpose |
|-----------|---------|
| `FeaturedHero` | Auto-cycling hero with gradient overlays, stats, Watch/Remix/Create CTAs |
| `ContentRail` | Horizontal scroll rail with nav arrows, category icon |
| `GalleryCard` | Thumbnail + stats overlay + duration badge + hover actions + Remix CTA |
| `PreviewModal` | Full video/thumbnail preview with stats, Remix button |
| `HeroSkeleton / CardSkeleton / RailSkeleton` | Instant skeleton loading |

### Category Rails (9 total)
Trending Now, Most Remixed, Kids Stories, Reels & Shorts, Emotional Stories, Cinematic AI, Business & Promo, Luxury & Lifestyle, Educational

### Explore Section
- Text search (client-side filtering)
- Category filter tabs (All, Trending, Kids, Reels, Emotional, Cinematic, Business, Luxury, Educational)
- Sort modes (Trending, Newest, Most Remixed)
- 4-column desktop / 2-column mobile grid
- Bottom CTA: "Pick a story you love. Make it yours."

### Remix Flow
1. Click Remix on any card → check auth
2. Not logged in → redirect to /signup with remix context
3. Logged in → store remix_data in localStorage + navigate to /app/story-video-studio
4. Story Video Studio picks up remix_data and prefills prompt

## Reel Creation Engine (BUILT Mar 31 2026) — P0 COMPLETE
- 12 outcome-driven input controls (Platform, Hook Style, Reel Format, CTA, Objective, Output Type + Advanced)
- 7-tab structured output (Script, Hook Variants, Caption, Hashtags, Shot List, Visual Prompts, Voiceover)
- Video generation config modal (style, voiceover, subtitles, aspect ratio, quality, estimated credits)
- 8 performance variations (Stronger Hook, Higher Retention, More Emotional, More Viral, More Sales, Shorter, Better CTA, Platform Optimized)
- AI Recommendations panel

## Premium Login UX (VERIFIED Mar 31 2026)
- Branded overlay masks auth.emergentagent.com transition (150ms)
- AuthCallback branded loading + error states
- No Emergent text on app-controlled screens

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
| `frontend/src/pages/Gallery.js` | Netflix-style gallery page |
| `frontend/src/pages/ReelGenerator.js` | Reel Creation Engine |
| `backend/models/schemas.py` | GenerateReelRequest with new fields |
| `backend/shared.py` | Upgraded reel prompts |
| `frontend/src/components/AuthLaunchOverlay.js` | Auth overlay |
| `frontend/src/pages/AuthCallback.js` | Branded auth callback |
| `frontend/src/pages/Dashboard.js` | User menu with logout |
| `frontend/src/pages/Profile.js` | Logout button in header |

## Completed (This Session — Mar 31 2026)
- [x] Premium Login UX — 14/14 tests passed
- [x] Logout button — Dashboard + Profile, desktop + mobile
- [x] Reel Creation Engine P0 — 11/11 backend + all frontend verified
- [x] Gallery Discovery Engine P0 — 18/18 backend + all frontend P0 verified (100% pass)

## Upcoming (P1)
### Gallery P1
1. Immersive TikTok-style fullscreen viewer (swipe navigation, autoplay)
2. Hover auto-preview on desktop cards
3. Continue Watching / Your Creations sections for logged-in users
4. Search improvements (server-side, tag-based)

### Reel P1
5. Reference-Based Generation (paste URL/text)
6. Presets (Viral Hook, Luxury, Product Promo, etc.)

### Platform P1
7. Anti-crop watermark improvements + dynamic per-user watermarks
8. Telemetry pipeline
9. Notification Center improvements

## Future/Backlog (P2)
- Gallery: Ranking algorithm, leaderboard, creator profiles, comments, infinite scroll
- Reel: History + Compare, Brand Kit, Output Scoring
- Platform: Forensic watermarking, admin leak dashboard, WebSocket admin dashboard
