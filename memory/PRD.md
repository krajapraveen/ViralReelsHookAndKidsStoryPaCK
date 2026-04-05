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
- **Auth**: Emergent-managed Google Auth + JWT

## User Personas
1. **Creator** — Makes story videos, comics, coloring books
2. **Viewer/Continuer** — Discovers stories via share pages, continues them
3. **Admin** — Monitors platform health, growth metrics, revenue

## What's Been Implemented

### Phase 1-2: Core Platform (Complete)
- User auth (Google + email/password)
- Story Video Studio (AI generation pipeline)
- Comic Storybook Creator, Coloring Book Generator, GIF Maker
- Credits system (50 initial credits, Cashfree payments)
- Gallery, sharing, social features

### Phase 3: Safety (Complete)
- Safety Playground (admin internal tool)
- Content moderation pipeline, Anti-abuse service

### Phase 4: Viral Story Engine (Complete)
- Fork API: `POST /api/share/{shareId}/fork`
- Redesigned Share Page with "Continue This Story" CTA
- Post-generation Share Modal
- A/B testing on Landing Page (3 variants)
- Alive signals, character-driven hooks, momentum-based social proof

### Phase 5: Growth Validation / DATA MODE (Complete — April 5, 2026)
- **30 Viral Seed Stories** (10 mystery, 10 thriller, 5 emotional, 5 fantasy)
- **Growth Dashboard** with Continuation Rate, Branches/Story, Funnel Drop-off
- **Story-Level Performance Tracking** (per-story views/forks/continuation rate, genre breakdown)
- **Public Explore API** (`GET /api/public/explore-stories` with genre filtering)

### P0: Auth Flow Optimization (Complete — April 5, 2026)
- Logged-in users skip /login and /signup instantly (redirect to /app)
- Google sign-in uses requestAnimationFrame (no 150ms setTimeout)
- AuthLaunchOverlay slow notice at 4s (was 6s)
- AuthCallback stripped to minimal UI (spinner + "Signing you in")
- Referral attribution is fire-and-forget (no blocking await)
- App shell preloaded via prefetch link on login/signup pages
- No artificial delays anywhere in auth flow

### Trust & Consistency Fixes (Complete)
- Fixed Security tab, truth-based admin metrics
- Credit system consistency (50 credits standard)
- Diverse "Live on the Platform" feed

## Key API Endpoints
| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/share/{shareId}/fork` | POST | None | Fork/continue a story |
| `/api/share/{shareId}` | GET | None | Get share page data |
| `/api/public/explore-stories` | GET | None | Browse stories with genre filter |
| `/api/public/featured-story` | GET | None | Get featured story for landing |
| `/api/admin/metrics/growth` | GET | Admin | Growth funnel metrics |
| `/api/admin/metrics/story-performance` | GET | Admin | Per-story performance data |

## Credentials
- Test User: `test@visionary-suite.com` / `Test@2026#`
- Admin User: `admin@creatorstudio.ai` / `Cr3@t0rStud!o#2026`

## Prioritized Backlog

### P1 — Next Up
- Premium tier download quality differentiation
- A/B test hook text variations on public pages

### P2 — Future
- Character-driven auto-share prompts after creation
- Remix Variants on share pages
- Story Chain leaderboard
- Personalization and Precomputed Daily Packs
- Admin Dashboard WebSocket upgrades
