# Visionary Suite — Product Requirements Document

## Original Problem Statement
Evolve the platform from a standard AI content generator into a highly addictive "Story Multiplayer Engine" built on viral network effects.

## Production Domain
- **Website**: https://www.visionary-suite.com

## Architecture
- Frontend: React (CRA) on port 3000
- Backend: FastAPI on port 8001
- Database: MongoDB
- Storage: Cloudflare R2 (via boto3 proxy)
- Payments: Cashfree
- Auth: JWT + Google OAuth
- AI: OpenAI/Gemini/Sora via Emergent LLM Key

## What's Been Implemented

### Phase 1: Universal Responsive Framework (April 2026)
- Created `/src/styles/responsive.css` — 15-module design system
- Created `/src/components/PageHeader.jsx` — universal responsive header
- Fluid typography with clamp() for hero/h1/h2/body
- iOS safe area handling (notch, Dynamic Island, gesture bar)
- Touch targets min 44x44px on coarse pointer devices
- Viewport-safe modals on <768px
- Video player: object-contain + touch-action:manipulation
- Mobile header truncation, compact padding
- Tab bars with horizontal scroll + scrollbar-hide
- iOS input zoom prevention (16px font)
- Support dock hidden during generation/preview
- Tour/tooltip viewport-bounded positioning
- Desktop frozen baseline — zero regressions

### Social Proof & Reviews (April 2026)
- Homepage counters (645+ Creations, 39+ Creators, 1.2K+ Scenes)
- Review wall with real user reviews
- Post-value review modal

### Landing CTR Optimization (April 2026)
- A/B Round 2 with 3 variants
- Variant-specific CTA text

### Admin Panel Trust Recovery (April 2026)
- Date range sync, polling propagation, freshness badges
- User Management duplicate route fix

### SEO (April 2026)
- Dynamic sitemap.xml (125+ URLs), robots.txt, JSON-LD

## Priority Tasks
1. Deploy all fixes to production
2. Monitor A/B CTR after 500 sessions
3. Phase 2: Premium Landing Page Rebuild
4. Phase 3: Growth Flywheel Features

## Backlog
- WebP/AVIF image optimization
- Auto-Recovery for FAILED_PERSISTENCE jobs
- Replace asyncio.create_task with Celery
- Resend Domain Verification (DNS pending)
