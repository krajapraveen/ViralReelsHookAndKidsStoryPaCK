# Visionary Suite — Product Requirements Document

## Original Problem Statement
Evolve the platform from a standard AI content generator into a highly addictive "Story Multiplayer Engine" built on viral network effects. Prioritize consumption, zero-friction entry, and strict behavioral psychology.

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
- **Email**: Resend (Emergent-managed, DNS pending)

## What's Been Implemented

### Landing CTR Optimization — A/B Round 2 (April 2026)
- **3 new hero variants** replacing weak Round 1 copy:
  - **A (Control)**: "Turn Any Story Into a Stunning AI Video" / CTA: "Create Free Video Now"
  - **B (Zero Friction)**: "Create Viral AI Videos in 60 Seconds" / CTA: "Try It Free — No Signup"
  - **C (Social Proof)**: "Kids Stories, Reels & Viral Videos — Instantly" / CTA: "Make My First Video"
- **Variant-specific CTA text** — each variant has its own high-conversion CTA
- **Updated trust line** — now includes real-time video count + "Ready in 60 seconds"
- **A/B system updated** — seed function now auto-updates variants, 3-way split via deterministic hash
- **Goal**: Raise landing CTR from 1.3% → 4%+

### Admin Panel Trust Recovery (April 2026)
- **Fixed date range disconnection** — Growth tab syncs with parent Executive Dashboard
- **Fixed polling propagation** — parent refresh signal triggers Growth re-fetch
- **Added LIVE/DELAYED/STALE freshness badges** on all admin widgets
- **All 18 admin APIs verified 200**, all 16 routes render, zero mock data

### SEO & Google Indexing (April 2026)
- Dynamic sitemap.xml (125+ URLs), robots.txt, JSON-LD structured data
- GSC: Sitemap accepted (33 pages discovered), homepage indexed

### Enterprise Protection Layer
- Guardrails, Kill Switches, User Signals, XSS sanitization, R2 proxy

## Current Business Metrics (30-day)
| Metric | Value | Status |
|--------|-------|--------|
| Landing Visits | 839 | Tracking |
| CTA Clicks | 11 | 1.3% CTR — needs 4%+ |
| Stories Created | 6 | Low volume |
| Stories Shared | 38 | High share rate |
| Share Opens | 78 | Good engagement |
| Continuations | 15 | 19.2% cont. rate |

## Priority Tasks
1. (P0) Deploy Round 2 A/B + admin fixes to production
2. (P0) Monitor A/B headline test — target 4%+ CTR
3. (P0) Above-the-fold rebuild — autoplay demo, before/after, 1-click CTA
4. (P0) Audit first-click path friction — minimize clicks to generation

## Backlog
- (P1) WebP/AVIF image optimization
- (P2) Category-specific AI hook selection
- (P0.6) Auto-Recovery for FAILED_PERSISTENCE jobs
- (P2) Replace asyncio.create_task with Celery
- Resend Domain Verification (blocked on DNS)
