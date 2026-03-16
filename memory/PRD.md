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
  WebM MediaRecorder fallback if SharedArrayBuffer unavailable
  
Server FFmpeg: Admin-only emergency fallback (not user-facing)
```

**Cross-Origin Isolation (for SharedArrayBuffer / ffmpeg.wasm):**
- COOP: same-origin (backend server.py + frontend setupProxy.js)
- COEP: credentialless (compatible with R2 cross-origin images)
- CSP: blob: in script-src, worker-src 'self' blob:
- Verified: window.crossOriginIsolated === true

**Output Priority:**
1. Primary: Instant playable preview (scenes + images + audio)
2. Standard: Story Pack ZIP (all raw assets)
3. Final: Client-side downloadable MP4 (browser ffmpeg.wasm export)
4. Fallback: WebM via MediaRecorder if SharedArrayBuffer unavailable

## Implemented Features

### Core Platform
- [x] User auth (JWT + Google OAuth), Credit system, Gallery
- [x] Story → Video, Comic Storybook, GIF/Reel generators
- [x] Admin panel, TTFD Analytics, Crash Diagnostics

### Asset-First Pipeline
- [x] Pipeline: scenes → images → voices (3 stages only)
- [x] Auto manifest generation with presigned asset URLs
- [x] Auto Story Pack ZIP on completion
- [x] COMPLETED status after assets (no render required)
- [x] 100% completion rate (6/6 test runs)

### Cross-Origin Isolation & Browser Export
- [x] COOP: same-origin on all responses
- [x] COEP: credentialless on all responses
- [x] SharedArrayBuffer available in browser
- [x] ffmpeg.wasm MP4 export as primary path
- [x] WebM MediaRecorder fallback for weak browsers
- [x] CSP includes blob: and worker-src for wasm workers

### Infrastructure Stability
- [x] Auto-resume from checkpoint on server restart
- [x] Fallback for interrupted jobs
- [x] Crash diagnostics logging
- [x] My Jobs Dashboard in Profile

## Key API Endpoints
| Method | Path | Description |
|--------|------|-------------|
| POST | /api/pipeline/create | Create new pipeline job |
| GET | /api/pipeline/status/{id} | Job status + manifest + ZIP URL |
| GET | /api/pipeline/preview/{id} | Public preview data |
| POST | /api/pipeline/resume/{id} | Resume from checkpoint |

## Backlog

### P1
- [ ] Generate showcase video content for gallery
- [ ] Cashfree live payment testing

### P2
- [ ] Email notifications (blocked on SendGrid)
- [ ] Landing page conversion optimization

### P3
- [ ] Multi-language narration
- [ ] A/B testing for landing page

## Test Credentials
- Admin: admin@creatorstudio.ai / Cr3@t0rStud!o#2026
- Test: test@visionary-suite.com / Test@2026#
