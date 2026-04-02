# Visionary Suite — Product Requirements Document

## Original Problem Statement
Build a full-stack AI creator suite with a "compulsion-driven" growth engine. Key products include Photo to Comic, Bedtime Story Builder, Story Video Studio, and Character Creator. The platform uses credit-based monetization with Cashfree payments, Emergent-managed Google Auth, and truth-based admin dashboards.

## Core Architecture
- **Frontend**: React 18 + Tailwind CSS + Shadcn UI
- **Backend**: FastAPI + MongoDB + Redis
- **AI**: OpenAI (GPT-4o-mini, GPT Image 1, Sora 2, TTS) + Gemini (gemini-2.0-flash, gemini-3-pro-image-preview) via Emergent LLM Key
- **Storage**: Cloudflare R2
- **Payments**: Cashfree
- **Auth**: Emergent-managed Google OAuth + JWT

## What's Been Implemented

### Photo to Comic (PRIMARY FOCUS)
- **P0 Complete**: Parallel panel generation (asyncio.gather), real backend-driven progress stages, smart story presets (8 presets), output bundle (PNG + TXT script), dynamic ETA
- **P1 Complete (2026-04-02)**:
  - PDF Comic Export via FPDF — cover page, 2x2 panel grid, script page, branding
  - Character Consistency Engine — stable seeds from photo/style hash, identity hash, style anchor prompts
  - StylePreviewStrip — 8 clickable style cards with visual highlight, horizontal scroll, mobile swipe
  - ComicDownloads — PDF readiness states (Preparing/Download/Unavailable), PNG download, script download, trust copy
  - Event tracking — 8 event types tracked to `comic_events` collection + GA4
  - Mobile-first validation — tested on 390px viewport

### Bedtime Story Builder (PAUSED — validation phase)
- P0 Complete: 1-screen UI, structured JSON generation, Web Speech API playback, Bedtime Mode, streak system
- Analytics: 6 event types tracked, admin metrics endpoint
- Bug fix: False "Generation Failed" toast resolved

### Growth Engine
- Redesigned public character/creation pages with momentum-based social proof
- 1-click continue flow (generation before login)
- Enforced credit deduction for all tools
- Consistent 50-credit allocation

### Trust & Admin
- Truth-based admin dashboard (real data only, "Not enough data" when insufficient)
- Fixed Profile → Security tab
- "Live on the Platform" feed with diverse, truthful location data

### Monetization
- Cashfree payments fully wired
- Strict credit checks on all generation paths
- Pro-rated charging for partial panel results

## Prioritized Backlog

### P1.5 (Next)
- Failure masking for Photo to Comic (silent retries + calm messaging)
- Photo quality scoring before generation

### P2
- Instagram 4:5 export, WhatsApp share card, GIF teaser for Photo to Comic
- A/B test hook text variations on public pages
- Character-driven auto-share prompts after creation
- "Remix Variants" on share pages
- Admin dashboard WebSocket upgrade
- Style preset preview thumbnails
- "Story Chain" leaderboard

### P3
- Real TTS, Image Generation, and Video Pipeline for Bedtime Stories (pending validation)

## Key DB Collections
- `users`, `orders`, `feedback`, `ratings`, `jobs`, `credit_transactions`
- `photo_to_comic_jobs` — generation jobs with stages, panels, consistency data
- `comic_events` — P1 analytics tracking (style clicks, downloads, conversions)
- `user_assets` — permanent CDN-backed assets
- `bedtime_events` — bedtime story analytics

## Test Credentials
- Test User: test@visionary-suite.com / Test@2026#
- Admin User: admin@creatorstudio.ai / Cr3@t0rStud!o#2026

## Key Files
- `/app/backend/routes/photo_to_comic.py` — All Photo to Comic logic including PDF, events, consistency
- `/app/frontend/src/pages/PhotoToComic.js` — Main Photo to Comic page
- `/app/frontend/src/components/photo-to-comic/StylePreviewStrip.jsx` — Style preview strip
- `/app/frontend/src/components/photo-to-comic/ComicDownloads.jsx` — Downloads with PDF readiness
