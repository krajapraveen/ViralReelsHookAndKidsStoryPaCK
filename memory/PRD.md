# Visionary-Suite — Product Requirements Document

## Original Problem Statement
AI content generation platform (story videos, comics, GIFs, reels). Progressive delivery architecture with browser-side rendering.

## Architecture
```
Backend (FastAPI + MongoDB + Redis):
  Story generation → Scene generation → Image generation → Voice generation → Asset storage (R2)
  
Frontend (React + TailwindCSS + Shadcn):
  Progressive preview → Web player → Browser-side MP4 export (ffmpeg.wasm)
  
Server FFmpeg: Admin-only fallback (not default path)
```

**3-Tier Output Model:**
1. Instant: Playable web preview (free)
2. Standard: Story Pack ZIP (images, audio, text)
3. Premium: Final MP4 export (browser-rendered)

## Implemented Features

### Core Platform
- [x] User auth (JWT + Google OAuth), Credit system, Gallery (30 showcase items)
- [x] Story → Video pipeline, Comic Storybook Builder, GIF/Reel generators
- [x] Admin panel with full analytics (parallel queries)

### Growth & Monetization
- [x] Priority queue (Admin > Paid > Free), Video watermarking (free)
- [x] Global CreditContext, Real-time WebSocket progress
- [x] Landing page optimization + Testimonials, Social sharing + OpenGraph
- [x] Cashfree payments with Geo-IP (INR/USD)

### Fallback Output System (Mar 2026)
- [x] Server fallback MP4, Story Pack ZIP, Public preview page
- [x] R2 presigned asset links, Notify-when-ready, Manual fallback trigger
- [x] Auto-fallback on render/upload failure

### Progressive Delivery + Client-Side Export (Mar 2026)
- [x] Per-asset WebSocket events (scene_ready, image_ready, voice_ready, preview_ready)
- [x] ProgressiveGeneration component with live scene cards
- [x] Web Preview Player with synced audio
- [x] BrowserVideoExport (ffmpeg.wasm, 720p, 15fps)
- [x] useJobWebSocket hook with auto-reconnect

### TTFD Analytics System (Mar 2026)
- [x] **Backend TTFD tracking**: Timestamps for scene_start, first_scene, first_image, first_voice, first_playable_preview, job_complete
- [x] **Derived metrics**: time_to_first_scene, time_to_first_image, time_to_first_voice, time_to_first_playable_preview, total_generation_time
- [x] **Queue performance**: Wait times by tier (free/paid/admin), avg/p95, starvation boost count
- [x] **Engagement tracking**: POST /api/analytics/track-event/{job_id}
- [x] **Admin TTFD Dashboard**: /app/admin/ttfd-analytics
- [x] **Daily aggregation job**: Runs hourly

### P0 Infrastructure Stability — Job Durability (Mar 2026)
- [x] **Auto-resume from checkpoint**: Jobs with completed stages auto-resume on server restart instead of being marked FAILED
- [x] **Fallback for interrupted jobs**: If resume fails but assets exist, fallback pipeline generates Story Pack ZIP + preview
- [x] **Crash diagnostics logging**: Each interrupt records restart_timestamp, job_id, stage_interrupted, progress, completed_stages, reason
- [x] **Enhanced error recovery UI**: ErrorPhase shows "Open Preview", "Download Story Pack ZIP", "Resume from Checkpoint", "Start Over"
- [x] **has_recoverable_assets flag**: Status and user-jobs endpoints report when raw assets exist even without formal fallback
- [x] **Admin crash diagnostics endpoint**: GET /api/pipeline/crash-diagnostics with full crash history
- [x] **Fallback triggers on any stage failure**: Not just render/upload — any stage with existing assets triggers fallback pipeline

### Performance Targets
| Metric | Target | Current |
|--------|--------|---------|
| Time to First Scene | <5s | 9.35s |
| Time to First Image | <20s | 60.47s |
| Time to Playable Preview | <60s | 79s |
| Export Success Rate | >95% | 0% (render env) |

## Key API Endpoints
| Method | Path | Description |
|--------|------|-------------|
| GET | /api/analytics/ttfd | TTFD metrics, targets, engagement, trends |
| GET | /api/analytics/queue | Queue depth, tier wait times |
| POST | /api/analytics/track-event/{job_id} | Track engagement event |
| GET | /api/analytics/daily-aggregates | Pre-computed daily analytics |
| GET | /api/pipeline/preview/{job_id} | Public preview data |
| GET | /api/pipeline/assets/{job_id} | Individual asset links |
| POST | /api/pipeline/notify-when-ready/{job_id} | Notification subscription |
| POST | /api/pipeline/generate-fallback/{job_id} | Manual fallback trigger |
| POST | /api/pipeline/resume/{job_id} | Resume job from checkpoint |
| GET | /api/pipeline/crash-diagnostics | Admin crash diagnostic logs |

## Backlog

### P1
- [ ] Generate showcase video content for gallery
- [ ] Improve TTFD performance (scene generation speed, parallel image gen)
- [ ] Cashfree live payment testing with production keys

### P2
- [ ] Email notifications (blocked on SendGrid)
- [ ] Onboarding flow optimization
- [ ] Free → Paid upgrade flow optimization
- [ ] Landing page conversion improvements

### P3
- [ ] Multi-language narration, Custom voice cloning
- [ ] Deprecate server FFmpeg after browser export proven stable
- [ ] A/B testing for landing page

## Test Credentials
- Admin: admin@creatorstudio.ai / Cr3@t0rStud!o#2026
- Test: test@visionary-suite.com / Test@2026#
