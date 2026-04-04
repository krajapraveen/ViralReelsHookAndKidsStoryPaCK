# Daily Viral Idea Drop — PRD

## Original Problem Statement
Full anti-copy/media-protection hardening for a queue-driven AI content creation platform. Protect generated media via opaque tokens, entitlement gating, anti-replay, HLS streaming, forensic watermarking, concurrency limits, abuse response, and admin oversight.

## Protection Stack (All Layers Complete)

| # | Layer | What It Does | Status |
|---|-------|-------------|--------|
| 1 | URL Blocking | `/api/static/generated/viral_*` returns 403 | DONE |
| 2 | Media Proxy | All assets via `/api/media/stream/{token}` | DONE |
| 3 | Visible Watermark | Tiled email + job ID on preview images | DONE |
| 4 | Browser Friction | Right-click, drag, copy, shortcuts — site-wide, route-aware | DONE |
| 5 | DB-Backed Opaque Tokens | Server-stored hashed tokens, replaces JWT-only | DONE |
| 6 | Anti-Replay | Single-use downloads, IP/UA binding, auto-revoke on mismatch | DONE |
| 7 | HLS Video Streaming | Tokenized manifest + segments, no raw MP4 for protected content | DONE |
| 8 | Forensic Watermarking | Pixel-level (images), frame-level (video), metadata (all), trace_manifest (ZIP) | DONE |
| 9 | Entitlement Gating | Ownership + role check, rate limiting (30/hr), session binding | DONE |
| 10 | Concurrency Limits | Free: 1 session, Paid: 3 sessions, oldest terminated | DONE |
| 11 | Active Abuse Response | Auto-suspend on severe abuse, token revocation, forced re-auth | DONE |
| 12 | Admin Dashboard | Overview, events, flags, per-user investigation, actions | DONE |

## DB Schemas Added
- `media_tokens`: token_hash, user_id, asset_id, file_ref, asset_type, purpose, expires_at, max_uses, used_count, session_id, ip_hash, ua_hash, status, created_at
- `user_media_sessions`: session_id, user_id, started_at, last_active, status, ip, ua_hash
- `media_suspensions`: suspension_id, user_id, status, reason, created_at, expires_at
- `media_abuse_flags`: flag_id, user_id, reason, details, severity, status, created_at
- `media_access_log`: user_id, action, ip, user_agent, timestamp, (extras: asset_id, forensic_id, watermark_type, etc.)

## API Endpoints

### Token Issuance
- `POST /api/media/access/issue` — preview/stream token (limited uses, 120s TTL)
- `POST /api/media/download/issue` — single-use download token (60s TTL, entitlement-gated)
- `POST /api/media/download-token` — legacy backwards-compat endpoint

### HLS Video
- `POST /api/media/hls/issue` — tokenized HLS manifest URL
- `GET /api/media/hls/manifest/{token}` — m3u8 with tokenized segment URLs
- `GET /api/media/hls/segment/{token}/{asset_id}/{segment}` — individual segment

### Media Delivery
- `GET /api/media/stream/{token}` — stream/download via opaque or legacy HMAC token

### Sessions
- `POST /api/media/session/start` — create media session (enforces concurrency)

### Admin
- `GET /api/admin/media/overview` — aggregated stats
- `GET /api/admin/media/access-events` — filtered event log
- `GET /api/admin/media/abuse-flags` — abuse flag list
- `GET /api/admin/media/user/{user_id}` — per-user investigation
- `POST /api/admin/media/tokens/revoke` — revoke all user tokens
- `POST /api/admin/media/users/suspend-media` — suspend user media access
- `POST /api/admin/media/users/unsuspend-media` — unsuspend
- `POST /api/admin/media/flags/resolve` — resolve abuse flag

## Key Files
- `/app/backend/services/media_token_service.py` — Token CRUD, validation, sessions, abuse
- `/app/backend/routes/media_proxy.py` — Streaming, HLS, forensic watermarking
- `/app/backend/routes/media_admin.py` — Admin endpoints
- `/app/backend/routes/viral_ideas_v2.py` — Asset API, URL normalization
- `/app/frontend/src/hooks/useContentProtection.js` — Anti-copy hook
- `/app/frontend/src/components/ContentProtectionWrapper.js` — Route-based wrapper
- `/app/frontend/src/pages/Admin/MediaSecurityDashboard.js` — Admin UI

## What Cannot Be Prevented (by design)
Screenshots, screen recording, OS capture tools, browser extensions, devtools, physical photography.
Goal: friction + entitlement + proxy + traceability. Not fantasy.

## Backlog
- (P2) Personalization and Precomputed Daily Packs
- (P2) Remix Variants and Story Chain leaderboard
- (P2) Admin Dashboard WebSocket upgrades
- (P2) Premium tier download quality/resolution differentiation

## Credentials
- Test: `test@visionary-suite.com` / `Test@2026#`
- Admin: `admin@creatorstudio.ai` / `Cr3@t0rStud!o#2026`
