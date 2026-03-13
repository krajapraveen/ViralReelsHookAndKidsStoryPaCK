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
- Reel Scripts, Kids Story Pack, Photo to Comic, Comic Storybook de-emphasized
- Clean, focused layout

### Phase 4: Growth Features ✅ (2026-03-13)
- Public Gallery page at `/gallery` (no auth required)
- Share screen after video completion: Download, Copy Link
- Social sharing buttons: X, Facebook, WhatsApp, LinkedIn
- "Create Your Own" CTA throughout gallery

### Credit System ✅ (2026-03-13)
- New signups: 10 free credits (was 100)
- Updated across all signup paths + 10+ frontend pages
- Admin/demo/UAT users retain existing credits

### Story→Video Pipeline ✅ (2026-03-13)
- Sequential render, single-threaded ffmpeg
- 5/5 consecutive + 3/3 concurrent tests passed
- Full platform audit: 100% across all 6 features

## Test Reports
| Iteration | Scope | Result |
|-----------|-------|--------|
| 153 | Story Video Pipeline | 100% (13/13 backend) |
| 154 | Full Platform Audit | 100% (18/18 backend, 9/9 frontend) |
| 155 | Landing Page + Credits | 100% |
| 156 | Onboarding + Dashboard + Gallery + Share | 100% (8/8 frontend) |

## Key Files
- `/app/frontend/src/pages/Landing.js` - Marketing landing page
- `/app/frontend/src/pages/Signup.js` - Signup with prompt capture
- `/app/frontend/src/pages/StoryVideoPipeline.js` - Studio with onboarding + share
- `/app/frontend/src/pages/Dashboard.js` - Reorganized dashboard
- `/app/frontend/src/pages/Gallery.js` - Public video gallery
- `/app/backend/routes/pipeline_routes.py` - Gallery API + pipeline endpoints
- `/app/backend/routes/auth.py` - 10-credit signup

## Backlog
- P2: WebSocket real-time progress (replace polling)
- P2: Worker auto-scaling
- P2: Email notifications on completion
- P3: Delete obsolete Story→Video code
- P1: SendGrid email (blocked on user upgrade)

## Test Credentials
- UAT: test@visionary-suite.com / Test@2026#
- Admin: admin@creatorstudio.ai / Cr3@t0rStud!o#2026
