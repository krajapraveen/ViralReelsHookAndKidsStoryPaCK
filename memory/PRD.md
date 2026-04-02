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
- **P1**: PDF export, StylePreviewStrip (8 clickable styles), ComicDownloads (PDF readiness states), event tracking (8 events)
- **P1.5-A Failure Masking**: 3-attempt retry per panel, single-panel repair, READY_WITH_WARNINGS status, calm UI copy
- **P1.5-B Photo Quality Scoring**: OpenCV YuNet face detection, blur/brightness analysis, 4-check system, cached results
- **P1.5-C Character Consistency Validator**: SFace embeddings, source→panel + panel1→panelN validation, tiered thresholds, max 1 retry, drift logging
- **P1.5-D Observability Dashboard**: Admin Comic Health tab — job success rate, retry rate, gen time, consistency drift by style, quality breakdown, PDF success, conversion funnel, alerts
- **P0 CRITICAL FIX (2026-04-02)**: Complete failure masking overhaul
  - Removed ALL scary language ("Panel X Failed", "Generation unsuccessful", "Generation Failed", red X icons, error toasts)
  - Full failure → clean recovery card ("Let's try a different approach") instead of empty panel grid
  - Failed panels show "Being optimized" with Sparkles icon (not red X)
  - Job-level fallback pipeline: when >50% panels fail, sequential fallback with simplified prompts
  - No error toast on FAILED status — recovery UI handles everything
  - STATUS_CONFIG FAILED → "Processing Complete" (not scary text)

### Other Features (Intact)
- Bedtime Story Builder (PAUSED for validation)
- Growth Engine, Trust & Admin, Monetization — all working

## Prioritized Backlog

### VALIDATION PHASE (Current)
- Monitor real-user data via Comic Health dashboard
- Tune consistency thresholds from real drift data
- Test edge cases: dark selfies, blurry photos, sunglasses, side faces, multiple people

### P2 (After Validation)
- Dynamic style popularity badges
- Instagram 4:5 export, WhatsApp share card, GIF teaser
- A/B test hook text, auto-share prompts, Remix Variants

### P3
- Real TTS/Image/Video pipeline for Bedtime Stories

## Key Files
- `/app/backend/routes/photo_to_comic.py` — All Photo to Comic logic including fallback pipeline
- `/app/backend/services/photo_quality.py` — OpenCV YuNet quality scoring
- `/app/backend/services/consistency_validator.py` — SFace consistency validation
- `/app/backend/routes/admin_metrics.py` — Comic Health endpoint
- `/app/frontend/src/pages/PhotoToComic.js` — Main page with failure masking
- `/app/frontend/src/pages/AdminDashboard.js` — Admin with Comic Health tab
- `/app/frontend/src/components/photo-to-comic/StylePreviewStrip.jsx`
- `/app/frontend/src/components/photo-to-comic/ComicDownloads.jsx`

## Test Credentials
- Test User: test@visionary-suite.com / Test@2026#
- Admin User: admin@creatorstudio.ai / Cr3@t0rStud!o#2026
