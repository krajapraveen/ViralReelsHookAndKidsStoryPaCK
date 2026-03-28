# Story Universe Engine — PRD

## Original Problem Statement
Build a viral, addictive "Story Universe Engine" — a full-stack AI creator suite (React, FastAPI, MongoDB) with a compulsion-driven growth engine. The platform enables users to create AI-powered story videos, comics, and more, with a focus on continuation and social proof to drive engagement.

## User Personas
- **Creators**: Users who create and continue stories, driving content generation.
- **Viewers**: Users who discover stories via shared links and are pulled into the creation loop.
- **Admins**: Platform operators who monitor health, content, users, revenue, and jobs.

## Core Requirements
1. **Story-First UI**: Stories dominate the dashboard. Tools are secondary.
2. **Continuation > Creation**: All CTAs and copy emphasize continuing existing stories over creating new ones.
3. **Trust-Based Systems**: All user-facing data must reflect real database state. No synthetic or mocked data.
4. **Credit System**: 50 credits for new normal users. Strict credit deduction for all generation tools.
5. **Admin Control Center**: Professional persistent sidebar for all admin workflows.
6. **Growth Engine**: Compulsion loops via public pages, 1-click continue, open-loop story endings.

## Tech Stack
- Frontend: React + Tailwind CSS + Shadcn/UI
- Backend: FastAPI (Python)
- Database: MongoDB + Redis
- Storage: Cloudflare R2
- Payments: Cashfree
- AI: OpenAI (GPT-4o-mini, GPT Image 1, Sora 2, TTS), Gemini 3 (via Emergent LLM Key)
- Auth: Emergent-managed Google Auth + JWT

## Architecture
```
/app/
├── backend/
│   ├── routes/ (admin_metrics, auth, public_routes, story_series, story_video_studio, media_proxy, engagement)
│   ├── services/ (story_engine, anti_abuse_service)
│   └── server.py
├── frontend/
│   └── src/
│       ├── components/ (AdminLayout.js, ui/)
│       ├── pages/ (Dashboard, AdminDashboard, Admin/, PublicCharacterPage, PublicCreation, etc.)
│       ├── contexts/ (CreditContext)
│       └── App.js
```

## What's Been Implemented

### P0 — Admin Sidebar Navigation (DONE — Feb 28, 2026)
- Persistent sidebar wrapping ALL `/app/admin/*` routes via `AdminLayout.js` with `<Outlet />`
- 8 nav groups: Overview, Users, Content Engine, Jobs & Pipelines, Revenue & Credits, Analytics, System Health, Security
- Admin-only JWT role guard (redirects non-admin to /app)
- Active state highlighting, expand/collapse groups
- Mobile hamburger menu with overlay
- Logout pinned at bottom, "Back to App" link
- Removed ALL duplicate inline "Back to Admin" nav from 20+ admin pages
- Slim toolbar in AdminDashboard (Executive Dashboard title, polling/ws status, date range, refresh)
- Direct URL entry preserves sidebar and route
- Tests: iteration_356.json (12/12 PASS), iteration_357.json (12/12 PASS)

### P1 — Homepage Copy & CTA Upgrade (DONE — Feb 28, 2026)
- Hero: "Watch & Continue" as primary CTA, "Create New" as secondary
- Fallback hero: "Every Story is Waiting for You" with continuation copy
- Create bar: "What happens next? Continue any story or start fresh..." with white "Go" button
- Row titles: "Trending Now", "Unfinished Worlds" (was Fresh Stories), "Continue Watching" (was Watch Now)
- Card CTAs: "See what happens >" for real stories, "Continue this >" for seed cards
- Seed card badges: "UNFINISHED" (was "CREATE")
- Quick tools: Made ultra-subtle (20% opacity, smaller text)
- Tests: iteration_357.json (12/12 PASS)

### Earlier Completed Work
- Cloudflare R2 proxy with HTTP 206 byte-range streaming
- FFmpeg faststart for web video playback
- Dashboard conditional rendering fix (no more dead space)
- Compulsion Engine: Public page redesign, 1-click continue, open-loop endings
- Monetization: Cashfree payments, strict credit checks, 50-credit allocation
- Social Proof: Momentum-based messaging, Character Power Score
- Trust Fixes: Security tab, truth-based admin metrics, diverse live activity feed

## Prioritized Backlog

### P1 — Next
- A/B test hook text variations on story cards
- Character-driven auto-share prompts after creation (viral loop boost)
- Refine user dashboard feature/tool cards (ensure tools stay secondary)

### P2 — Future
- Remix Variants on share pages
- Self-Hosted GPU Models (Wan2.1, Kokoro)
- WebSockets for live admin job tracking
- Story-first hierarchy reinforcement (ongoing)
- Style preset preview thumbnails

### P3 — Backlog
- Story Chain leaderboard for gamified continuations
- SendGrid email fix (blocked on valid API key)
- General UI polish

## Key DB Schema
- `users`: Profile, role, credits
- `orders`: Cashfree payment records
- `story_engine_jobs`: Story outputs, pipeline state
- `feedback`, `ratings`: User feedback
- `credit_transactions`: Credit ledger

## Credentials
- Admin: admin@creatorstudio.ai / Cr3@t0rStud!o#2026
- Test User: test@visionary-suite.com / Test@2026#
