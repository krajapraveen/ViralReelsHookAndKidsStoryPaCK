# Visionary Suite — Product Requirements Document

## Original Problem Statement
Build a full-stack AI creator suite with a "compulsion-driven" growth engine. The platform enables users to create AI-generated story videos, comics, and visual content. The core growth strategy centers on viral story continuation — every story creates more stories through forking, sharing, and continuation loops.

## Core Architecture
- **Frontend**: React (port 3000)
- **Backend**: FastAPI (port 8001, all routes prefixed with /api)
- **Database**: MongoDB (via MONGO_URL env var)
- **Object Storage**: Cloudflare R2
- **Payments**: Cashfree (production keys, static webhook URL)
- **AI**: OpenAI (GPT-4o-mini, GPT Image 1, Sora 2, TTS), Gemini — via Emergent LLM Key
- **Auth**: Custom Google Identity Services (GIS) + JWT

## User Personas
1. **Creator** — Makes story videos, comics, coloring books
2. **Viewer/Continuer** — Discovers stories via share pages, continues them
3. **Admin** — Monitors platform health, growth metrics, revenue

## What's Been Implemented

### Phase 1-2: Core Platform (Complete)
- User auth (Google + email/password)
- Story Video Studio, Comic Storybook Creator, Coloring Book Generator, GIF Maker
- Credits system (50 initial credits, Cashfree payments)
- Gallery, sharing, social features

### Phase 3: Safety (Complete)
- Safety Playground, content moderation pipeline, anti-abuse service

### Phase 4: Viral Story Engine (Complete)
- Fork API, Share Page with "Continue This Story" CTA
- Post-generation Share Modal, A/B testing, alive signals

### Phase 5: Growth Validation / DATA MODE (Complete)
- 30 Viral Seed Stories, Growth Dashboard with funnel metrics
- Story-Level Performance Tracking, Public Explore API

### Custom Google Sign-In (Complete — April 6, 2026)
- Frontend: `@react-oauth/google` `GoogleLogin` component (credential/JWT flow)
- Backend: `POST /api/auth/google-signin` verifies Google ID token
- Account linking by email or `google_sub`

### Payment Hardening (Complete — April 6, 2026)
- Fixed double-crediting vulnerability, added idempotency guard in `award_credits()`
- Static webhook URL via `CASHFREE_WEBHOOK_URL`

### My Space Phase 1 — Real-Time Source of Truth (Complete — April 6, 2026)
- 3-section layout: In Progress (animated progress bars), Completed (video cards), Failed (error + retry)
- Granular stage labels (e.g., "Creating artwork", "Rendering video")
- Auto-redirect from StoryVideoPipeline to `/app/my-space?projectId=<id>` on generation start
- Real-time polling every 4s for in-progress jobs
- Section collapse/expand toggles with counts
- Tested: 100% backend (12/12), 100% frontend

### My Space Phase 2 — Notifications & Actions (Complete — April 6, 2026)
- In-app completion toast notification ("Your video 'Title' is ready!")
- Browser push notification on video completion (via Notification API)
- Notification toggle (bell icon) in header
- Completion action tray: Watch, Download, WhatsApp share
- Share-link generation API: `POST /api/story-engine/share-link/{job_id}` (idempotent)
- One-tap WhatsApp share via `wa.me` with pre-filled text
- "Just Completed" badge with green glow animation on newly finished videos
- Tested: All features verified

## Key API Endpoints
| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/auth/google-signin` | POST | None | Custom Google Sign-In (verify JWT credential) |
| `/api/auth/login` | POST | None | Email/password login |
| `/api/auth/register` | POST | None | Email/password signup |
| `/api/cashfree/create-order` | POST | JWT | Create Cashfree payment order |
| `/api/cashfree/verify` | POST | JWT | Verify payment and activate subscription |
| `/api/cashfree/webhook` | POST | None | Cashfree webhook handler (idempotent) |
| `/api/story-engine/user-jobs` | GET | JWT | Get all user jobs (merged story engine + legacy) |
| `/api/story-engine/share-link/{job_id}` | POST | JWT | Generate share link + WhatsApp URL for completed job |
| `/api/share/create` | POST | JWT | Create a shareable link for any creation |
| `/api/share/{shareId}` | GET | None | Get share data with OG tags |
| `/api/share/{shareId}/fork` | POST | None | Fork/continue a story |
| `/api/public/explore-stories` | GET | None | Browse stories with genre filter |

## Credentials
- Test User: `test@visionary-suite.com` / `Test@2026#`
- Admin User: `admin@creatorstudio.ai` / `Cr3@t0rStud!o#2026`

## Prioritized Backlog

### P0 — Immediate (My Space Phase 3)
- Auto-download preference trigger on completion
- Share prompt after video completion

### P1 — Next Up
- Pipeline parallelization (script → voice + images in parallel → composition)
- Analytics instrumentation (project_created, download_triggered, etc.)
- Publish Google OAuth consent screen (exit Testing mode)

### P0 — Viral Growth Engine (1M Users System)
- Share page with CTAs (convert viewers to creators)
- Watermark system ("Created with Visionary Suite")
- First video free (zero friction onboarding)
- 1-Tap "Remix this video" button
- Daily viral ideas & multi-platform share

### P2 — Future
- A/B test hook text variations
- Remix Variants on share pages
- Story Chain leaderboard
- Admin Dashboard WebSocket upgrades
