# Visionary-Suite PRD

## Product
AI-powered Story Video Studio and Creator Tools Platform. Generates story videos, comics, coloring books, GIFs, reels, bios, and more for content creators.

## Core Architecture
- **Frontend**: React + Tailwind CSS + Shadcn/UI (dark theme: slate-950/indigo-950 gradient)
- **Backend**: FastAPI + MongoDB
- **Storage**: Cloudflare R2 (served via presigned URLs - public URL disabled)
- **AI**: OpenAI GPT-4o-mini, GPT Image 1, Sora 2, TTS + Gemini Nano Banana
- **Payment**: Cashfree
- **Workers**: Auto-scaling pipeline worker pool (1-3 workers)

## Key Users
- **Test**: test@visionary-suite.com / Test@2026#
- **Admin**: admin@creatorstudio.ai / Cr3@t0rStud!o#2026

## What's Implemented (Complete)
- Full AI story video pipeline (script → scenes → images → voices → render → upload)
- Gallery with 30 professional showcase items (thumbnails, presigned URLs)
- Rate limiting: 5/hour for normal users, exempt for admin/test/demo
- Worker auto-scaling: 1 min, 3 max, scales on queue depth
- 50+ creator tools (reel generator, story generator, coloring book, comic maker, etc.)
- Payment/billing system (Cashfree integration)
- Admin dashboard with analytics, user management, monitoring
- UI: Consistent dark professional theme across all pages
- Error boundary with recovery options
- Credit system with refunds on failure
- **New signups get 0 credits (no free signup bonus)**
- **Admin/Demo/UAT users have unlimited credits (999,999)**
- **Landing page spacing reduced between sections**
- **All 26 landing page links/buttons verified working correctly**

## Backlog
- **P1**: SendGrid email (BLOCKED - needs plan upgrade)
- **P1**: WebSocket real-time progress for video generation
- **P2**: Video watermarking for free plan
- **P2**: Email notifications on video completion

## Test Reports
| Iter | Scope | Backend | Frontend |
|------|-------|---------|----------|
| 255 | Gallery Showcase | 100% | 100% |
| 256 | **Full Production Audit** | **93% (39/42)** | **100%** |

## Technical Notes
- R2 public URL returns 403 - all media served via presigned URLs (4hr expiry)
- Presigned URL utility: `/app/backend/utils/r2_presign.py`
- Pipeline rendering: 1280x720, 24fps, veryfast preset
- Thumbnail generation via ffmpeg frame extraction
