# Visionary Suite - PRD

## Original Problem Statement
Full-stack SaaS platform for creative content generation with monitoring, security, and admin analytics.

## LATEST UPDATE: 2026-03-12 — Session 14

### P0 Fix: Payment History Page — FIXED & TESTED
Fixed frontend field mappings to handle backend's snake_case response (`order_id`, `plan_name`, `created_at`). Page displays all transactions correctly.

### Task: 4 New SEO Blog Posts — COMPLETED & TESTED
Added 4 new SEO-optimized articles (Business Tips, Monetization, Design Tools, Content Creation). Total: 12 blog posts.

### Task: 4 Promotional Videos with Voice-Over — COMPLETED
Generated 4 AI promotional videos using Sora 2 + OpenAI TTS (onyx male voice) + ffmpeg merge:
1. Instagram Reel (12s, 2.3MB) - Hype/energetic, all features overview
2. Instagram Story (8s, 2.0MB) - Quick POV teaser
3. YouTube Shorts (12s, 3.5MB) - Feature showcase with detailed voiceover
4. Facebook Reel (12s, 2.2MB) - Before/after transformation theme
- Pipeline: Sora 2 (1280x720 landscape) → ffmpeg vertical convert (720x1280 with blurred bg) → TTS voice-over → merge
- Download page at `/app/promo-videos` with video previews, download buttons, share functionality
- Dashboard link added with "NEW" badge

## Architecture
- Backend: FastAPI + MongoDB + Cashfree PG + Emergent LLM (Gemini + Sora 2 + TTS)
- Frontend: React + Shadcn UI + Cashfree JS SDK
- Storage: Cloudflare R2 + local static/generated
- Queue: Redis workers
- Video: Sora 2 + OpenAI TTS + ffmpeg

## Known Issues
- SendGrid: requires plan upgrade (BLOCKED on user)
- Generated files 404 on production: fix ready, awaiting user deployment
- LLM key budget should be monitored (video generation uses more credits)

## Backlog
- P0: User must deploy generated file 404 fix to production
- P1: LLM timeout retry logic (tenacity) across all generation routes
- P1: Full system audit on production after deployment
- P2: Job queue architecture improvements
- P2: File storage cleanup policy (R2)
- P2: Monitoring & observability (Sentry/Prometheus)
