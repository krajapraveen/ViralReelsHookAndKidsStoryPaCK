# Visionary-Suite — Product Requirements Document

## Original Problem Statement
AI content generation platform (story videos, comics, GIFs, reels). 

## Final Permanent Architecture (Approved Mar 2026)
```
Backend (FastAPI + MongoDB + Redis + Cloudflare R2):
  scenes → images → voices → manifest + ZIP → COMPLETED
  No server-side video rendering in normal user flow.
  
Frontend (React + TailwindCSS + Shadcn + ffmpeg.wasm):
  Instant preview → Browser-side MP4 export → Download
  
Server FFmpeg: Admin-only emergency fallback (not user-facing)
```

**Output Priority:**
1. Primary: Instant playable preview (scenes + images + audio)
2. Standard: Story Pack ZIP (all raw assets)
3. Final: Client-side downloadable MP4 (browser ffmpeg.wasm export)

## Architecture Details

### Backend (asset generation only)
- Story → Scene → Image → Voice generation
- R2 asset storage with presigned URLs
- Manifest creation (complete data for browser export)
- Auto ZIP generation on completion
- Workers process only asset stages → freed from render/upload

### Frontend (preview + export)
- Progressive preview (scenes stream in as generated)
- Instant playable web preview when assets ready
- Browser-side MP4 export via ffmpeg.wasm
- Story Pack ZIP download always available
- Graceful degradation if browser export fails

### Completion Semantics
Job is COMPLETED when: scenes + images + voices + manifest + ZIP exist.
NOT dependent on server-rendered MP4.

## Implemented Features

### Core Platform
- [x] User auth (JWT + Google OAuth), Credit system, Gallery
- [x] Story → Video, Comic Storybook, GIF/Reel generators
- [x] Admin panel, TTFD Analytics, Crash Diagnostics

### Asset-First Pipeline (Permanent Architecture)
- [x] Pipeline: scenes → images → voices (3 stages only)
- [x] Auto manifest generation with presigned asset URLs
- [x] Auto Story Pack ZIP on completion
- [x] COMPLETED status after assets (no render required)
- [x] Preview page as primary output destination
- [x] Browser-side Export MP4 as primary video path
- [x] "Your story is ready" banner with 3 options
- [x] Worker throughput improvement (no render blocking)
- [x] 100% completion rate (6/6 test runs)

### Infrastructure Stability
- [x] Auto-resume from checkpoint on server restart
- [x] Fallback for interrupted jobs
- [x] Crash diagnostics logging
- [x] Enhanced error recovery UI
- [x] has_recoverable_assets detection

### My Jobs Dashboard
- [x] Profile tab with filters and job cards
- [x] Resume, Preview, Download actions

### Error Handling
- [x] Specific error messages (422/401/402/429/500/network)
- [x] Action links (Go to Login, Get More Credits)

## Key API Endpoints
| Method | Path | Description |
|--------|------|-------------|
| POST | /api/pipeline/create | Create new pipeline job |
| GET | /api/pipeline/status/{id} | Job status + manifest + ZIP URL |
| GET | /api/pipeline/preview/{id} | Public preview data |
| POST | /api/pipeline/resume/{id} | Resume from checkpoint |
| GET | /api/pipeline/user-jobs | All user jobs |
| GET | /api/pipeline/crash-diagnostics | Admin crash logs |

## Production Test Results (Mar 2026)
| Test | Result |
|------|--------|
| 5 consecutive runs | 6/6 COMPLETED |
| Manifest generated | 6/6 YES |
| ZIP generated | 6/6 YES |
| Preview works | VERIFIED |
| Browser export available | VERIFIED |
| No render/upload in pipeline | VERIFIED |
| Resume works | VERIFIED |

## Backlog

### P1
- [ ] Generate showcase video content for gallery
- [ ] Cashfree live payment testing

### P2
- [ ] Email notifications (blocked on SendGrid)
- [ ] Landing page conversion optimization
- [ ] Free → Paid upgrade flow

### P3
- [ ] Multi-language narration
- [ ] A/B testing for landing page

## Test Credentials
- Admin: admin@creatorstudio.ai / Cr3@t0rStud!o#2026
- Test: test@visionary-suite.com / Test@2026#
