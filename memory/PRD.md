# AI Creator Suite — Product Requirements Document

## Original Problem Statement
Full-stack AI creator suite with tools for story/comic/GIF/video generation, character creation, brand kits, and social content. The platform uses a credit-based monetization model with Cashfree payments.

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
- **Centralized rewrite engine** at `backend/services/rewrite_engine/`
  - `rule_rewriter.py`: 200+ term mappings (brands, franchises, characters, celebrities, platforms)
  - `rewrite_service.py`: Orchestrator — detect, rewrite, continue. Never blocks.
- **Replaced hard-blocking in 20+ files**: All `BLOCKED_KEYWORDS`, `check_copyright`, `check_copyright_violation`, `screen_safety` functions updated to use safe_rewrite()
- **Preserved harmful content blocking**: nsfw, violence, gore, explicit still blocked
- **Preserved negative prompts**: Image generation still includes copyright safety in negative prompts
- **Test result**: 26/26 tests passed (iteration_423)

### P0 — Story Video Studio Dead-End Fix (April 2026)
- **Replaced generic dead-end error boundary** with actionable error handling:
  - Shows error classification (data error, network error, cache error, render error)
  - Shows actual error message for debugging
  - Retry button (up to 3 attempts), Refresh Page, Go to Dashboard options
  - Cache clear suggestion after repeated failures
- **Added client error logging**: `POST /api/monitoring/client-error` captures frontend crashes with stack traces
- **Added safe_rewrite to story-engine/create**: Trademarked terms in story text/title rewritten before job creation
- **Added rewrite_note to response**: Frontend shows soft toast notification when terms are sanitized
- **Root cause on production**: Likely stale JS chunk cache or deployment gap (preview works perfectly)

### Previous Completions
- Production Metrics Dashboard
- Brand Kit Generator (stabilized)
- Photo-to-Reaction GIF (zero-friction single-screen UI, viral packs)
- Character Studio (backward-compatible, actionable CTAs)
- Growth Engine (compulsion loops, social proof)
- Cashfree Payment Integration
- Credit System (50 credits standard)
- Truth-based Admin Dashboard

## Current Mode: VALIDATION
- No new feature development
- Only fix production-breaking bugs backed by real usage data
- Drive real traffic to 100-200 jobs
- Track rewrite frequency, missed terms, generation success rate

## Prioritized Backlog (ALL FROZEN)

### P1
- Auto captions for Reaction GIFs
- Multi-reaction pack generation
- Character DNA System

### P2
- Smart router, repair pipeline, GPU optimization
- Advanced analytics
- Rewrite analytics dashboard

## Test Credentials
- Test User: `test@visionary-suite.com` / `Test@2026#`
- Admin User: `admin@creatorstudio.ai` / `Cr3@t0rStud!o#2026`
