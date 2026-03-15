# Visionary-Suite — Product Requirements Document

## Original Problem Statement
AI content generation platform (story videos, comics, GIFs, reels) with React frontend, FastAPI backend, MongoDB. Users create content using AI and monetize through credits/subscriptions.

## Core Architecture
```
/app/
├── backend/  (FastAPI + MongoDB + Redis)
│   ├── routes/         (API endpoints)
│   ├── services/       (Business logic)
│   ├── utils/          (Helpers)
│   └── scripts/        (Seeding, migrations)
└── frontend/ (React + TailwindCSS + Shadcn)
    └── src/
        ├── components/  (Reusable UI)
        ├── context/     (Global state)
        └── pages/       (Route pages)
```

## Implemented Features (Complete)

### Phase 1 — Core Platform
- [x] User auth (JWT + Google OAuth)
- [x] Story → Video pipeline (scenes, images, voices, render)
- [x] Comic Storybook Builder
- [x] GIF/Reel generators
- [x] Credit system + ledger
- [x] Gallery with 30 showcase items
- [x] Admin panel with full analytics

### Phase 2 — Growth & Monetization
- [x] Priority queue system (Admin > Paid > Free)
- [x] Global CreditContext (React Context API)
- [x] Real-time WebSocket progress updates
- [x] Video watermarking (free users)
- [x] Social sharing buttons + OpenGraph tags
- [x] Landing page conversion optimization
- [x] Testimonials section
- [x] Cashfree payments with Geo-IP (INR/USD)

### Phase 3 — Fallback Output System (Mar 2026)
- [x] **Lightweight fallback MP4** — Slideshow-style video (640x360, 10fps, veryfast encode)
- [x] **Story Pack ZIP** — All scene images, audio, text, manifest.json
- [x] **Preview page** — Public URL with scene-by-scene viewer + audio playback
- [x] **R2 direct asset links** — Presigned URLs for individual assets
- [x] **Notify when ready** — "Email me when done" subscription flow
- [x] **Manual fallback trigger** — API to regenerate fallback for old failed jobs
- [x] Pipeline auto-triggers fallback on render/upload failure
- [x] Frontend handles PARTIAL status → redirects to preview page
- [x] Gallery gracefully handles items without video URL

## API Endpoints — Fallback System
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | /api/pipeline/preview/{job_id} | No | Public preview data |
| GET | /api/pipeline/assets/{job_id} | Yes | Individual asset download links |
| POST | /api/pipeline/notify-when-ready/{job_id} | Yes | Subscribe for completion notification |
| POST | /api/pipeline/generate-fallback/{job_id} | Yes | Manually trigger fallback generation |

## Key Database Collections
- `pipeline_jobs`: Now includes `fallback_outputs`, `fallback_status`, `notify_on_complete`
- `users`, `orders`, `subscriptions`, `credit_ledger`, `trending_topics`, `notifications`

## Backlog

### P1 — Next Up
- [ ] Generate showcase video content (actual AI-rendered showcase videos)
- [ ] Complete Cashfree live payment flow testing (production keys)

### P2
- [ ] Email notifications for completed jobs (blocked on SendGrid upgrade)
- [ ] Multi-language narration support

### P3
- [ ] Custom voice cloning
- [ ] Advanced video templates
- [ ] A/B testing for landing page

## 3rd Party Integrations
- OpenAI (GPT-4o-mini, GPT Image 1, Sora 2, TTS)
- Gemini
- Google Auth (Emergent-managed)
- Redis
- Cloudflare R2
- Cashfree (Geo-IP ready)
- SendGrid (BLOCKED — user needs to upgrade plan)
- FFmpeg (system package)

## Test Credentials
- Admin: admin@creatorstudio.ai / Cr3@t0rStud!o#2026
- Test user: test@visionary-suite.com / Test@2026#
