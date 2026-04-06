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
- User auth (Google + email/password), Story Video Studio, Comic Storybook Creator, Coloring Book Generator, GIF Maker
- Credits system (50 initial credits, Cashfree payments), Gallery, sharing, social features

### Phase 3: Safety (Complete)
- Safety Playground, content moderation pipeline, anti-abuse service

### Phase 4: Viral Story Engine (Complete)
- Fork API, Share Page with "Continue This Story" CTA, Post-generation Share Modal, A/B testing

### Phase 5: Growth Validation (Complete)
- 30 Viral Seed Stories, Growth Dashboard with funnel metrics, Public Explore API

### Custom Google Sign-In (Complete — April 6, 2026)
- `@react-oauth/google` `GoogleLogin` credential/JWT flow, server-side verification

### Payment Hardening (Complete — April 6, 2026)
- Idempotency guard in `award_credits()`, static webhook URL via `CASHFREE_WEBHOOK_URL`

### My Space Phase 1 — Real-Time Source of Truth (Complete — April 6, 2026)
- 3-section layout: In Progress / Completed / Failed
- Granular stage labels, auto-redirect from StoryVideoPipeline, 4s polling, section collapse/expand

### My Space Phase 2 — Notifications & Actions (Complete — April 6, 2026)
- Toast + browser notification on completion, notification toggle
- Share-link API: `POST /api/story-engine/share-link/{job_id}` (idempotent)
- One-tap WhatsApp share, "Just Completed" green glow badge

### My Space Phase 3 — Completion Conversion (Complete — April 6, 2026)
- Auto-download preference toggle (persisted in localStorage `vs_auto_download`)
- Post-completion prompt modal with 3 CTAs: Download / Share on WhatsApp / Create Another
- Prompt deduplication (only shows once per job via promptedJobIds ref)
- Auto-triggers download when preference is on and job completes
- No page refresh required — real-time polling handles all transitions

## Key API Endpoints
| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/auth/google-signin` | POST | None | Google Sign-In (verify JWT credential) |
| `/api/auth/login` | POST | None | Email/password login |
| `/api/cashfree/create-order` | POST | JWT | Create Cashfree payment order |
| `/api/cashfree/verify` | POST | JWT | Verify payment |
| `/api/cashfree/webhook` | POST | None | Cashfree webhook (idempotent) |
| `/api/story-engine/user-jobs` | GET | JWT | All user jobs (story engine + legacy) |
| `/api/story-engine/share-link/{job_id}` | POST | JWT | Generate share link + WhatsApp URL |
| `/api/share/create` | POST | JWT | Create shareable link for any creation |
| `/api/share/{shareId}` | GET | None | Get share data with OG tags |

## Credentials
- Test User: `test@visionary-suite.com` / `Test@2026#`
- Admin User: `admin@creatorstudio.ai` / `Cr3@t0rStud!o#2026`

## Prioritized Backlog

### P0 — Growth Engine (Next — completion → sharing → viewer → creation loop)
1. Share page with strong CTA (convert viewers to creators)
2. First video free (zero friction onboarding)
3. 1-Tap Remix this video
4. Watermark system ("Created with Visionary Suite")
5. Referral loop

### P1 — Optimization
- Pipeline parallelization (script → voice + images in parallel → composition)
- Analytics instrumentation (project_created, download_triggered, etc.)
- Publish Google OAuth consent screen (exit Testing mode)

### P2 — Future
- A/B test hook text variations
- Remix Variants on share pages
- Story Chain leaderboard
- Admin Dashboard WebSocket upgrades
