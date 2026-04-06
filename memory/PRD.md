# Visionary Suite — Product Requirements Document

## Original Problem Statement
Build a full-stack AI creator suite with a "compulsion-driven" growth engine. Convert the system from User → Create → Done into User → Create → Share → Viewer → Create → Share → Repeat.

## Core Architecture
- **Frontend**: React (port 3000)
- **Backend**: FastAPI (port 8001, all routes prefixed with /api)
- **Database**: MongoDB (via MONGO_URL env var)
- **Object Storage**: Cloudflare R2
- **Payments**: Cashfree (production keys, static webhook URL)
- **AI**: OpenAI (GPT-4o-mini, GPT Image 1, Sora 2, TTS), Gemini — via Emergent LLM Key
- **Auth**: Custom Google Identity Services (GIS) + JWT

## What's Been Implemented

### Core Platform (Complete)
- User auth (Google + email/password), Story Video Studio, Comic Storybook Creator, Coloring Book Generator, GIF Maker
- Credits system (50 initial credits, Cashfree payments), Gallery, sharing

### Safety & Moderation (Complete)
- Safety Playground, content moderation pipeline, anti-abuse service

### Viral Story Engine (Complete)
- Fork API, Share Page with CTAs, Post-generation Share Modal

### Growth Validation (Complete)
- 30 Viral Seed Stories, Growth Dashboard, Public Explore API

### Custom Google Sign-In (Complete)
- `@react-oauth/google` `GoogleLogin` credential/JWT flow

### Payment Hardening (Complete)
- Idempotency guard, static webhook URL

### My Space — Real-Time Source of Truth (Complete — All 3 Phases)
- **Phase 1**: 3-section layout (In Progress / Completed / Failed), granular stage labels, auto-redirect from StoryVideoPipeline, 4s polling
- **Phase 2**: Toast + browser notification on completion, share-link API (`POST /api/story-engine/share-link/{job_id}`), one-tap WhatsApp share, "Just Completed" green glow badge
- **Phase 3**: Auto-download preference toggle (localStorage), post-completion prompt modal (Download / WhatsApp / Create Another), prompt deduplication

### Growth Engine — P0 (Complete — April 6, 2026)

#### 1. Share Page — Video-First Growth Funnel
- Route: `/share/:shareId` — public, no auth needed
- Above-the-fold: autoplay video (muted, looped), strong title, social proof bar
- Primary CTA block: "Create your own video in 30 seconds" / "Made with AI. No editing needed. Free to start."
- Two CTAs: "Create Your Video — Free" (pulsing gradient) + "Remix This Video"
- Value props grid: Made with AI / No editing needed / Free to start
- Share tools: WhatsApp + Copy Link
- Bottom CTA repeats for scrollers: "Your turn. Make something amazing."
- Header: persistent "Create yours" button
- Backend enriched: `GET /api/share/{share_id}` now returns `videoUrl`, `animationStyle`, `generationId` from source job

#### 2. First Video Free — Zero Friction Onboarding
- New users with zero previous jobs get their first generation free (credits skipped)
- Backend: `POST /api/story-engine/create` checks job count, sets `skip_credits=True` for first-timers
- API: `GET /api/story-engine/first-video-free` returns eligibility status
- Guest mode (IP-based) already supports 1 free generation per IP

#### 3. 1-Tap Remix
- "Remix This Video" button on share page calls `POST /api/share/{shareId}/fork`
- Stores remix_data in localStorage with parent prompt, style, characters, tone
- Redirects to `/app/story-video-studio` which picks up remix_data and prefills
- Fork count incremented on parent share, tracked via share_events

## Key API Endpoints
| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/auth/google-signin` | POST | None | Google Sign-In |
| `/api/auth/login` | POST | None | Email/password login |
| `/api/cashfree/create-order` | POST | JWT | Create payment order |
| `/api/cashfree/webhook` | POST | None | Payment webhook (idempotent) |
| `/api/story-engine/create` | POST | Optional | Create video (first-video-free for new users) |
| `/api/story-engine/user-jobs` | GET | JWT | All user jobs |
| `/api/story-engine/share-link/{job_id}` | POST | JWT | Generate share link + WhatsApp URL |
| `/api/story-engine/first-video-free` | GET | Optional | Check first-free eligibility |
| `/api/share/{shareId}` | GET | None | Share data with videoUrl, animationStyle |
| `/api/share/{shareId}/fork` | POST | None | Remix/fork a story |
| `/api/share/create` | POST | JWT | Create shareable link |

## Credentials
- Test User: `test@visionary-suite.com` / `Test@2026#`
- Admin User: `admin@creatorstudio.ai` / `Cr3@t0rStud!o#2026`

## Prioritized Backlog

### P1 — Next Up
1. Watermark system — "Visionary Suite | Create yours → visionary-suite.com" on all videos
2. Referral loop — reward users who drive signups via share links

### P1 — Optimization
- Pipeline parallelization (script → voice + images in parallel)
- Analytics instrumentation (project_created, download_triggered, share_clicked)
- Publish Google OAuth consent screen

### P2 — Future
- A/B test hook text and CTA variations on share page
- Story Chain leaderboard
- Daily viral ideas & multi-platform share
- Admin Dashboard WebSocket upgrades
