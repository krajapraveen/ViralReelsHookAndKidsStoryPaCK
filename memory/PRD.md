# Visionary Suite — Product Requirements Document

## Original Problem Statement
Build a full-stack AI creator suite with a "compulsion-driven" growth engine. Key products include Photo to Comic, Bedtime Story Builder, Story Video Studio, and Character Creator. The platform uses credit-based monetization with Cashfree payments, Emergent-managed Google Auth, and truth-based admin dashboards.

## Core Architecture
- **Frontend**: React 18 + Tailwind CSS + Shadcn UI
- **Backend**: FastAPI + MongoDB + Redis
- **AI**: OpenAI (GPT-4o-mini, GPT Image 1, Sora 2, TTS) + Gemini via Emergent LLM Key
- **Storage**: Cloudflare R2
- **Payments**: Cashfree
- **Auth**: Emergent-managed Google OAuth + JWT
- **CV**: OpenCV (FaceDetectorYN/YuNet + FaceRecognizerSF/SFace) + Pillow

## What's Been Implemented

### Photo to Comic — Feature-Complete for Validation
- **P0**: Parallel panel generation, real progress stages, smart story presets, output bundle, dynamic ETA
- **P1**: PDF export (FPDF), character consistency engine foundation, StylePreviewStrip (8 clickable styles), ComicDownloads (PDF readiness states), event tracking (8 events → comic_events + GA4)
- **P1.5-A Failure Masking**: 3-attempt retry strategy per panel (primary → retry → fallback model), single-panel post-gen repair, READY_WITH_WARNINGS status, all user-facing copy is calm
- **P1.5-B Photo Quality Scoring**: OpenCV FaceDetectorYN (YuNet), Laplacian blur, brightness histogram, 4-check system (Face/Clarity/Lighting/Framing), hard block on no-face, cached per image hash
- **P1.5-C Character Consistency Validator**: OpenCV FaceRecognizerSF (SFace), source→panel (primary) + panel1→panelN (secondary) validation, tiered thresholds (accept/borderline/retry), no-face panel handling, max 1 auto-retry per panel, rich drift logging to consistency_logs
- **P1.5-D Observability Dashboard**: Admin Comic Health section with job success rate, retry rate, avg gen time, consistency drift by style, quality check breakdown, PDF success rate, conversion funnel, critical alerts

### Bedtime Story Builder (PAUSED — validation phase)
- P0 Complete, analytics tracking, false toast bug fixed

### Growth Engine, Trust & Admin, Monetization
- All previously completed features intact

## Prioritized Backlog

### VALIDATION PHASE (Current)
- No new features. Monitor real-user data via Comic Health dashboard.
- Tune consistency thresholds from real drift data.
- Hold P2 until validation data confirms stability.

### P2 (After Validation)
- Dynamic style popularity badges (from real comic_events data)
- Instagram 4:5 export, WhatsApp share card, GIF teaser
- A/B test hook text, auto-share prompts, Remix Variants
- Admin dashboard WebSocket upgrade
- "Story Chain" leaderboard

### P3
- Real TTS/Image/Video pipeline for Bedtime Stories

## Key DB Collections
- `photo_to_comic_jobs` — generation jobs with panels, consistency metadata
- `comic_events` — analytics (style clicks, downloads, conversions)
- `consistency_logs` — per-job drift data (similarity scores, retries, no-face rates, by style)
- `quality_cache` — cached photo quality results by image hash
- `users`, `orders`, `feedback`, `ratings`, `jobs`, `credit_transactions`

## Key Files
- `/app/backend/routes/photo_to_comic.py` — All Photo to Comic logic
- `/app/backend/services/photo_quality.py` — OpenCV YuNet quality scoring
- `/app/backend/services/consistency_validator.py` — SFace consistency validation
- `/app/backend/routes/admin_metrics.py` — Comic Health endpoint
- `/app/frontend/src/pages/PhotoToComic.js` — Main page
- `/app/frontend/src/pages/AdminDashboard.js` — Admin with Comic Health tab
- `/app/frontend/src/components/photo-to-comic/StylePreviewStrip.jsx`
- `/app/frontend/src/components/photo-to-comic/ComicDownloads.jsx`

## Test Credentials
- Test User: test@visionary-suite.com / Test@2026#
- Admin User: admin@creatorstudio.ai / Cr3@t0rStud!o#2026
