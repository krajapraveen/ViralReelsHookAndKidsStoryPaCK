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

### Phase 1: Marketing Landing Page ✅ (2026-03-13)
- Hero: "Turn stories into cinematic videos using AI"
- 3-step How It Works, 6 clickable prompt templates
- Video Gallery with real AI-generated videos
- Secondary tools section (de-emphasized)
- Pricing overview (10/100/1000 credits)
- Simplified nav + mobile responsive

### Phase 2: Onboarding Flow ✅ (2026-03-13)
- Prompt templates on landing link to `/signup?prompt=...`
- Signup captures prompt via localStorage (`onboarding_prompt`)
- Post-signup redirects to Story→Video studio (not dashboard)
- Studio reads prompt from localStorage and pre-fills story text
- Welcome overlay: "Let's turn your story into a cinematic video"

### Phase 3: Dashboard UX ✅ (2026-03-13)
- Story→Video is hero card at top (indigo gradient, large)
- "More Creator Tools" label with secondary tools below
- Clean, focused layout

### Phase 4: Growth Features ✅ (2026-03-13)
- Public Gallery page at `/gallery` (no auth required)
- Share screen after video completion: Download, Copy Link
- Social sharing buttons: X, Facebook, WhatsApp, LinkedIn
- "Create Your Own" CTA throughout gallery

### Phase 5: Growth, Monetization & Analytics ✅ (2026-03-13)
#### Pricing & Subscriptions
- **Creator plan**: $9/mo — 100 credits, priority rendering
- **Pro plan**: $19/mo — 250 credits, no watermark, gallery featured
- **Credit top-ups**: $5 (50cr), $12 (150cr), $30 (500cr)
- Updated Cashfree PRODUCTS with new plan structure
- Full Pricing page at `/pricing` with Free/Creator/Pro tiers

#### Remix This Video (Viral Growth Loop)
- Gallery shows "Remix This Video" button on each video card
- Clicking stores parent video data (title, story, style) in localStorage
- Navigates to story studio with `?remix=true` query param
- Studio pre-fills all fields from remixed video
- Remix banner shown in input phase
- `parent_video_id` sent to backend, `remix_count` incremented on parent

#### Rate Limiting
- Max 5 videos per hour per user (429 on exceed)
- Max 1 concurrent job per user (429 on exceed)
- Implemented in `_check_rate_limit()` in pipeline_routes.py

#### Analytics Dashboard
- `GET /api/pipeline/analytics/funnel?days=N` — admin-only endpoint
- Returns: event counts, daily breakdown, total videos/completed/remixes/credits
- Growth Funnel tab added to Admin Dashboard
- Shows summary cards + funnel visualization + daily activity table

#### Upsell Mechanism
- `GET /api/credits/check-upsell` — returns `show_upsell` when credits < 10
- UpsellModal component renders on Story Video Studio load
- Options: Subscribe from $9/mo or Top Up credits
- Dismiss with "Maybe later"

#### Landing Page V2 (Professional Redesign)
- Dark `#0a0a0f` background with grid line texture
- Gradient hero text (indigo → sky → amber)
- Emerald checkmarks beside trust signals
- Brighter font colors (slate-300 body, white headings)
- Pricing section shows $9/$19 plans inline
- Gallery link changed to dedicated `/gallery` page

### Credit System ✅ (2026-03-13)
- New signups: 10 free credits
- Updated across all signup paths + frontend pages

### Story→Video Pipeline ✅ (2026-03-13)
- Sequential render, single-threaded ffmpeg
- 5/5 consecutive + 3/3 concurrent tests passed
- Full platform audit: 100%

## Test Reports
| Iteration | Scope | Result |
|-----------|-------|--------|
| 153 | Story Video Pipeline | 100% (13/13 backend) |
| 154 | Full Platform Audit | 100% (18/18 backend, 9/9 frontend) |
| 155 | Landing Page + Credits | 100% |
| 156 | Onboarding + Dashboard + Gallery + Share | 100% (8/8 frontend) |
| 157 | Growth, Monetization & Analytics | 100% (17/17 backend, 12 frontend features) |

## Key Files
- `/app/frontend/src/pages/Landing.js` - Marketing landing page V2
- `/app/frontend/src/pages/Signup.js` - Signup with prompt capture
- `/app/frontend/src/pages/StoryVideoPipeline.js` - Studio + remix + upsell
- `/app/frontend/src/pages/Dashboard.js` - Reorganized dashboard
- `/app/frontend/src/pages/Gallery.js` - Public gallery + remix buttons
- `/app/frontend/src/pages/Pricing.js` - $9/$19 subscription plans + top-ups
- `/app/frontend/src/components/UpsellModal.js` - Upsell modal
- `/app/frontend/src/components/admin/GrowthFunnelTab.js` - Analytics funnel
- `/app/backend/routes/pipeline_routes.py` - Gallery + analytics + rate limit
- `/app/backend/routes/credits.py` - Balance + upsell check
- `/app/backend/routes/cashfree_payments.py` - Updated products/plans
- `/app/backend/routes/auth.py` - 10-credit signup

## Backlog
- P1: SendGrid email (blocked on user upgrade)
- P1: Stress Testing (5/10/20 concurrent users)
- P2: Gallery enhancements (categories, sorting, featured videos)
- P2: Share optimization (watermarking, OpenGraph metadata)
- P2: WebSocket real-time progress (replace polling)
- P3: Worker auto-scaling
- P3: Email notifications on completion
- P3: Delete obsolete legacy code

## Test Credentials
- UAT: test@visionary-suite.com / Test@2026#
- Admin: admin@creatorstudio.ai / Cr3@t0rStud!o#2026
