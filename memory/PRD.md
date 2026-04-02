# Visionary Suite — Product Requirements Document

## Original Problem Statement
AI Creator Suite ("Growth Engine") with Photo to Comic as the primary conversion feature. Focus on compulsion-driven growth, monetization discipline, and pipeline resilience. Currently in **VALIDATION MODE** — no new features, only stability/reliability work.

## Core Products
1. **Photo to Comic** (Primary — Active Development)
2. **Bedtime Story Builder** (Paused for validation)

## Architecture
- **Frontend**: React (Vite) + Tailwind + Shadcn/UI
- **Backend**: FastAPI + MongoDB + Redis
- **Integrations**: OpenAI/Gemini (Emergent LLM Key), Cloudflare R2, Cashfree, Google Auth

## Credentials
- Test User: test@visionary-suite.com / Test@2026#
- Admin User: admin@creatorstudio.ai / Cr3@t0rStud!o#2026

---

## What's Been Implemented

### Photo to Comic — Complete Feature Set
- Interactive StylePreviewStrip (conversion lever)
- Gated PDF, PNG, script downloads (ComicDownloads)
- Pre-generation OpenCV/YuNet Photo Quality Scoring
- Post-generation Character Consistency Validator (face embeddings)
- Bulletproof Failure Masking (panel-level + job-level fallbacks)
- Admin "Comic Health" observability dashboard

### P0 Fallback Quality Validation (Apr 2, 2026) ✅
- **5 Validation Dimensions** baked into pipeline:
  1. `perceived_quality_score` (1-5) — Would user say "cool" or "broken"?
  2. `narrative_coherence` (1-5) — Story flow, sequential panels, gap detection
  3. `style_consistency_score` (0-1) — Panel-to-panel embedding similarity
  4. `fallback_latency_penalty_ms` — Extra time from retries/fallbacks
  5. `ui_emotional_safety` (PASS/FAIL) — Zero scary words in user-facing text
- **Admin Validation Test Runner**: Single panel failure + majority failure controlled tests
- **UI Safety Audit** endpoint: Scans 20 user-facing text strings for scary words
- **Admin Dashboard**: Validation Quality section + FallbackValidationRunner with test history
- **UI Text Cleanup**: Removed "Continue failed", "Assets could not be validated" — all calm copy

### Growth Loop & Monetization (Previous Sessions)
- Redesigned public pages with momentum-based social proof
- 1-click continue flow (generate before login)
- Cashfree payments fully wired
- 50-credit standard for all normal users
- Truth-based admin dashboard (no synthetic data)

---

## Current Status: VALIDATION MODE

### Completed Validations
- ✅ Single-panel failure injection → repair triggers → coherent output
- ✅ Majority failure (>50%) injection → job-level fallback triggers → degraded but usable
- ✅ UI Safety Audit: 20/20 texts pass, 0 scary words
- ✅ All 5 quality dimensions tracked and displayed on admin dashboard
- ✅ Edge-case inputs (blurry, dark, multi-face, tiny-face) handled correctly

---

## Upcoming Tasks
- (P1) A/B test hook text variations on public pages
- (P1) Character-driven auto-share prompts after creation

## Future/Backlog (P2 — DO NOT implement until validation complete)
- Dynamic style popularity badges ("Trending Now")
- Instagram 4:5 export, WhatsApp share card, GIF teaser
- Real TTS, Image Generation, Video Pipeline for Bedtime Stories
- "Remix Variants" on share pages
- Admin dashboard WebSocket upgrade
- "Story Chain" leaderboard

## Known Issues
- Minor F841 unused variables in photo_to_comic.py from rapid refactoring
- photo_to_comic.py is >2800 lines — needs splitting post-validation
