# Story Universe Engine — Product Requirements Document

## Original Problem Statement
Build a "Story Universe Engine" — a full-stack AI creator suite with growth engine, monetization, and viral sharing.

## Core Architecture
- Frontend: React (CRA + Craco) on port 3000
- Backend: FastAPI on port 8001
- Database: MongoDB
- Storage: Cloudflare R2 (all media via same-origin streaming proxy)
- Payments: Cashfree
- AI: OpenAI GPT-4o-mini, Sora 2, TTS + Gemini 3 via Emergent LLM Key

## Media Delivery (Production-Grade — Mar 30 2026)

### 5-Layer Fix (ALL COMPLETE)
1. Data Pipeline: DB backfilled thumbnail_small_url. API enforces non-null.
2. Delivery Routing: ALL media via same-origin proxy /api/media/r2/{key}. Zero direct R2 CDN.
3. Protocol: Content-Type from R2 metadata (authoritative). nosniff safe. ETag, Content-Disposition.
4. Streaming: Videos streamed 64KB chunks. Range <2MB buffered. Surrogate-Control bypasses ingress.
5. Frontend Priority: Hero eager+opacity0.6. First 2 rows eager. First 6 cards loading="eager".

### Platform Constraints (K8s Ingress)
- Strips Content-Length from GET (HEAD preserves it)
- Overrides Cache-Control to no-store (Surrogate-Control survives)

## Auto-Run Video Bug Fix (Mar 30 2026)
- **Root cause**: StoryVideoPipeline.js auto-reconnected to ANY active job on page load, including stale/crashed jobs from previous sessions
- **Frontend fix**: Don't auto-reconnect to jobs >10 min old. Don't show jobs >15 min old in active banner.
- **Backend fix**: Added pipeline_jobs to stuck job recovery. Jobs stuck in PROCESSING >threshold marked as FAILED.

## Test Credentials
- Test User: test@visionary-suite.com / Test@2026#
- Admin User: admin@creatorstudio.ai / Cr3@t0rStud!o#2026
