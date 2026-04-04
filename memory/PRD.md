# Daily Viral Idea Drop — PRD

## Original Problem Statement
Build a "Growth Engine" / "Daily Viral Idea Drop" — queue-driven AI content creation. Secure all generated media assets. Apply site-wide anti-copy friction with secure proxy-based asset protection, watermarking, entitlement enforcement, telemetry, and forensic traceability.

## Core Architecture
- React frontend + FastAPI backend + MongoDB
- Media Proxy Layer: JWT-signed streaming, visible + forensic watermarking, entitlement gating
- Site-Wide Content Protection: Reusable hook + wrapper, route-based activation
- Telemetry: Rich logging (IP, user-agent, action), abuse flagging, admin dashboards

## What's Been Implemented

### P0 — URL Leak Consistency Bug — FIXED (April 4, 2026)
- Bug: 2/66 DB records stored file_url as `/static/...` instead of `/api/static/...`
- Fix: `_is_protected_asset_url()` + `_normalize_asset_url()` handles both prefixes
- Audit: 126/126 assets — 66 secure_url, 60 content, 0 leaks, 0 misses

### P0 — Site-Wide Anti-Copy Friction Layer — COMPLETE (April 4, 2026)
- `useContentProtection` hook: right-click, drag, copy/cut, Ctrl+S/C/A/U, PrintScreen, mobile long-press
- `ContentProtectionWrapper`: route-based activation, form/input exemptions
- Protected: all `/app/*` (except admin), `/viral/*`, `/share/*`, `/gallery`, `/explore`
- Unprotected: `/`, `/login`, `/signup`, `/pricing`, `/contact`, `/blog`, legal pages, admin

### P1 — Entitlement Gating — COMPLETE (April 4, 2026)
- Download tokens require authenticated owner of unlocked pack
- Admin bypass explicit
- Rate limit: 30 download tokens per user per hour
- Non-owner returns 403, locked pack returns 402, unauthenticated returns 401
- Abuse flag auto-created when rate limit exceeded

### P1 — Telemetry / Abuse Detection — COMPLETE (April 4, 2026)
- Every media event logged: action, user_id, IP, user-agent, asset details, timestamp
- Abuse flagging: automatic when download rate exceeds threshold
- Admin endpoints:
  - `GET /api/media/admin/telemetry-summary` — aggregated stats, top downloaders, denied events, open flags
  - `GET /api/media/admin/access-log` — filtered log viewer with IP, user-agent
  - `GET /api/media/admin/abuse-flags` — view/resolve abuse flags
  - `POST /api/media/admin/abuse-flags/{flag_id}/resolve` — resolve specific flag
- All admin endpoints return 403 for non-admin users

### P1 — Forensic Watermarking — COMPLETE (April 4, 2026)
- Format: `UID:{user_id}|AID:{asset_id}|DL:{download_event_id}|TS:{unix_timestamp}`
- Image: Embedded in PNG metadata (Description + Comment fields) and JPEG EXIF (ImageDescription)
- Video: Embedded in MP4 metadata (comment + description) via ffmpeg
- Audio: Embedded in MP3/WAV metadata (comment + artist) via ffmpeg
- Admin downloads exempt from forensic watermarking
- Every forensic download logged in media_access_log with forensic_id and watermark_type

### Protection Stack Summary
| Layer | What It Does | Status |
|-------|-------------|--------|
| URL Blocking | Direct `/api/static/generated/viral_*` returns 403 | DONE |
| Media Proxy | All assets served via JWT-signed `/api/media/stream/{token}` | DONE |
| Visible Watermark | Tiled user email + job ID on preview images | DONE |
| Browser Friction | Right-click, drag, copy, shortcuts blocked site-wide | DONE |
| Entitlement Gating | Ownership + role check on download tokens, rate limiting | DONE |
| Telemetry | Rich logging, abuse flagging, admin dashboards | DONE |
| Forensic Watermark | UID+AID+DL+TS embedded in downloaded image/video/audio metadata | DONE |

### What CANNOT Be Prevented (by design)
- Screenshots, screen recording, OS capture tools
- Browser extensions, devtools
- Physical photography
Goal is: friction + entitlement + proxy + traceability — not fantasy.

## Key Files
- `/app/backend/routes/media_proxy.py` — All layers: proxy, entitlement, telemetry, forensic watermarking, admin endpoints
- `/app/backend/routes/viral_ideas_v2.py` — Asset API, URL normalization helpers
- `/app/frontend/src/hooks/useContentProtection.js` — Anti-copy friction hook
- `/app/frontend/src/components/ContentProtectionWrapper.js` — Route-based wrapper
- `/app/frontend/src/App.js` — Integration point
- `/app/frontend/src/App.css` — CSS protection rules + form exemptions

## DB Collections
- `media_access_log` — fields: user_id, action, ip, user_agent, timestamp, asset_id, asset_type, purpose, forensic_id, watermark_type, entitlement, reason, file_ext
- `media_abuse_flags` — fields: flag_id, user_id, reason, details, status (open/resolved), created_at, resolved_by, resolved_at

## Backlog
- (P2) Personalization and Precomputed Daily Packs
- (P2) Remix Variants and Story Chain leaderboard
- (P2) Admin Dashboard WebSocket upgrades
- (P2) Entitlement tiers (free vs premium download quality/limits)

## Credentials
- Test: `test@visionary-suite.com` / `Test@2026#`
- Admin: `admin@creatorstudio.ai` / `Cr3@t0rStud!o#2026`
