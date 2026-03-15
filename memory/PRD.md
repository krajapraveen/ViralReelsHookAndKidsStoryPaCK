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
- Gallery with 12+ professional AI-generated showcase items (HD thumbnails, presigned URLs)
- Rate limiting: 5/hour for normal users, exempt for admin/test/demo
- Worker auto-scaling: 1 min, 3 max, scales on queue depth
- 50+ creator tools
- Payment/billing system (Cashfree integration)
- Admin dashboard with analytics, user management, monitoring
- Credit system with refunds on failure (unlimited for admin/demo/UAT)

### Render Architecture Redesign (Mar 14, 2026)
- Single-pass FFmpeg encode (was 2N+1 FFmpeg calls)
- 960x540, 15fps, ultrafast, CRF 28, threads 1
- Real-time render progress via FFmpeg -progress flag
- ~27s solo render, 28/28 completions

### Landing Page Optimization (Mar 15, 2026)
- **Hero**: "Turn Any Story Into a Cinematic AI Video"
- **Trust Indicators**: 12,426+ videos, 40+ countries, 6 styles, ~90s
- **Problem → Solution**: "Creating animated videos is difficult" → "Visionary Suite solves this"
- **Example AI Videos**: 6 HD showcase cards from gallery API with remix counts + "Remix This" links
- **Features**: AI Story Writer, AI Scene Generator, AI Illustration Engine, AI Voice Narration, AI Video Renderer, Ready in Minutes
- **How It Works**: Write Your Story → AI Creates the Video → Download or Share
- **Remix Section**: "Click Remix to create your own version"
- **Final CTA**: "Your Story Deserves to Be Seen"
- **Page Flow**: Hero → Trust → Problem → Solution → Examples → Features → How It Works → Styles → Prompts → Pricing → Remix → Tools → CTA → Footer

### Geo-Based Currency (Mar 14, 2026)
- India (Asia/Kolkata timezone): Creator ₹699/mo, Pro ₹1,299/mo, TopUp ₹299
- International: Creator $9/mo, Pro $19/mo, TopUp $5
- Applied to: Landing, Pricing, UpsellModal, ContextualUpgrade

### Gallery & Showcase (Mar 14, 2026)
- 12 AI-generated showcase items with HD thumbnails
- Category filters, leaderboard, remix count badges
- Seeded via /app/backend/scripts/seed_gallery.py

### Credits & UpsellModal Fixes (Mar 14, 2026)
- Admin/exempt users show 999,999 credits
- UpsellModal properly checks isOpen prop
- X, backdrop click, "Maybe Later" all close the modal

### Critical Bug Fixes (Mar 15, 2026)
- **Google Auth**: Fixed AuthCallback.js error handling — extracts session_id from both hash & query params, shows backend `detail` errors properly
- **Photo to Comic**: Verified working — LLM available, test image generation successful
- **Reel Generator Admin Popup**: Fixed race condition — added `creditsLoaded` state, banners only render after credits API response. Admin (999999999 credits) sees NO banners
- **Gallery Auto-Seeding**: server.py startup now auto-seeds 12 showcase items when DB is empty (production-safe: skips if items exist)

## Backlog
- **P1**: Landing Page content optimization (detailed copy from user)
- **P1**: WebSocket real-time progress for video generation
- **P1**: Video watermarking for free plan users
- **P2**: Geo-IP integration with Cashfree payment gateway
- **P2**: Email notifications (BLOCKED on SendGrid)
- **P2**: Global credit state management refactor (React Context)

## Technical Notes
- R2 public URL returns 403 - all media served via presigned URLs (4hr expiry)
- Pipeline rendering: 960x540, 15fps, ultrafast, CRF 28, single-pass encode
- Geo-detection: Intl.DateTimeFormat().resolvedOptions().timeZone → Asia/Kolkata = INR
- Admin exempt emails: admin@creatorstudio.ai, test@visionary-suite.com, demo@visionary-suite.com
- Gallery seed: 12 showcase items auto-inserted on startup if pipeline_jobs has no is_showcase=true docs
