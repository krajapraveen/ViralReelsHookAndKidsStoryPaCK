# Visionary Suite — PRD (Product Requirements Document)

## Product Vision
Visionary Suite is an **AI Creative Operating System** — a creator network centered around the growth loop: **Create → Share → View → Remix → Create**.

## Core Architecture
- **Frontend**: React (CRA) + Tailwind CSS + Shadcn/UI
- **Backend**: FastAPI + MongoDB (Motor async)
- **Storage**: Cloudflare R2
- **AI**: OpenAI (GPT-4o-mini, GPT Image 1, Sora 2, TTS), Gemini, ElevenLabs
- **Auth**: JWT + Google Auth (Emergent-managed)
- **Payments**: Cashfree (geo-IP based)

## Flagship Feature
**Story → Video Pipeline**: User writes a prompt → AI generates script, scenes, images, voiceover → Complete video.

## Pipeline Architecture (Optimized)
```
User Prompt → API Gateway → Job Orchestrator → Queue (Priority) → Workers → Result Store
```
- **Parallel image gen**: asyncio.gather with semaphore (5 concurrent)
- **Parallel voice gen**: asyncio.gather with semaphore (6 concurrent)
- **Plan-based scene limits**: Free=3, Paid=4, Premium=6
- **Credit reservation**: Reserve → Finalize on success → Refund on failure
- **Scene caching**: SHA-256 hash of (prompt + style + scene_count) reuses scene structure
- **Priority queue**: Admin=0, Paid=1, Free=10 with anti-starvation
- **Browser-side export**: ffmpeg.wasm offloads rendering to client

## Plan-Based Controls
| Plan | Max Scenes | Queue Priority | Watermark |
|------|-----------|---------------|-----------|
| Free | 3 | Low (10) | Yes |
| Starter/Monthly | 4 | Medium (1) | No |
| Pro/Premium | 6 | Medium (1) | No |
| Admin/Demo | 6 | High (0) | No |

## Credit System
- Small (≤3 scenes): 10 credits
- Medium (4-6 scenes): 15 credits
- Large (7+ scenes): 20 credits
- **Reservation model**: Credits reserved at job start, finalized on completion, refunded on failure

## Distribution Loop (LIVE)
| Component | Status | Route |
|-----------|--------|-------|
| Public Creation Pages | LIVE | `/v/{slug}` |
| Explore Gallery | LIVE | `/explore` |
| Remix Button | LIVE | On every public page |
| Share Buttons (X, LinkedIn, Reddit, Copy) | LIVE | On every public page |
| Prompt Display for Remix | LIVE | On every public page |
| OG Meta Tags (share page) | LIVE | `/api/public/s/{slug}` |
| Dynamic OG Image | LIVE | `/api/public/og-image/{slug}` |
| Canonical URLs | LIVE | On every public page |
| Sitemap | LIVE | `/api/public/sitemap.xml` |
| Creator Profiles | LIVE | `/creator/{username}` |
| Content Seeding (40 Phase A) | DONE | 40 videos seeded |
| Admin Growth Dashboard | LIVE | `/app/admin/growth` |
| Watermark on exports | LIVE | Client-side |

## Completed Features (All Sessions)
### Session 1-2: Foundation
- Global design system, high-conversion homepage, simplified dashboard
- Story Video Pipeline (multi-stage, durable)
- Distribution loop (explore, public pages, remix, share)

### Session 3: Distribution Engine
- OG Meta Tags + Share Pages + Dynamic OG Images
- Social Share Buttons (X, LinkedIn, Reddit, Copy Link)
- Remix Prompt Display, Sitemap, Creator Profiles
- Admin Growth Dashboard (5 core metrics)
- Content Seeding Phase A (40 videos)

### Session 4: Pipeline Speed & Cost Control
- Plan-based scene limits (free=3, paid=4, premium=6)
- Credit reservation model (reserve → finalize → refund)
- Scene caching for prompt reuse (skips LLM call on cache hit)
- Better progress labels (Step X/3 format)
- Verified: images already parallelized (asyncio.gather)
- Verified: voices already parallelized (asyncio.gather)
- Verified: priority queue already implemented (Admin/Paid/Free)

## Performance Baseline (3-scene free job)
- Scene generation: ~7s
- Image generation (3 parallel): ~57s
- Voice generation (3 parallel): ~13s
- Total: ~79s
- Cache hit saves: ~7s (scene generation skipped)

## Remaining Backlog
### P0
- [ ] Content Seeding Phase B+C (80 more videos → 120 total)

### P1
- [ ] UX: Reduce friction to first creation (prompt before login)
- [ ] Time to First Creation metric tracking
- [ ] Better progress UX (show first generated asset immediately)

### P2
- [ ] BYO API / BYO Cloud mode (users provide own API keys)
- [ ] Creator Challenges (weekly engagement)
- [ ] Live Cashfree Payment Integration
- [ ] Email Notifications (BLOCKED — SendGrid)

## Technical Debt
- SendGrid integration blocked (external issue)
