# Visionary-Suite PRD

## Product Vision
**"Turn stories into cinematic videos using AI"**

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

### Phase 5: Growth, Monetization & Analytics ✅
- Creator $9/mo, Pro $19/mo, credit top-ups ($5/$12/$30)
- Remix viral growth loop, rate limiting, analytics funnel, upsell modal

### Phase 6-10: Landing V3, Gallery, OG, Performance, Stress Testing ✅
- Text-only landing page (no videos), gallery categories/sorting/leaderboard
- OpenGraph meta tags, performance monitoring tab, stress tested 5/10/20 users

### P0 Bug Fix: Story Video Studio Blank Page ✅ (2026-03-14)
#### Root Causes Identified & Fixed:
1. **Stale PROCESSING jobs** blocking new creations — added 15-min auto-timeout
2. **Pydantic model error** — `parent_video_id: str` rejected `null` → fixed to `Optional[str]`
3. **JS TypeError** — `detail.toLowerCase()` crashed when `detail` was not a string → defensive type check
4. **Silent disabled button** — `disabled={isDisabled}` prevented ALL click feedback → button always clickable, validates on click
5. **Missing error boundary** — component crash = blank page → added React ErrorBoundary
6. **No rate-limit pre-check** — users couldn't see why they can't create → added `/api/pipeline/rate-limit-status`

#### Files Changed:
- `/app/backend/routes/pipeline_routes.py` — Auto-timeout stale jobs, rate-limit-status endpoint, Optional[str] fix
- `/app/frontend/src/pages/StoryVideoPipeline.js` — Complete rewrite with ErrorBoundary, inline validation, rate-limit awareness, active job banner

#### Validation Fixes:
- Empty title → "Please enter a title for your video."
- Title < 3 chars → "Title must be at least 3 characters."
- Title > 100 chars → "Title must be 100 characters or less."
- Empty story → "Please enter a story to generate a video from."
- Story < 50 chars → "Story must be at least 50 characters. You have X — need Y more."
- Rate limited → Shows amber warning with exact reason
- Concurrent job → "You have a video currently generating" banner with View Progress button
- API 429 → Inline error with clear message
- API 402 → Insufficient credits + upsell modal
- API 401 → Session expired message

## Test Reports
| Iteration | Scope | Result |
|-----------|-------|--------|
| 157 | Phase 5 | 100% |
| 158 | Phases 6-10 | 100% (22/22 backend) |
| 159 | P0 Bug Fix | 90% (20/22 — 2 failures were test-script session issues) |

## Backlog
- P1: SendGrid email (blocked on user upgrade)
- P2: Automatic video watermarking
- P2: WebSocket real-time progress (replace polling)
- P3: Worker auto-scaling
- P3: Email notifications on completion
- P3: Legacy code cleanup

## Test Credentials
- UAT: test@visionary-suite.com / Test@2026#
- Admin: admin@creatorstudio.ai / Cr3@t0rStud!o#2026
