# Daily Viral Idea Drop — PRD

## Original Problem Statement
Build a "Growth Engine" / "Daily Viral Idea Drop" — queue-driven AI content creation. Never show dead-end UI. Optimize strictly for growth and conversion. Secure all generated media assets behind authenticated proxy with zero raw URL exposure. Apply site-wide anti-copy friction with secure proxy-based asset protection, watermarking, and entitlement enforcement across all pages.

## Core Architecture
- React frontend + FastAPI backend + MongoDB
- 7 background workers + queue abstraction + fallback ladder
- Media Proxy Layer: JWT-signed streaming, watermarking, direct static access blocked
- Site-Wide Content Protection: Reusable hook + wrapper component, route-based activation

## What's Been Implemented

### P0 Fixes (All verified — April 4, 2026)

**1. Generation Blank Screen Bug — FIXED**
**2. Broken Media Assets on Result Page — FIXED**
**3. "Generate Another Pack" Dead Button — FIXED**
**4. Credit Reset to 50 — DONE**
**5. Admin Dashboard — VERIFIED ON PRODUCTION**

### P0 Media Protection Hardening — COMPLETED (April 4, 2026)

**6. Media Proxy & URL Blocking — DONE**
- Created `/api/media/stream/{token}` for JWT-signed asset delivery
- Created `/api/media/download-token` for authenticated downloads
- Blocked direct access to `/api/static/generated/viral_*` (returns 403)
- All file-based assets served via secure_url, file_url stripped from all API responses

**7. URL Prefix Inconsistency Bug — FIXED**
- Added `_is_protected_asset_url()` and `_normalize_asset_url()` to handle both `/api/static/` and `/static/` prefixes
- Full audit: 126/126 assets pass — 66 with secure_url, 60 with content, 0 leaks, 0 misses

**8. Image Watermarking — DONE**
- Preview images served with tiled watermark (user email + job ID), admin exempt

### P0 Site-Wide Anti-Copy Friction Layer — COMPLETED (April 4, 2026)

**9. Reusable Content Protection System — DONE**
- `useContentProtection` hook: right-click blocking, drag prevention on media (img/video/audio/canvas), copy/cut interception, keyboard shortcut blocking (Ctrl+S/C/A/U, PrintScreen), mobile long-press prevention
- `ContentProtectionWrapper` component: applies protection based on route classification
- Smart exemptions: form inputs, textareas, contenteditable, rich text editors (ProseMirror, Quill, CodeMirror, Monaco) remain fully functional
- CSS-level text selection prevention with explicit form element overrides

**10. Route Classification — DONE**
- Protected: All `/app/*` routes (except admin), `/viral/*`, `/share/*`, `/gallery`, `/explore`, `/v/*`, `/character/*`, `/creator/*`, `/series/*`
- Unprotected: `/`, `/login`, `/signup`, `/pricing`, `/contact`, `/reviews`, `/blog`, `/privacy-policy`, `/cookie-policy`, `/terms`, `/user-manual`, `/help`, `/verify-email`, `/reset-password`, `/forgot-password`, `/app/admin/*`

**11. Removed One-Off Patches — DONE**
- Removed duplicate protection code from DailyViralIdeas.js ResultView
- ComixAI.js and GifMaker.js inline `onContextMenu` with toast messages retained (complementary UX)

### What This Protection DOES:
- Blocks right-click context menu on protected surfaces
- Prevents drag-and-drop save of media elements
- Intercepts copy/cut events on non-input elements
- Blocks Ctrl+S, Ctrl+C, Ctrl+A, Ctrl+U, PrintScreen shortcuts
- Reduces mobile long-press save behavior
- Applies CSS user-select:none on protected routes
- Serves all protected media via authenticated proxy (no raw URLs)
- Watermarks preview images with user identity

### What This Protection CANNOT Do (by design):
- Cannot block screenshots or screen recording
- Cannot prevent OS-level capture tools or browser extensions
- Cannot stop physical photography of screens
- Cannot fully prevent devtools/network extraction for determined users

### Full Audit Results
```
Total assets in DB:                126
secure_url present in API:         66 (all media assets)
content present (text-only):       60
file_url leaked:                   0
missing (neither):                 0

Route Protection (tested):
  Protected routes verified:       7 (/app, /app/daily-viral-ideas, /app/story-generator, /app/reel-generator, /gallery, /explore, /viral/*)
  Unprotected routes verified:     8 (/, /login, /signup, /pricing, /contact, /terms, /privacy-policy, /app/admin)
  Form input functionality:        PASS (textarea accepts text on protected pages)
```

## Key Files
- `/app/frontend/src/hooks/useContentProtection.js` — Reusable protection hook
- `/app/frontend/src/components/ContentProtectionWrapper.js` — Route-based wrapper
- `/app/frontend/src/App.js` — Integration point
- `/app/frontend/src/App.css` — CSS protection rules + form exemptions
- `/app/backend/routes/viral_ideas_v2.py` — Asset API, URL normalization
- `/app/backend/routes/media_proxy.py` — Token signing, streaming, watermarking
- `/app/backend/server.py` — Static file blocking middleware
- `/app/backend/tests/test_media_protection.py` — 16 unit tests
- `/app/backend/tests/test_media_protection_api.py` — 14 API integration tests
- `/app/backend/tests/test_content_protection_api.py` — 8 content protection API tests

## Next Priorities (P1 — required for complete asset protection)

### P1 — Entitlement Gating
- Enforce Free vs Paid user download controls on token generation
- Rate limit token generation per user

### P1 — Telemetry for Abuse Detection
- Log repeated token generation per user/IP
- Log abnormal access/download behavior
- Log repeated failed access attempts
- Add admin visibility later

### P1 — Forensic Watermarking
- Add hidden identifiers to downloadable assets (images, video, audio)
- Traceable back to specific user/download event

## Backlog
- (P2) Personalization and Precomputed Daily Packs
- (P2) Remix Variants and Story Chain leaderboard
- (P2) Admin Dashboard WebSocket upgrades

## Credentials
- Test: `test@visionary-suite.com` / `Test@2026#`
- Admin: `admin@creatorstudio.ai` / `Cr3@t0rStud!o#2026`
