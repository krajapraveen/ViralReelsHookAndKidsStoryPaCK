# Visionary Suite — Product Requirements Document

## Original Problem Statement
Evolve the platform from a standard AI content generator into a highly addictive "Story Multiplayer Engine" built on viral network effects. PRODUCT REQUIREMENTS: Prioritize consumption, zero-friction entry, and strict behavioral psychology.

## Production Domain
- **Website**: https://www.visionary-suite.com

## Core Architecture
- **Frontend**: React (CRA) on port 3000
- **Backend**: FastAPI on port 8001
- **Database**: MongoDB
- **Storage**: Cloudflare R2 (via boto3 proxy)
- **Payments**: Cashfree
- **Auth**: JWT + Google OAuth (Emergent-managed)
- **AI**: OpenAI/Gemini/Sora via Emergent LLM Key
- **Email**: Resend (Emergent-managed, DNS verification pending)

## Key Modules (10 Creator Tools)
1. Story Video Studio (full pipeline)
2. Reel Generator
3. Story Generator
4. Character Consistency Studio
5. Coloring Book Wizard
6. Photo to Comic
7. GIF Maker / Reaction GIF
8. Comic Storybook Builder
9. Bedtime Story Builder
10. Story Episode Creator

## What's Been Implemented

### SEO & Google Indexing (April 2026)
- **Dynamic sitemap.xml** at `/api/public/sitemap.xml` — 125+ URLs covering static pages, blog posts, pipeline jobs, shares, series
- **robots.txt** at `/api/public/robots.txt` — Allow/Disallow rules, Sitemap directive pointing to production URL
- **Static robots.txt** backup in `frontend/public/robots.txt`
- **JSON-LD structured data** in `index.html` — WebSite, Organization, SoftwareApplication schemas
- **react-helmet-async** meta tags on Landing, Blog, Explore, Pricing pages with canonical URLs, OG tags
- **Fixed FRONTEND_URL** bug — sitemap now uses `www.visionary-suite.com` instead of preview URL
- **Removed duplicate `<title>` tag** from index.html

### Enterprise Protection Layer (Completed)
- Guardrail APIs (`/api/admin/guardrails/critical`) — credit drift, orphan deductions, data integrity
- 4 Kill Switches (Generation, Payments, Battle, Read-Only) with frontend 503 toast handling
- User Signals API (`/api/admin/user-signals`) — TTFV, funnel drop-offs, return behavior
- Draft Concurrency Race Condition fix (MongoDB Unique Partial Index)
- XSS sanitization (bleach + case-insensitive regex)
- R2 media proxy (`/api/media/r2/`)
- 7 strict funnel tracking events with server-side deduplication

### Story Multiplayer Engine
- Story battles, chains, continuations
- Explore feed with genre filtering
- Public creation pages with OG meta tags
- Creator profiles
- Series system

## Pending / Blocked
- **Resend Domain Verification** — BLOCKED on user DNS action
- **WebP/AVIF image optimization** (P1)
- **Push live traffic monitoring** (P0)

## Backlog
- (P2) Category-specific AI hook selection
- (P0.6) Auto-Recovery for FAILED_PERSISTENCE jobs
- (P2) Replace asyncio.create_task with Celery

## Key Endpoints
- `GET /api/public/sitemap.xml` — Dynamic XML sitemap
- `GET /api/public/robots.txt` — Crawler directives
- `GET /api/admin/guardrails/critical` — Money/data integrity
- `GET /api/admin/user-signals` — Product analytics
- `POST /api/admin/kill-switch/{id}` — Emergency disable
- `GET /api/media/r2/{key}` — Media proxy

## 3rd Party Integrations
- Cashfree (Payments) — User API Key required
- Cloudflare R2 (Storage) — Emergent managed
- Resend (Emails) — Emergent managed
- OpenAI/Gemini/Sora — Emergent LLM Key
- Google OAuth — User Client ID/Secret
- Google Analytics 4 (GA4) — G-X4Y9E4QSF8
- PostHog — Analytics
