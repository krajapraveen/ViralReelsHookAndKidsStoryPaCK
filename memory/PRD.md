# Visionary-Suite PRD

## Product
AI-powered Story Video Studio and Creator Tools Platform. Generates story videos, comics, coloring books, GIFs, reels, bios, and more for content creators.

## Core Architecture
- **Frontend**: React + Tailwind CSS + Shadcn/UI (dark theme: #060B1A base, #0B1220 cards)
- **Backend**: FastAPI + MongoDB
- **Storage**: Cloudflare R2 (served via presigned URLs - public URL disabled)
- **AI**: OpenAI GPT-4o-mini, GPT Image 1, Sora 2, TTS + Gemini Nano Banana
- **Payment**: Cashfree
- **Workers**: Auto-scaling pipeline worker pool (1-3 workers) + 6 feature pools

## Key Users
- **Test**: test@visionary-suite.com / Test@2026#
- **Admin**: admin@creatorstudio.ai / Cr3@t0rStud!o#2026

## What's Implemented (Complete)

### Core Platform
- Full AI story video pipeline (script > scenes > images > voices > render > upload)
- Gallery with 30+ professional showcase items (AI-generated thumbnails, presigned URLs)
- Rate limiting: 5/hour for normal users, exempt for admin/test/demo
- Worker auto-scaling: 1 min, 3 max, scales on queue depth
- 50+ creator tools (reel generator, story generator, coloring book, comic maker, etc.)
- Payment/billing system (Cashfree integration)
- Admin dashboard with analytics, user management, monitoring
- Credit system with refunds on failure (unlimited for admin/demo/UAT)
- Error boundary with recovery options

### Render Architecture Redesign (Completed Mar 14, 2026)
- **REMOVED** scene-by-scene mp4 clip rendering (was 2N+1 FFmpeg calls)
- **REPLACED** with single-pass FFmpeg encode using filter_complex concat
- Resolution: 960x540, FPS: 15, libx264 ultrafast, CRF 28, threads 1
- Real-time render progress via FFmpeg -progress flag
- Render time: ~27s solo (3 scenes), ~65-85s concurrent
- 28 successful completions, 0 render failures

### Landing Page & Pricing Fixes (Completed Mar 14, 2026)
- **Removed "Start Free" button** from landing page nav (desktop + mobile)
- **Geo-based currency detection**: INR (₹) for India users, USD ($) for international
  - India: Creator ₹699/mo (300 credits), Pro ₹1,299/mo (1000 credits), TopUp ₹299 (150 credits)
  - International: Creator $9/mo (100 credits), Pro $19/mo (250 credits), TopUp $5 (50 credits)
  - Detection via browser timezone (Asia/Kolkata = India)
- Applied to: Landing page, Pricing page, UpsellModal, ContextualUpgrade

### Gallery & Showcase Overhaul (Completed Mar 14, 2026)
- Seeded 12 AI-generated showcase items with HD thumbnails
- Gallery now shows 48+ items with category filters
- "Most Remixed Creations" leaderboard with remix count badges
- Categories: All, 2D Cartoon, Watercolor, Anime, Comic Book, 3D Animation, Claymation
- Remix button on gallery cards for engagement

### Credits & UpsellModal Fixes (Completed Mar 14, 2026)
- Admin/exempt users now show 999,999 credits (was 0)
- `/api/credits/balance` returns `unlimited: true` for admin users
- UpsellModal properly checks `isOpen` prop — no longer blocks admin
- X button, backdrop click, and "Maybe Later" all properly close the modal
- Fixed in: PhotoToComic, ReelGenerator, ComicStorybookBuilder, PhotoReactionGIF

### Remix & Variations Engine
- CreationActionsBar component across all 7 tools
- Remix tracking, leaderboard, cross-tool conversions
- Pre-fill logic for remix flow

### P0 Pipeline Stabilization
- Stuck job recovery (background service)
- Asset download retries with presigned URL regeneration
- Frontend stuck detection with retry option

## API Endpoints

### Credits
- `GET /api/credits/balance` — Returns credits (999999 for admin), unlimited flag, plan

### Gallery
- `GET /api/pipeline/gallery` — Showcases + user videos, presigned URLs
- `GET /api/pipeline/gallery/leaderboard` — Top remixed creations
- `GET /api/pipeline/gallery/categories` — Category counts

### Remix
- `GET /api/remix/variations/{tool}` — Variation config
- `POST /api/remix/track` — Track remix event
- `GET /api/remix/stats` — Analytics

## Backlog
- **P1**: WebSocket real-time progress for video generation
- **P1**: Video watermarking for free plan users
- **P1**: Expand contextual upgrade prompts
- **P2**: Email notifications (BLOCKED on SendGrid)
- **P2**: Break Dashboard.js into smaller components

## Technical Notes
- R2 public URL returns 403 - all media served via presigned URLs (4hr expiry)
- Pipeline rendering: 960x540, 15fps, ultrafast, CRF 28, single-pass encode
- Stuck job recovery: every 2 min, 10 min timeout, auto credit refund
- Geo-detection: `Intl.DateTimeFormat().resolvedOptions().timeZone` → Asia/Kolkata = INR
- Admin exempt emails: admin@creatorstudio.ai, test@visionary-suite.com, demo@visionary-suite.com
