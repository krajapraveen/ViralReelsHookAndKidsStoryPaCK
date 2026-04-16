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

## What's Been Implemented

### Admin Panel Trust Recovery (April 2026)
- **Fixed date range disconnection** — Growth tab now syncs with parent Executive Dashboard's date selector
- **Fixed polling propagation** — Parent polling signal now triggers Growth tab refresh
- **Added freshness badges** — LIVE/DELAYED/STALE indicators on all admin widgets
- **Root cause**: Dashboard was showing real data, but UX defaulted to 3-day window on a low-traffic site, making everything look dead
- **Verified**: All 18 admin APIs return 200, all 16 admin routes render, all metrics are real production data

### SEO & Google Indexing (April 2026)
- **Dynamic sitemap.xml** at `/api/public/sitemap.xml` — 125+ URLs with hardcoded production domain
- **robots.txt** at `/api/public/robots.txt` — Allow/Disallow rules, sitemap exception
- **JSON-LD structured data** — WebSite, Organization, SoftwareApplication schemas
- **react-helmet-async** meta tags on Landing, Blog, Explore, Pricing
- **GSC verified**: Sitemap accepted (33 pages discovered), homepage indexed, indexing requested for key pages

### Enterprise Protection Layer
- Guardrail APIs, 4 Kill Switches, User Signals API
- Draft Concurrency fix, XSS sanitization, R2 media proxy
- 7 strict funnel tracking events with server-side deduplication

## Pending / Blocked
- **Resend Domain Verification** — BLOCKED on user DNS action

## Backlog
- (P0) Push live traffic monitoring
- (P1) WebP/AVIF image optimization
- (P1) Optimize thresholds based on traffic data
- (P2) Category-specific AI hook selection
- (P0.6) Auto-Recovery for FAILED_PERSISTENCE jobs
- (P2) Replace asyncio.create_task with Celery
