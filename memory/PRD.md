# Visionary Suite — Product Requirements Document

## Original Problem Statement
Build a full-stack AI creator suite with a viral growth engine. Convert the system from User → Create → Done into User → Create → Share → Viewer → Create → Share → Repeat. Every video must become a distribution channel.

## Core Architecture
- **Frontend**: React (port 3000)
- **Backend**: FastAPI (port 8001, all routes prefixed with /api)
- **Database**: MongoDB (via MONGO_URL env var)
- **Object Storage**: Cloudflare R2
- **Payments**: Cashfree (static webhook URL)
- **AI**: OpenAI (GPT-4o-mini, GPT Image 1, Sora 2, TTS), Gemini — via Emergent LLM Key
- **Auth**: Custom Google Identity Services (GIS) + JWT

## What's Been Implemented

### Core Platform (Complete)
- User auth (Google + email/password), Story Video Studio, Comic Storybook Creator, Coloring Book Generator, GIF Maker
- Credits system (50 initial credits, Cashfree payments), Gallery, sharing

### My Space — Real-Time Source of Truth (Complete — All 3 Phases)
- Phase 1: 3-section layout (In Progress / Completed / Failed), granular stage labels, auto-redirect, 4s polling
- Phase 2: Toast + browser notification on completion, share-link API, WhatsApp share, "Just Completed" badge
- Phase 3: Auto-download preference, post-completion prompt modal (Download / WhatsApp / Create Another), deduplication
- "Create Another" retention loop: 4 quick-create buttons (New story, Different style, Make it funny, Kids story)

### Growth Engine — Complete (April 6, 2026)

#### 1. Share Page — Video-First Growth Funnel
- Route: `/share/:shareId` — public, no auth
- Autoplay video (muted, looped) above the fold
- Social proof banner: "12,000+ videos created today" (computed from real data)
- Primary CTA: "Create Your Video — Free" (pulsing gradient animation)
- 1-Tap Remix: "Remix This Video" (calls fork API, preloads prompt/style)
- Value props: Made with AI / No editing needed / Free to start
- Urgency: "Takes less than 30 seconds. No credit card required."
- Bottom CTA repeats for scrollers
- Analytics tracking: share_viewed, cta_clicked, remix_clicked, whatsapp_shared

#### 2. First Video Free
- New users with 0 previous jobs get free generation (skip_credits=True)
- API: `GET /api/story-engine/first-video-free`

#### 3. Watermark System
- 2.5s branded end screen appended to all generated videos via ffmpeg
- Text: "Created with Visionary Suite" / "Make yours in seconds" / "visionary-suite.com"
- Called in pipeline before R2 upload, non-fatal (falls back to unwatermarked)

#### 4. Referral System
- `GET /api/referral/code` — generate referral link
- `GET /api/referral/stats` — referral count, earned credits, tier info
- `POST /api/referral/validate/{code}` — validate code
- `POST /api/referral/apply` — award credits to both parties
- Tiered system: bronze → silver → gold → platinum

#### 5. Analytics Tracking
- Events: share_viewed, cta_clicked, signup_from_share, first_video_created, remix_clicked, download_triggered, whatsapp_shared
- Funnel metrics: `GET /api/growth/funnel`
- Viral coefficient: `GET /api/growth/viral-coefficient`
- Loop dashboard: `GET /api/growth/loop-dashboard`

## The Growth Loop
```
Create → Complete → Share (WhatsApp/Link) → Viewer lands on Share Page
→ Watches video → Clicks CTA → Signs up → Gets 1 free video
→ Creates → Watermark drives more viewers → Shares → Repeat
```

## Key API Endpoints
| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/story-engine/create` | POST | Optional | Create video (first-video-free) |
| `/api/story-engine/user-jobs` | GET | JWT | All user jobs |
| `/api/story-engine/share-link/{job_id}` | POST | JWT | Generate share + WhatsApp URL |
| `/api/story-engine/first-video-free` | GET | Optional | Check eligibility |
| `/api/share/{shareId}` | GET | None | Share data with videoUrl |
| `/api/share/{shareId}/fork` | POST | None | Remix/fork story |
| `/api/referral/code` | GET | JWT | Get/create referral code |
| `/api/referral/stats` | GET | JWT | Referral statistics |
| `/api/growth/event` | POST | None | Track growth event |
| `/api/growth/funnel` | GET | None | Funnel conversion metrics |

## Credentials
- Test User: `test@visionary-suite.com` / `Test@2026#`
- Admin User: `admin@creatorstudio.ai` / `Cr3@t0rStud!o#2026`

## Prioritized Backlog

### P1 — Optimization
- Pipeline parallelization (script → voice + images in parallel)
- Publish Google OAuth consent screen (exit Testing mode)
- A/B test share page CTA variations

### P2 — Future
- Story Chain leaderboard
- Daily viral ideas & multi-platform share
- Admin Dashboard WebSocket upgrades
