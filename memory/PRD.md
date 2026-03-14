# Visionary-Suite PRD

## Product
AI-powered Story Video Studio and Creator Tools Platform. Generates story videos, comics, coloring books, GIFs, reels, bios, and more for content creators.

## Core Architecture
- **Frontend**: React + Tailwind CSS + Shadcn/UI (dark theme: #060B1A base, #0B1220 cards)
- **Backend**: FastAPI + MongoDB
- **Storage**: Cloudflare R2 (served via presigned URLs - public URL disabled)
- **AI**: OpenAI GPT-4o-mini, GPT Image 1, Sora 2, TTS + Gemini Nano Banana
- **Payment**: Cashfree
- **Workers**: Auto-scaling pipeline worker pool (1-3 workers) + 6 feature pools

## Key Users
- **Test**: test@visionary-suite.com / Test@2026#
- **Admin**: admin@creatorstudio.ai / Cr3@t0rStud!o#2026

## What's Implemented (Complete)

### Core Platform
- Full AI story video pipeline (script > scenes > images > voices > render > upload)
- Gallery with 30 professional showcase items (thumbnails, presigned URLs)
- Rate limiting: 5/hour for normal users, exempt for admin/test/demo
- Worker auto-scaling: 1 min, 3 max, scales on queue depth
- 50+ creator tools (reel generator, story generator, coloring book, comic maker, etc.)
- Payment/billing system (Cashfree integration)
- Admin dashboard with analytics, user management, monitoring
- UI: Consistent dark professional theme across all pages
- Error boundary with recovery options
- Credit system with refunds on failure (0 credits for new signups, unlimited for admin/demo/UAT)

### Premium Dashboard with Engagement System (Completed Mar 14, 2026)
- 2-Column Layout: Main content (left) + utility sidebar (right, 320px, hidden lg:block)
- Universal AI Prompt: Keyword intent detection routes to correct tool (16 tool mappings)
- 3 Hero Action Cards: Story Video, Photo to Comic, Reel Generator
- 6 Inspiration Templates: Pre-filled prompts with one-click navigation
- Recent Creations: Generation history with status badges
- Tool Categories: 4 tabbed categories (Video/Image/Story/Social) with 20+ tools
- Trending Feed: Top 6 gallery items with presigned thumbnails
- Credits Panel, Creator Level (5 levels), Daily Challenge, Creation Streak (7-day), AI Ideas, Activity Feed, Quick Links

### Remix & Variations Engine (Completed Mar 14, 2026)
- **CreationActionsBar component**: Reusable across all 7 tools
  - Quick Variations Row: 4 one-click buttons (Funny, Dramatic, Anime Style, Short Version etc.)
  - Style Switcher: Dropdown with 5-7 styles per tool
  - Prompt Edit + Remix: Editable prompt box with Generate button
  - Cross-Tool Conversions: Turn Into Reel, Turn Into Comic, Turn Into Video etc.
  - Regenerate button
  - Remix Source Tag: Shows "Remixed from: [title]"
- **Variation configs for 7 tools**: story-video-studio, reels, photo-to-comic, gif-maker, stories, bedtime-story-builder, comic-storybook
- **Remix tracking**: All remix events logged with source_tool, target_tool, variation_type, lineage
- **Navigation state integration**: Tools accept `location.state.prompt` for pre-filled input on remix
- **Backend**: `/api/remix/variations/{tool}`, `/api/remix/track`, `/api/remix/stats`

### Engagement Analytics (Completed Mar 14, 2026)
- Track CTA clicks (upgrade banners, buy credits, plans)
- Track template usage
- Admin analytics report: challenge completion rate, streak retention (7/14/30d), creations per user, remix rate, remix chain length, cross-tool conversions, variation click rate, template usage

### P0 Pipeline & Worker Fixes (Completed Mar 14, 2026)
- **Asset download reliability**: Retry logic with 3 attempts, presigned URL regeneration, R2 key fallback
- **Stuck job recovery**: Periodic loop (every 2 min) detects jobs stuck >10 min, marks FAILED, refunds credits
- **Stale job cleanup**: On server restart, auto-fails orphaned PROCESSING/QUEUED jobs with credit refund
- **ffmpeg optimization**: ultrafast preset, scene timeout 120s, concat timeout 120s
- **Progress reporting**: Sub-step updates during render (downloading, encoding, concatenating)
- **Frontend stuck detection**: Polling detects stale progress (no change for ~3.3 min), shows retry message
- **R2 presign utility**: Handles .r2.dev/ and r2.cloudflarestorage.com URLs, strips query params, key-based fallback
- **R2 key storage**: Image/voice assets store R2 key alongside URL for reliable re-download

## API Endpoints

### Remix Engine
- `GET /api/remix/variations/{tool_type}` - Variation config per tool (public)
- `POST /api/remix/track` - Track remix event (auth required)
- `GET /api/remix/stats` - Remix analytics (admin: full breakdown, user: total count)

### Engagement Analytics
- `POST /api/engagement-analytics/track-cta` - Track CTA clicks
- `POST /api/engagement-analytics/track-template` - Track template usage
- `GET /api/engagement-analytics/report` - Full admin analytics report

### Engagement System
- `GET /api/engagement/dashboard` - Full dashboard data
- `POST /api/engagement/challenge/complete` - Complete daily challenge
- `POST /api/engagement/streak/update` - Update creation streak
- `GET /api/engagement/trending` - Top 6 trending items

## Backlog
- **P1**: WebSocket real-time progress for video generation
- **P1**: Video watermarking for free plan users
- **P1**: SendGrid email (BLOCKED - needs plan upgrade)
- **P2**: Email notifications on video completion
- **P2**: Break Dashboard.js into smaller components for maintainability

## Test Reports
| Iter | Scope | Backend | Frontend |
|------|-------|---------|----------|
| 161 | Engagement Dashboard E2E | 76% | 100% |
| 162 | Remix + Analytics + Pipeline | 95% (20/21) | 100% |

## Technical Notes
- R2 public URL returns 403 - all media served via presigned URLs (4hr expiry)
- Pipeline rendering: 1280x720, 24fps, ultrafast preset
- Stuck job recovery: every 2 min, 10 min timeout, auto credit refund
- CreationActionsBar: conditionally rendered after generation completes
- Dashboard sidebar: hidden lg:block (desktop only)
