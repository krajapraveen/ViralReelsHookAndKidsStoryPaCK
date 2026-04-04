# Daily Viral Idea Drop — PRD

## Original Problem Statement
Build a "Growth Engine" / "Daily Viral Idea Drop" — queue-driven AI content creation. Never show dead-end UI. Optimize strictly for growth and conversion. Secure all generated media assets behind authenticated proxy with zero raw URL exposure.

## Core Architecture
- React frontend + FastAPI backend + MongoDB
- 7 background workers + queue abstraction + fallback ladder
- Media Proxy Layer: JWT-signed streaming, watermarking, direct static access blocked

## What's Been Implemented

### P0 Fixes (All verified — April 4, 2026)

**1. Generation Blank Screen Bug — FIXED**
- Root cause: `handleGenerate` never set activeIdea/activeNiche state
- Fix: Added state setters + prop passing to ProgressView

**2. Broken Media Assets on Result Page — FIXED**
- Root cause (video): moviepy ffmpeg v7.0.2 produced non-web-compatible MP4s
- Fix: System ffmpeg re-encode (baseline h264, faststart), all existing videos re-encoded
- Frontend: VideoAsset, ThumbnailAsset, VoiceoverAsset components with onError fallbacks

**3. "Generate Another Pack" Dead Button — FIXED**
- Root cause: `<Link to="/app/daily-viral-ideas">` navigated to same route without resetting `view` state
- Fix: Replaced with `<button onClick={onGoToFeed}>` that resets view to 'feed'

**4. Credit Reset to 50 — DONE**
- Hard reset 30 non-admin users to exactly 50 credits
- 3 admins excluded

**5. Admin Dashboard — VERIFIED ON PRODUCTION**
- All 10+ backend endpoints return 200

### P0 Media Protection Hardening — COMPLETED (April 4, 2026)

**6. Media Proxy & URL Blocking — DONE**
- Created `/api/media/stream/{token}` for JWT-signed asset delivery
- Created `/api/media/download-token` for authenticated downloads
- Blocked direct access to `/api/static/generated/viral_*` (returns 403)
- All file-based assets (thumbnail, video, voiceover, zip_bundle) served via secure_url
- file_url stripped from all API responses — zero raw URL exposure

**7. URL Prefix Inconsistency Bug — FIXED (April 4, 2026)**
- Bug: 2/66 DB records stored file_url as `/static/generated/viral_*` (missing `/api/` prefix)
- The prefix check `raw_url.startswith("/api/static/generated/viral_")` silently failed for these
- Result: assets got NEITHER secure_url NOR file_url — silent data loss
- Fix: Added `_is_protected_asset_url()` (matches both prefixes) and `_normalize_asset_url()` (normalizes to `/api/static/...`)
- Verified: 126/126 assets pass — 66 with secure_url, 60 with content, 0 leaks, 0 misses

**8. Image Watermarking — DONE**
- Preview images served with diagonal tiled watermark (user email fragment + job ID)
- Admin users exempt from watermarking

**9. Browser Friction Layer — DONE**
- CSS: `user-select: none`, `-webkit-touch-callout: none`
- JS: contextmenu, copy, keydown (PrintScreen), dragstart event blocking on result view

### Full Audit Results
```
Total assets in DB:                126
Assets with file_url:              66
  /api/static/ prefix:             64
  /static/ prefix (bug case):      2
  unexpected prefix:               0
Assets without file_url:           60
  text-only (have content):        60
  no file_url AND no content:      0

API Output After Fix:
  secure_url present:              66
  content present (text-only):     60
  file_url leaked:                 0
  missing (neither):               0
```

## Key Files
- `/app/backend/routes/viral_ideas_v2.py` — Asset API, URL normalization
- `/app/backend/routes/media_proxy.py` — Token signing, streaming, watermarking
- `/app/backend/server.py` — Static file blocking middleware
- `/app/frontend/src/pages/DailyViralIdeas.js` — Result view, secure URL consumption
- `/app/backend/tests/test_media_protection.py` — 16 unit tests
- `/app/backend/tests/test_media_protection_api.py` — 14 API integration tests

## Next Priorities (NOT optional — required for complete asset protection)

### P1 — Entitlement Gating
- Enforce Free vs Paid user download controls on token generation
- Rate limit token generation per user

### P1 — Telemetry for Abuse Detection
- Track token generation frequency per user/IP
- Alert on abnormal download spikes
- Log all media access with user/IP/asset metadata

### P1 — Forensic Watermarking
- Add hidden identifiers to exported files (images, video, audio)
- Traceable back to specific user/download event

## Backlog
- (P2) Personalization and Precomputed Daily Packs
- (P2) Remix Variants and Story Chain leaderboard
- (P2) Admin Dashboard WebSocket upgrades
- (P2) General UI polish and style preset preview thumbnails

## Credentials
- Test: `test@visionary-suite.com` / `Test@2026#`
- Admin: `admin@creatorstudio.ai` / `Cr3@t0rStud!o#2026`
