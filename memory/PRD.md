# Visionary-Suite PRD

## Product Vision
**"Turn stories into cinematic videos using AI"**
Visionary Suite is an AI Story→Video platform. Users write a story and the AI generates scenes, creates images, adds voiceover, and renders a complete video in ~90 seconds.

## Architecture
- **Frontend**: React (CRA + craco) on port 3000
- **Backend**: FastAPI on port 8001
- **Database**: MongoDB (creatorstudio_production)
- **Storage**: Cloudflare R2
- **Payment**: Cashfree
- **LLM**: OpenAI GPT-4o-mini, GPT Image 1, OpenAI TTS, Sora 2, Gemini
- **Video**: ffmpeg (single-threaded, 640x360@10fps)

## Implemented Features

### Phase 1-4: Product Foundation ✅
- Marketing landing page, onboarding flow, dashboard UX, public gallery, share screen

### Phase 5: Growth, Monetization & Analytics ✅ (2026-03-13)
- Creator $9/mo (100 credits), Pro $19/mo (250 credits) subscription plans
- Credit top-ups: $5 (50), $12 (150), $30 (500)
- Remix This Video viral growth loop
- Rate limiting: 5 videos/hour, 1 concurrent
- Admin analytics funnel dashboard
- Upsell modal when credits < 10

### Phase 6: Landing Page V3 — Text-Only Redesign ✅ (2026-03-13)
- Removed all video/player elements from landing page
- Professional dark #06060b background with grid texture
- Gradient hero text (indigo → violet → amber)
- 6 feature showcase cards with icons (Write, Scene Gen, Image, Voice, Render, Speed)
- 6 animation style cards (2D Cartoon, Anime, 3D, Watercolor, Comic, Clay)
- Remix CTA section with "Browse Gallery" button
- Story prompt templates section
- Pricing overview with $9/$19 plans inline

### Phase 7: Gallery Optimization ✅ (2026-03-13)
- Category filters: All, 2D Cartoon, Watercolor, Anime, Comic Book, Claymation
- Sort options: Newest, Most Remixed, Trending
- Remix Leaderboard section (shows when remixed videos exist)
- Backend endpoints: /gallery/categories, /gallery/leaderboard
- Gallery sort/filter via query params: ?sort=most_remixed&category=cartoon_2d

### Phase 8: Social Sharing Optimization ✅ (2026-03-13)
- OpenGraph meta tags for gallery video sharing: /gallery/{job_id}/og
- Returns HTML with og:video, og:title, og:description, twitter:card
- Updated index.html meta tags for homepage

### Phase 9: Remix Leaderboard ✅ (2026-03-13)
- Most Remixed Videos leaderboard on Gallery page
- Ranked #1-#6 with gold/silver/bronze colors
- Shows remix count per video

### Phase 10: Performance Monitoring ✅ (2026-03-13)
- Admin Performance tab: queue depth, failure rate, avg/max render times, worker pool
- Alert system: queue > 5 (warning), failure > 10% (critical), render > 3min (warning)
- Auto-refresh mode (10s interval)
- Backend endpoint: GET /api/pipeline/performance

### Phase 6 Stress Testing ✅ (2026-03-13)
- 5 concurrent users: 5/5 signups, 5/5 videos, 0 failures
- 10 concurrent users: 10/10 logins, 4/10 videos (6 rate limited), 0 failures
- 20 concurrent users: 20/20 logins, 1/20 videos (19 rate limited), 0 failures
- Platform stable under all load levels

## Test Reports
| Iteration | Scope | Result |
|-----------|-------|--------|
| 157 | Phase 5: Growth/Monetization/Analytics | 100% (17/17 backend) |
| 158 | Phase 6-10: Landing V3/Gallery/OG/Perf | 100% (22/22 backend, 17 frontend) |

## Key Files
- `/app/frontend/src/pages/Landing.js` - Text-only feature showcase
- `/app/frontend/src/pages/Gallery.js` - Categories, sorting, leaderboard
- `/app/frontend/src/pages/Pricing.js` - $9/$19 subscription plans
- `/app/frontend/src/components/admin/PerformanceMonitorTab.js` - Perf monitor
- `/app/frontend/src/components/admin/GrowthFunnelTab.js` - Analytics funnel
- `/app/frontend/src/components/UpsellModal.js` - Upsell modal
- `/app/backend/routes/pipeline_routes.py` - Gallery/analytics/perf/OG endpoints
- `/app/backend/routes/credits.py` - Balance + upsell check
- `/app/backend/routes/cashfree_payments.py` - Products/plans
- `/app/backend/tests/stress_test.py` - Load testing script

## Backlog
- P1: SendGrid email (blocked on user upgrade)
- P2: Automatic video watermarking
- P2: WebSocket real-time progress (replace polling)
- P3: Worker auto-scaling
- P3: Email notifications on completion
- P3: Delete obsolete legacy code

## Test Credentials
- UAT: test@visionary-suite.com / Test@2026#
- Admin: admin@creatorstudio.ai / Cr3@t0rStud!o#2026
