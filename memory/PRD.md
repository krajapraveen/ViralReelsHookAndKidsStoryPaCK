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

### Phase 5: Growth Validation / DATA MODE (Complete — April 5, 2026)
- 30 Viral Seed Stories (10 mystery, 10 thriller, 5 emotional, 5 fantasy)
- Growth Dashboard with funnel metrics
- Story-Level Performance Tracking
- Public Explore API

### P0: Custom Google Sign-In (In Progress — April 6, 2026)
- Frontend: `@react-oauth/google` `GoogleLogin` component (credential/JWT flow)
- Backend: `POST /api/auth/google-signin` verifies Google ID token via `google.oauth2.id_token.verify_oauth2_token()`
- No `GOOGLE_CLIENT_SECRET` needed — JWT verified locally with just `GOOGLE_CLIENT_ID`
- Account linking by email or `google_sub`
- CSP configured for `accounts.google.com`
- Status: Code deployed, awaiting user verification of popup → redirect flow

### P0: Payment Hardening (Complete — April 6, 2026)
- Fixed double-crediting vulnerability: webhook now checks ALL terminal states
- Added idempotency guard in `award_credits()` via `credit_ledger` duplicate check
- Webhook now handles subscription activation (mirrors verify handler)
- Static webhook URL via `CASHFREE_WEBHOOK_URL` env var (no more dynamic derivation)
- 5/5 race condition tests passing (verify-first, webhook-first, duplicates, repeated calls, webhook-only)

## Key API Endpoints
| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/auth/google-signin` | POST | None | Custom Google Sign-In (verify JWT credential) |
| `/api/auth/login` | POST | None | Email/password login |
| `/api/auth/register` | POST | None | Email/password signup |
| `/api/cashfree/create-order` | POST | JWT | Create Cashfree payment order |
| `/api/cashfree/verify` | POST | JWT | Verify payment and activate subscription |
| `/api/cashfree/webhook` | POST | None | Cashfree webhook handler (idempotent) |
| `/api/share/{shareId}/fork` | POST | None | Fork/continue a story |
| `/api/public/explore-stories` | GET | None | Browse stories with genre filter |
| `/api/admin/metrics/growth` | GET | Admin | Growth funnel metrics |

## Credentials
- Test User: `test@visionary-suite.com` / `Test@2026#`
- Admin User: `admin@creatorstudio.ai` / `Cr3@t0rStud!o#2026`
- Google OAuth Client ID: `972517860807-cjgrpibkrg4n1ncdgs4kvmnqfpasgkao.apps.googleusercontent.com`

## Important: Google OAuth Testing Mode
The Google OAuth app is currently in **Testing** mode. Only users added as test users in Google Cloud Console can sign in. To enable public sign-in:
1. Go to https://console.cloud.google.com/apis/credentials/consent
2. Click **Publish App**
3. Complete verification if required by Google

## Prioritized Backlog

### P0 — Immediate
- Verify Google Auth popup → redirect flow on production (user test pending)
- Deploy payment hardening to production
- Run live ₹149 smoke test post-deploy
- Audit 2 real paying users from yesterday on production DB

### P1 — Next Up
- Publish Google OAuth consent screen (exit Testing mode)
- Premium tier download quality differentiation
- A/B test hook text variations
- High-conversion Google button copy + UI layout

### P2 — Future
- Character-driven auto-share prompts
- Remix Variants on share pages
- Story Chain leaderboard
- Personalization / Daily Packs
- Admin Dashboard WebSocket upgrades
