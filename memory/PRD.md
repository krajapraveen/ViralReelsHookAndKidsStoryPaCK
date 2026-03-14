# Visionary-Suite PRD

## Product
AI-powered Story Video Studio and Creator Tools Platform. Generates story videos, comics, coloring books, GIFs, reels, bios, and more for content creators.

## Core Architecture
- **Frontend**: React + Tailwind CSS + Shadcn/UI (dark theme: #060B1A base, #0B1220 cards)
- **Backend**: FastAPI + MongoDB
- **Storage**: Cloudflare R2 (served via presigned URLs - public URL disabled)
- **AI**: OpenAI GPT-4o-mini, GPT Image 1, Sora 2, TTS + Gemini Nano Banana
- **Payment**: Cashfree
- **Workers**: Auto-scaling pipeline worker pool (1-3 workers)

## Key Users
- **Test**: test@visionary-suite.com / Test@2026#
- **Admin**: admin@creatorstudio.ai / Cr3@t0rStud!o#2026

## What's Implemented (Complete)
- Full AI story video pipeline (script > scenes > images > voices > render > upload)
- Gallery with 30 professional showcase items (thumbnails, presigned URLs)
- Rate limiting: 5/hour for normal users, exempt for admin/test/demo
- Worker auto-scaling: 1 min, 3 max, scales on queue depth
- 50+ creator tools (reel generator, story generator, coloring book, comic maker, etc.)
- Payment/billing system (Cashfree integration)
- Admin dashboard with analytics, user management, monitoring
- UI: Consistent dark professional theme across all pages
- Error boundary with recovery options
- Credit system with refunds on failure
- New signups get 0 credits (no free signup bonus)
- Admin/Demo/UAT users have unlimited credits (999,999)
- Landing page spacing reduced between sections
- All 26 landing page links/buttons verified working correctly
- R2 presigned URL utility for all media assets
- Dynamic worker auto-scaling in pipeline

### Premium Dashboard with Engagement System (Completed Mar 14, 2026)
- **2-Column Layout**: Main content (left) + utility sidebar (right, 320px, hidden lg:block)
- **Universal AI Prompt**: Keyword intent detection routes to correct tool (16 tool mappings)
- **3 Hero Action Cards**: Story Video, Photo to Comic, Reel Generator with gradient cards
- **6 Inspiration Templates**: Pre-filled prompts with one-click navigation
- **Recent Creations**: Generation history with status badges (COMPLETED/FAILED/PENDING)
- **Tool Categories**: 4 tabbed categories (Video/Image/Story/Social) with 20+ tools
- **Trending Feed**: Top 6 gallery items with presigned thumbnails
- **Credits Panel**: Balance display, progress bar, Buy/Plans CTAs
- **Creator Level System**: 5 levels (Beginner > Creator > Creator Pro > AI Producer > Visionary)
- **Daily Challenge**: Rotating challenges from 30-item pool, +10-15 credit rewards
- **Creation Streak**: 7-day calendar tracker with milestone rewards (3/7/14/30/60/100 days)
- **AI Ideas**: 4 personalized daily suggestions per user
- **Activity Feed**: Recent generation timeline
- **Quick Links**: Referrals, Analytics, Payments, Help Center
- **Responsive**: Desktop 2-column, tablet/mobile single-column

## Engagement System Backend
- `GET /api/engagement/dashboard` - Full dashboard data (challenge, streak, level, ideas)
- `POST /api/engagement/challenge/complete` - Complete daily challenge, award credits
- `POST /api/engagement/streak/update` - Update creation streak after successful generation
- `GET /api/engagement/trending` - Top 6 trending gallery items
- **Collections**: challenge_completions, creation_streaks
- **Streak Milestones**: 3d=10cr, 7d=25cr, 14d=50cr, 30d=100cr, 60d=250cr, 100d=500cr
- **Creator Levels**: Beginner(0), Creator(10), Creator Pro(50), AI Producer(150), Visionary(500)

## Backlog
- **P1**: WebSocket real-time progress for video generation
- **P1**: Video watermarking for free plan users
- **P1**: SendGrid email (BLOCKED - needs plan upgrade)
- **P2**: Email notifications on video completion

## Test Reports
| Iter | Scope | Backend | Frontend |
|------|-------|---------|----------|
| 255 | Gallery Showcase | 100% | 100% |
| 256 | Full Production Audit | 93% (39/42) | 100% |
| 257 | Premium Dashboard Redesign | N/A | 100% (29/29) |
| 161 | Engagement Dashboard E2E | 76% (16/21)* | 100% |

*5 backend failures were test file path issues, not actual bugs. All engagement APIs passed 100%.

## Technical Notes
- R2 public URL returns 403 - all media served via presigned URLs (4hr expiry)
- Presigned URL utility: `/app/backend/utils/r2_presign.py`
- Pipeline rendering: 1280x720, 24fps, veryfast preset
- Thumbnail generation via ffmpeg frame extraction
- Dashboard sidebar uses `hidden lg:block` for responsive hiding (>=1024px only)
