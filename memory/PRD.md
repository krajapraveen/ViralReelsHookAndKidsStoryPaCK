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
- **CV**: OpenCV (FaceDetectorYN / YuNet) + Pillow for photo quality scoring

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
- **P1.5-A Complete (2026-04-02) — Failure Masking**:
  - 3-attempt retry strategy per panel: primary model → retry → fallback model
  - Single-panel post-generation repair (regenerate only failed panels, up to 2)
  - `READY_WITH_WARNINGS` status for retried-but-successful jobs
  - All user-facing copy is calm (no "failed", "error", "crashed")
  - PDF/script export failure never blocks PNG result
  - Status mapping: READY_WITH_WARNINGS → "Your comic is ready!", PARTIAL_READY → "Your comic is ready with X optimized panels", FAILED → "Let's Try Again"
- **P1.5-B Complete (2026-04-02) — Photo Quality Scoring**:
  - OpenCV FaceDetectorYN (YuNet) for face detection
  - Laplacian variance for blur detection
  - Brightness histogram analysis
  - 4-check system: Face, Clarity, Lighting, Framing
  - 3-tier quality: good / acceptable / poor
  - Hard block on no-face images
  - Warnings for multi-face, blurry, dark, small face
  - Quality results cached per image hash (24h TTL)
  - Frontend quality card with pass/warn/fail indicators
  - Generate button disabled when quality says can't proceed

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
- Truth-based admin dashboard (real data only)
- Fixed Profile → Security tab
- "Live on the Platform" feed with diverse, truthful location data

### Monetization
- Cashfree payments fully wired
- Strict credit checks on all generation paths

## Prioritized Backlog

### P1.5-C (Next)
- Character consistency validator (post-generation face embedding comparison, auto-retry low-similarity panels)

### P1.5-D
- Production observability dashboard (job success rate, retry rate, stage latency, refund rate)

### P2
- Instagram 4:5 export, WhatsApp share card, GIF teaser for Photo to Comic
- A/B test hook text variations on public pages
- Character-driven auto-share prompts after creation
- "Remix Variants" on share pages
- Admin dashboard WebSocket upgrade
- Style preset preview thumbnails
- "Story Chain" leaderboard
- Dynamic style popularity badges (based on real usage data)

### P3
- Real TTS, Image Generation, and Video Pipeline for Bedtime Stories (pending validation)

## Key DB Collections
- `users`, `orders`, `feedback`, `ratings`, `jobs`, `credit_transactions`
- `photo_to_comic_jobs` — generation jobs with stages, panels, consistency data
- `comic_events` — P1 analytics tracking (style clicks, downloads, conversions)
- `quality_cache` — cached photo quality results by image hash
- `user_assets` — permanent CDN-backed assets
- `bedtime_events` — bedtime story analytics

## Test Credentials
- Test User: test@visionary-suite.com / Test@2026#
- Admin User: admin@creatorstudio.ai / Cr3@t0rStud!o#2026

## Key Files
- `/app/backend/routes/photo_to_comic.py` — All Photo to Comic logic including PDF, events, consistency, quality check
- `/app/backend/services/photo_quality.py` — OpenCV YuNet face detection + Pillow quality scoring
- `/app/backend/models/face_detection_yunet.onnx` — YuNet DNN face detection model
- `/app/frontend/src/pages/PhotoToComic.js` — Main Photo to Comic page with quality check UI
- `/app/frontend/src/components/photo-to-comic/StylePreviewStrip.jsx` — Style preview strip
- `/app/frontend/src/components/photo-to-comic/ComicDownloads.jsx` — Downloads with PDF readiness
