# Visionary Suite — Product Requirements Document

## Original Problem Statement
Evolve the platform from a standard AI content generator into a highly addictive "Story Multiplayer Engine" built on viral network effects. Prioritize consumption, zero-friction entry, and strict behavioral psychology.

## Production Domain
- **Website**: https://www.visionary-suite.com

## Core Architecture
- Frontend: React (CRA) on port 3000
- Backend: FastAPI on port 8001
- Database: MongoDB
- Storage: Cloudflare R2 (via boto3 proxy)
- Payments: Cashfree
- Auth: JWT + Google OAuth (Emergent-managed)
- AI: OpenAI/Gemini/Sora via Emergent LLM Key
- Email: Resend (Emergent-managed, DNS pending)

## What's Been Implemented

### Mobile P0 Rescue Sprint (April 2026)
- Fixed GlobalUserBar — compact on mobile, no header collision
- Fixed Profile page — credits hidden on mobile, tabs shortened with scroll
- Fixed Studio header — subtitle hidden, title truncated, right-padding for bar
- Fixed StoryPreview header — truncation, mobile padding
- Fixed Support dock — hidden during generation/preview pages
- Fixed Tour tooltip — viewport-bounded positioning
- Fixed Video player — object-contain, touch-action:manipulation
- Global CSS — max-width:100% on all img/video, mobile header truncation

### Social Proof & Reviews (April 2026)
- Homepage counter coherence fix (3 distinct metrics)
- Review wall with real user reviews + avg rating
- Post-value review modal (triggers after 3rd dashboard visit)
- Review submission/moderation API

### Landing CTR Optimization (April 2026)
- A/B Round 2 with 3 variants (Direct Value, Zero Friction, Social Proof)
- Variant-specific CTA text
- Updated trust line with real metrics

### Admin Panel Trust Recovery (April 2026)
- Date range sync across all sections
- Polling propagation to Growth tab
- LIVE/DELAYED/STALE freshness badges
- User Management duplicate route fix

### SEO & Google Indexing (April 2026)
- Dynamic sitemap.xml (125+ URLs), robots.txt, JSON-LD structured data
- GSC: Sitemap accepted (33 pages discovered), homepage indexed

### Enterprise Protection Layer
- Guardrails, Kill Switches, User Signals, XSS sanitization, R2 proxy

## Current Business Metrics (30-day)
| Metric | Value |
|--------|-------|
| Landing Visits | 839 |
| CTA Clicks | 11 (1.3% CTR) |
| Stories Created | 6 |
| Shares | 38 |
| Continuation Rate | 19.2% |

## Priority Tasks
1. Deploy full bundle to production
2. Monitor A/B CTR after 500 sessions — target 4%+
3. Continue mobile QA across all pages
4. Push traffic aggressively

## Backlog
- (P1) WebP/AVIF image optimization
- (P2) Category-specific AI hook selection
- (P0.6) Auto-Recovery for FAILED_PERSISTENCE jobs
- (P2) Replace asyncio.create_task with Celery
- Resend Domain Verification (blocked on DNS)
