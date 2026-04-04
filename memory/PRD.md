# AI Creator Suite — Product Requirements Document

## Original Problem Statement
Full-stack AI creator suite with tools for story/comic/GIF/video generation, character creation, brand kits, and social content. Credit-based monetization with Cashfree payments.

## Core Architecture
- **Frontend**: React (port 3000)
- **Backend**: FastAPI (port 8001)
- **Database**: MongoDB
- **AI**: OpenAI GPT-4o-mini, GPT Image 1, Sora 2, Gemini (via Emergent LLM Key)
- **Storage**: Cloudflare R2
- **Payments**: Cashfree
- **Auth**: Emergent-managed Google Auth + JWT

## Completed Features

### P0 — Safe Rewrite Engine (April 2026)
- Centralized rewrite engine at `backend/services/rewrite_engine/` with 200+ term mappings
- Replaced hard-blocking in 20+ files with safe_rewrite()
- Test result: 26/26 tests passed (iteration_423)

### P0 — Story Video Studio Crash Fix (April 2026)
- **Root cause**: `handleDownload` referenced at line 1967 but never defined in `PostGenPhase` component. Caused full-page React error boundary crash on production.
- **Fix**: Replaced naked `handleDownload` button with `EntitledDownloadButton` component (consistent with rest of page)
- **Hardening**: Added `safeAction()` utility wrapper that prevents any future undefined handler from crashing the page — logs to `/api/monitoring/client-error` instead
- **Error boundary improvement**: Now shows error classification, actual error message, retry/refresh/dashboard buttons
- **Files changed**: `frontend/src/pages/StoryVideoPipeline.js`, `backend/routes/monitoring.py`

### Previous Completions
- Production Metrics Dashboard
- Brand Kit Generator (stabilized)
- Photo-to-Reaction GIF (zero-friction single-screen UI, viral packs)
- Character Studio (backward-compatible, actionable CTAs)
- Growth Engine (compulsion loops, social proof)
- Cashfree Payment Integration, Credit System, Truth-based Admin Dashboard

## Current Mode: VALIDATION
- No new feature development
- Only fix production-breaking bugs backed by real usage data
- Drive real traffic to 100-200 jobs

## Frozen Backlog
- Auto captions for Reaction GIFs (P1)
- Multi-reaction pack generation (P1)
- Character DNA System (P1)
- Smart router, repair pipeline, GPU optimization (P2)
- Advanced analytics, Rewrite analytics dashboard (P2)

## Test Credentials
- Test User: `test@visionary-suite.com` / `Test@2026#`
- Admin User: `admin@creatorstudio.ai` / `Cr3@t0rStud!o#2026`
