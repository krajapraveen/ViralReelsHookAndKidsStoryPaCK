# Visionary Suite — Product Requirements Document

## Original Problem Statement
Build a full-stack AI creator suite with a "compulsion-driven" growth engine. The platform enables users to create AI-generated story videos, comics, and visual content. The core growth strategy centers on viral story continuation — every story creates more stories through forking, sharing, and continuation loops.

## Core Architecture
- **Frontend**: React (port 3000)
- **Backend**: FastAPI (port 8001, all routes prefixed with /api)
- **Database**: MongoDB (via MONGO_URL env var)
- **Object Storage**: Cloudflare R2
- **Payments**: Cashfree
- **AI**: OpenAI (GPT-4o-mini, GPT Image 1, Sora 2, TTS), Gemini — via Emergent LLM Key
- **Auth**: Custom Google Identity Services (GIS) + JWT (replaced Emergent-hosted auth)

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

### P0: Custom Google Sign-In Migration (Complete — April 5, 2026)
- **Replaced Emergent-hosted auth** (`auth.emergentagent.com`) with direct Google Identity Services
- Frontend: `@react-oauth/google` `GoogleLogin` component renders native Google button
- Backend: `POST /api/auth/google-signin` verifies Google ID token server-side via `google-auth`
- Account linking: Existing users matched by email, new users created with 50 credits
- CSP updated to allow `accounts.google.com` in script-src, style-src, and frame-src
- Old Emergent callback endpoint preserved for backward compatibility
- No Emergent-branded pages visible in primary auth flow
- Prefetch hints for `/app` on login/signup pages

## Key API Endpoints
| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/auth/google-signin` | POST | None | Custom Google Sign-In (verify ID token) |
| `/api/auth/login` | POST | None | Email/password login |
| `/api/auth/register` | POST | None | Email/password signup |
| `/api/share/{shareId}/fork` | POST | None | Fork/continue a story |
| `/api/public/explore-stories` | GET | None | Browse stories with genre filter |
| `/api/admin/metrics/growth` | GET | Admin | Growth funnel metrics |
| `/api/admin/metrics/story-performance` | GET | Admin | Per-story performance data |

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

### P1 — Next Up
- Publish Google OAuth consent screen (exit Testing mode)
- Premium tier download quality differentiation
- A/B test hook text variations

### P2 — Future
- Character-driven auto-share prompts
- Remix Variants on share pages
- Story Chain leaderboard
- Personalization / Daily Packs
- Admin Dashboard WebSocket upgrades
