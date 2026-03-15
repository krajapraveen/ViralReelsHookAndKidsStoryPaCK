# Visionary-Suite PRD

## Product
AI-powered Story Video Studio and Creator Tools Platform. Generates story videos, comics, coloring books, GIFs, reels, bios, and more for content creators.

## Core Architecture
- **Frontend**: React + Tailwind CSS + Shadcn/UI (dark theme: #060B1A base, #0B1220 cards)
- **Backend**: FastAPI + MongoDB
- **Storage**: Cloudflare R2 (served via presigned URLs - public URL disabled)
- **AI**: OpenAI GPT-4o-mini, GPT Image 1, Sora 2, TTS + Gemini Nano Banana
- **Payment**: Cashfree (geo-IP: INR for India, USD for international)
- **Workers**: Auto-scaling pipeline worker pool (1-3 workers) + 6 feature pools
- **Real-time**: WebSocket progress updates via /ws/progress

## Key Users
- **Test**: test@visionary-suite.com / Test@2026#
- **Admin**: admin@creatorstudio.ai / Cr3@t0rStud!o#2026

## What's Implemented (Complete)

### Core Platform
- Full AI story video pipeline (script > scenes > images > voices > render > upload)
- Gallery with 30 professional AI-generated showcase items (HD thumbnails, presigned URLs)
- Rate limiting: 5/hour for normal users, exempt for admin/test/demo
- Worker auto-scaling: 1 min, 3 max, scales on queue depth
- 50+ creator tools
- Payment/billing system (Cashfree integration with geo-IP)
- Admin dashboard with analytics, user management, monitoring
- Credit system with refunds on failure (unlimited for admin/demo/UAT)

### Render Architecture Redesign (Mar 14, 2026)
- Single-pass FFmpeg encode (was 2N+1 FFmpeg calls)
- 960x540, 15fps, ultrafast, CRF 28, threads 1
- Real-time render progress via FFmpeg -progress flag
- ~27s solo render, 28/28 completions

### Landing Page Optimization (Mar 15, 2026)
- **Hero**: "Turn Any Story Into a Cinematic AI Video"
- **Speed line**: "Create animated videos from stories in under 90 seconds."
- **Subheading**: "Write a story and our AI instantly generates scenes, illustrations, narration, and a finished animated video ready to download or share."
- **CTAs**: "Create Your First Video" (primary) + "Explore Gallery" (secondary)
- **Trust Signals**: 12,000+ Videos Created | 40+ Countries | 6 Animation Styles | ~90s Generation
- **Page Flow**: Hero > Trust > Problem > Solution > Examples > Features > How It Works > Styles > Prompts > Pricing > Remix > Tools > CTA > Footer

### Geo-Based Currency (Mar 14-15, 2026)
- India: Creator ₹749/mo, Pro ₹1,599/mo, TopUp packs from ₹399
- International: Creator $9/mo, Pro $19/mo, TopUp from $5
- Applied to: Landing, Pricing, UpsellModal, ContextualUpgrade, Cashfree
- Detection: Cloudflare cf-ipcountry header + Accept-Language fallback

### Video Watermarking (Mar 15, 2026)
- FFmpeg drawtext filter: "Made with Visionary-Suite.com"
- Semi-transparent (white@0.35), bottom-right corner, fontsize 16
- **Free users only** — Creator/Pro/Admin/Demo plans = no watermark
- Plan check at job creation: `apply_watermark = user_plan not in paid_plans`

### WebSocket Real-Time Progress (Mar 15, 2026)
- Backend: `/ws/progress` endpoint with ConnectionManager
- Frontend: `useWebSocketProgress` hook with auto-reconnect (5 retries)
- Pipeline integration: Broadcasts at stage start, completion, and failure
- Stages: Initializing > Generating scenes > Creating images > Generating voiceover > Rendering video > Uploading output > Completed

### Social Sharing (Mar 15, 2026)
- 7 platforms: WhatsApp, Twitter/X, Facebook, LinkedIn, Instagram, Telegram, Email
- Copy Link + QR Code generation
- Share Card download (canvas-rendered OG preview)
- OpenGraph meta tags: og:title, og:description, og:image, og:site_name = "Visionary Suite"
- Remix CTA in all shared links

### Global Credit State (Mar 15, 2026)
- `CreditContext.js` provides: credits, plan, isFreeTier, creditsLoaded, refreshCredits
- `CreditProvider` wraps entire app in App.js
- `useCredits()` hook available to all components
- Eliminates credit race conditions across all tool pages

### Gallery & Showcase (Mar 14-15, 2026)
- 30 AI-generated showcase items with HD thumbnails
- Themes: dragon village, robot Mars, bedtime forest, underwater kingdom, superhero, animals, candy pirates, baker mice, ice princess, robo teacher, mouse knight, dinosaur party, time-traveling cat, singing flowers, space school, wolf dance, cloud shepherd, rainbow cave, penguin chef, lighthouse wishes, ninja bunnies, firefly festival, tiny astronaut, enchanted library, paper airplane race, brave submarine, mountain giant, fox detective, solar school bus, autumn leaf ballet
- Category filters, leaderboard, remix count badges
- Auto-seed on startup if DB empty (`server.py`)

### Cashfree Geo-IP Payment (Mar 15, 2026)
- Geo-detected currency: India=INR, International=USD
- Products endpoint returns displayPrice, displayCurrency, displaySymbol
- Order creation uses geo-detected or client-specified currency
- Currently in PRODUCTION mode (sandbox ready for testing)

### Bug Fixes (Mar 15, 2026)
- Google Auth: Fixed AuthCallback.js error handling (detail field, session_id from hash+query)
- Photo to Comic: Verified working (LLM available, test image gen successful)
- Reel Generator Admin Popup: Fixed race condition with creditsLoaded state
- Gallery Auto-Seeding: server.py auto-seeds on startup when DB empty
- **Story Video Pipeline**: Fixed local image deletion after R2 upload — files now preserved until render completes
- **Comic Storybook Rating Loop**: Fixed stale closure bug — replaced useState with useRef for polling interval
- **Landing Page Testimonials**: Added 10 realistic reviews (4.4/5 avg, mix of 4★ and 5★)

## Backlog
- **P2**: Email notifications (BLOCKED on SendGrid upgrade)
- **P3**: Multi-language support for narration
- **P3**: Custom voice cloning integration

### Video Queue Priority (Mar 15, 2026)
- Priority levels: Admin=0 (highest), Paid=1, Free=10 (standard)
- `PriorityQueue` with `PriorityJob` dataclass: `(priority, sequence)` ordering
- FIFO within each tier via monotonic sequence counter
- Anti-starvation: Free jobs boosted from priority 10 → 2 after 120s wait
- Worker analytics: avg_wait_ms per tier, starvation boost count
- Job fields: queue_priority, queue_tier, queued_at, queue_wait_ms, picked_up_at
- UI: "Priority Queue" badge (amber, Zap icon) for paid/admin in WaitingExperience
- Free users see normal progress (no negative messaging)
- Future-ready: easy to add Pro > Creator, Enterprise dedicated queue

## Technical Notes
- R2 public URL returns 403 - all media served via presigned URLs (4hr expiry)
- Pipeline rendering: 960x540, 15fps, ultrafast, CRF 28, single-pass encode
- Geo-detection: Cloudflare cf-ipcountry header > Accept-Language > default USD
- Admin exempt emails: admin@creatorstudio.ai, test@visionary-suite.com, demo@visionary-suite.com
- Gallery seed: 30 showcase items auto-inserted on startup if pipeline_jobs has no is_showcase=true docs
- WebSocket: Best-effort broadcasts, never block pipeline on failure
