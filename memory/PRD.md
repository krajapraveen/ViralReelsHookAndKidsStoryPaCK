# Photo to Comic — AI Creator Suite PRD

## Original Problem Statement
Build a "Smart Repair Pipeline" for an AI creator suite (Photo to Comic). Highest priority: Failure Masking — users must NEVER see raw failures. If generation fails completely, deterministic fallback filter (Guaranteed Output) ensures the user always gets a comic.

## Current Status: PRODUCTION OBSERVATION PHASE
- Development is STRICTLY FROZEN
- No new features, no polish, no refactoring
- Only critical production-breaking bugs allowed
- Awaiting real production traffic data

## What's Been Implemented
- Phase 1 & 2 Pipelines fully tested (190+ pytest tests)
- Real cross-panel continuity wired (approved panels fed to LLM as context)
- Multi-tier fallback system ending in deterministic guaranteed_output.py (Pillow-based)
- Frontend scrubbed of all failure dead-end UI states
- Guaranteed Output fix: IMPLEMENTED, PENDING PRODUCTION VERIFICATION (zero real traffic so far)

## Production Observation Metrics (To Monitor When Traffic Arrives)
1. Guaranteed output rate
2. Fallback tier usage rate
3. Repair success rate
4. Dead-end screen rate (must be 0%)
5. Comic completion success rate
6. Latency by tier
7. User retry rate after output
8. Download/share/open rates
9. Credits charged vs credits waived
10. Low-quality output frequency

## P0 Bug Criteria (Only These Warrant Code Changes)
- Users reaching dead-end states
- Users charged without usable output
- Pipeline hanging/stuck jobs
- Widespread low-quality deterministic fallback
- Broken downloads/shares
- Severe latency causing abandonment
- Repair/fallback loop failures

## Frozen/Paused Tasks (DO NOT START)
- Admin routing config editor
- Smart Repair self-tuning router
- Dynamic style popularity badges ("Trending Now")
- Photo to Comic: Instagram export, WhatsApp share card, GIF teasers
- Bedtime Stories (TTS, Image Gen)

## Architecture
- Backend: FastAPI + MongoDB
- Frontend: React
- Pipeline: /app/backend/services/comic_pipeline/
- Key files: guaranteed_output.py, panel_orchestrator.py, job_orchestrator.py, continuity_pack.py
- Routes: /app/backend/routes/photo_to_comic.py
- Frontend: /app/frontend/src/pages/PhotoToComic.js

## 3rd Party Integrations
- OpenAI & Gemini (Emergent LLM Key)
- Cloudflare R2 (Object Storage)
- Cashfree (Payments)

## Test Credentials
- Test User: test@visionary-suite.com / Test@2026#
- Admin User: admin@creatorstudio.ai / Cr3@t0rStud!o#2026

## Last Data Report: Feb 2026
- Total jobs: 0 (no production traffic yet)
- No P0 issues — no data to reveal them
- Correct move: deploy, drive traffic, watch
