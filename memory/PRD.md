# Visionary-Suite — Product Requirements Document

## Original Problem Statement
AI content generation platform (story videos, comics, GIFs, reels). Users create content using AI and monetize through credits/subscriptions.

## Core Architecture
```
/app/
├── backend/  (FastAPI + MongoDB + Redis)
│   ├── routes/         (API endpoints)
│   ├── services/       (Business logic incl. pipeline, fallback, R2)
│   ├── utils/          (R2 presign, payment monitoring)
│   └── scripts/        (Seeding, migrations)
└── frontend/ (React + TailwindCSS + Shadcn)
    └── src/
        ├── components/  (ProgressiveGeneration, BrowserVideoExport, WaitingExperience, Testimonials)
        ├── context/     (CreditContext global state)
        ├── hooks/       (useJobWebSocket, useWebSocketProgress)
        └── pages/       (StoryPreview, StoryVideoPipeline, StoryVideoStudio, Gallery, Landing, Dashboard)
```

## Architecture Philosophy
**Progressive Delivery** — Server generates story + images + voices. User sees value incrementally. Browser handles final video assembly. Server FFmpeg is kept as admin-only fallback.

**3-Tier Output Model:**
1. **Instant**: Playable web preview (free, no render needed)
2. **Standard**: Story Pack ZIP (images, audio, text, manifest)
3. **Premium**: Final MP4 export (browser-rendered via ffmpeg.wasm)

## Implemented Features

### Phase 1 — Core Platform
- [x] User auth (JWT + Google OAuth)
- [x] Story → Video pipeline (scenes, images, voices, render)
- [x] Comic Storybook Builder, GIF/Reel generators
- [x] Credit system + ledger
- [x] Gallery with 30 showcase items
- [x] Admin panel with full analytics (parallel queries)

### Phase 2 — Growth & Monetization
- [x] Priority queue system (Admin > Paid > Free)
- [x] Global CreditContext (React Context API)
- [x] Real-time WebSocket progress updates
- [x] Video watermarking (free users)
- [x] Social sharing + OpenGraph tags
- [x] Landing page conversion optimization + Testimonials
- [x] Cashfree payments with Geo-IP (INR/USD)

### Phase 3 — Fallback Output System (Mar 2026)
- [x] Lightweight server fallback MP4 (640x360, veryfast encode)
- [x] Story Pack ZIP (all scene images, audio, text, manifest.json)
- [x] Public preview page `/app/story-preview/:jobId`
- [x] R2 direct asset links with presigned URLs
- [x] Notify when ready — notification subscription flow
- [x] Manual fallback trigger API
- [x] Pipeline auto-triggers fallback on render/upload failure

### Phase 4 — Progressive Delivery + Client-Side Export (Mar 2026)
- [x] **Per-asset WebSocket events**: `scene_ready`, `image_ready`, `voice_ready`, `preview_ready`
- [x] **ProgressiveGeneration component**: Live scene cards, streaming images/voices, stage pipeline indicator
- [x] **Web Preview Player**: Browser-based slideshow with synced audio playback
- [x] **BrowserVideoExport**: ffmpeg.wasm browser-side MP4 rendering (720p, 15fps)
- [x] **3-tier output model on StoryPreview page**: Instant Preview, Export MP4, Story Pack ZIP
- [x] **useJobWebSocket hook**: WebSocket connection with ping/pong and auto-reconnect
- [x] **Graceful fallback**: Unsupported browsers get Story Pack + Preview instead of broken export
- [x] **Server FFmpeg preserved as admin-only fallback**

## Key API Endpoints
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | /api/pipeline/preview/{job_id} | No | Public preview data with presigned URLs |
| GET | /api/pipeline/assets/{job_id} | Yes | Individual asset download links |
| POST | /api/pipeline/notify-when-ready/{job_id} | Yes | Subscribe for completion notification |
| POST | /api/pipeline/generate-fallback/{job_id} | Yes | Manually trigger fallback generation |
| GET | /api/pipeline/status/{job_id} | Yes | Job status with fallback data |
| GET | /api/cashfree/products | No | Geo-IP aware pricing (INR/USD) |
| GET | /api/admin/analytics/dashboard | Yes | Admin analytics (parallel queries) |

## Key Database Schema
- `pipeline_jobs`: Includes `fallback_outputs`, `fallback_status`, `notify_on_complete`, `queue_priority`, `queue_tier`
- `users`, `orders`, `subscriptions`, `credit_ledger`, `trending_topics`, `notifications`

## Backlog

### P1 — Next Up
- [ ] Generate actual showcase video content (real AI-rendered videos for gallery)
- [ ] Complete Cashfree live payment flow testing with production keys
- [ ] Before/after benchmarks for time-to-first-visible-output

### P2
- [ ] Email notifications (blocked on SendGrid upgrade)
- [ ] Multi-language narration support
- [ ] Performance metrics dashboard (TTFD tracking)

### P3
- [ ] Custom voice cloning
- [ ] Advanced video templates
- [ ] A/B testing for landing page
- [ ] Deprecate server-side FFmpeg after browser export stability proven

## 3rd Party Integrations
- OpenAI (GPT-4o-mini, GPT Image 1, Sora 2, TTS)
- Gemini, Google Auth, Redis, Cloudflare R2
- Cashfree (Geo-IP ready), SendGrid (BLOCKED)
- FFmpeg (server fallback + ffmpeg.wasm browser export)

## Test Credentials
- Admin: admin@creatorstudio.ai / Cr3@t0rStud!o#2026
- Test user: test@visionary-suite.com / Test@2026#
