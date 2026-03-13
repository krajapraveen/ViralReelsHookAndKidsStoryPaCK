# Visionary-Suite PRD

## Original Problem Statement
The "Story To Video" feature was unstable in production (OOM crashes). After fixing that, a full platform audit was completed. The next phase is repositioning the product: transforming from a "toolbox" site into a focused **AI Story→Video platform** to improve user activation, retention, and revenue.

## Architecture
- **Frontend**: React (CRA with craco) on port 3000
- **Backend**: FastAPI on port 8001 
- **Database**: MongoDB (creatorstudio_production)
- **Storage**: Cloudflare R2
- **Payment**: Cashfree
- **LLM**: OpenAI GPT-4o-mini, GPT Image 1, OpenAI TTS, Sora 2, Gemini
- **Video Processing**: ffmpeg (system dependency)

## Current Product Positioning
**"Turn stories into cinematic videos using AI"**
- Story→Video is the HERO feature
- Secondary tools: Reel Scripts, Photo to Comic, GIF Creator, Comic Storybook
- 10 free credits on signup (previously 100)

## What's Been Implemented

### Phase 1: New Marketing Landing Page (2026-03-13) ✅
- **Hero section**: "Turn stories into cinematic videos using AI" + CTA
- **Social proof bar**: Video count, 90s avg time, 5 pipeline stages, 5-star rating
- **How It Works**: 3-step visual (Write → AI Creates → Download)
- **Prompt templates**: 6 genre-based clickable prompts (Fantasy, Bedtime, Space, Animal, Superhero, Underwater)
- **Video Gallery**: Real generated videos from /api/pipeline/gallery (public endpoint)
- **Secondary tools**: De-emphasized "More Creator Tools" section
- **Pricing overview**: Free (10) / Starter (100) / Pro (1,000) credits
- **Final CTA**: "Your story deserves to be seen"
- **Simplified nav**: Gallery | How It Works | Pricing | Login | Start Creating
- **Mobile responsive**: Hamburger menu for mobile

### Credit System Change (2026-03-13) ✅
- New signups receive **10 free credits** (was 100)
- Updated across: email registration, Google OAuth, signup page, pricing page, blog, live chat, terms of service, demo reel generator
- Admin/demo/UAT users retain existing credits

### Production-Safe Render Stage (P0 Fix) ✅
- Sequential scene rendering, single-threaded ffmpeg
- 640x360 @ 10fps, aggressive memory control
- 5/5 consecutive + 3/3 concurrent tests passed

### Full Platform Audit ✅
- All 6 features verified (18/18 backend, 9/9 frontend)
- Credit integrity verified across all features

## Key Files
- `/app/frontend/src/pages/Landing.js` - New marketing landing page
- `/app/backend/routes/pipeline_routes.py` - Gallery API endpoint (line 30)
- `/app/backend/routes/auth.py` - Credit system (10 credits)
- `/app/backend/services/pipeline_engine.py` - Pipeline + render logic
- `/app/frontend/src/App.js` - All route definitions

## Test Reports
- iteration_153: Story Video Pipeline (100%)
- iteration_154: Full Platform Audit (100%)
- iteration_155: Landing Page + Credits (100%)

## Upcoming (Phase 2): Onboarding Flow
- Guided first-time experience after signup
- Pre-filled story prompt → one-click generate → wow moment
- Welcome screen: "Create your first video in 60 seconds"

## Upcoming (Phase 3): UX Improvements
- Dashboard reorganization (Story→Video hero at top)
- Example outputs throughout the app
- Remove decision overload

## Upcoming (Phase 4): Growth Features
- Public AI Video Gallery page (/gallery)
- Share screen after video generation
- Video watermark (already exists)

## Backlog
- P2: WebSocket real-time progress
- P2: Worker auto-scaling
- P2: Email notifications on completion
- P3: Delete obsolete old Story→Video code
- P3: GPU-accelerated rendering
- P1: SendGrid email (blocked on user's plan upgrade)

## Test Credentials
- UAT: test@visionary-suite.com / Test@2026#
- Admin: admin@creatorstudio.ai / Cr3@t0rStud!o#2026
