# Story Universe Engine — Product Requirements Document

## Original Problem Statement
Build a "Story Universe Engine" — a full-stack AI creator suite with a behavior-driven growth engine, monetization, and viral sharing. Core mandate: Netflix-level media delivery, deterministic personalization, addictive hook system, and a complete dopamine loop.

## Core Architecture
- Frontend: React (CRA + Craco) on port 3000
- Backend: FastAPI on port 8001
- Database: MongoDB (creatorstudio_production)
- Storage: Cloudflare R2
- Payments: Cashfree
- AI: OpenAI GPT-4o-mini, Sora 2, TTS + Gemini 3 via Emergent LLM Key

## Entitlement-Based Media Access (BUILT Mar 31 2026)

### Business Rules
- **Free users**: Preview only. Cannot download. See "Upgrade to Download" CTA.
- **Active paid subscribers** (starter/pro/premium with active subscription): Full download via short-lived presigned URLs.
- **Top-up credits alone** WITHOUT active subscription: Does NOT unlock download.
- **Admin/Superadmin**: Full access override.

### Architecture
```
Backend (Source of Truth):
  /api/media/entitlement       — Returns can_download, upgrade_required flags
  /api/media/download-token/   — Returns 60-sec presigned URL (paid) or 403 (free)
  /api/story-engine/status/    — Scrubs output_url for free users
  /api/story-engine/user-jobs  — Scrubs output_url for free users

Frontend (Renders from Backend Truth):
  MediaEntitlementContext       — Caches entitlement flags
  EntitledDownloadButton        — Full download button with gating
  EntitledDownloadIcon          — Compact lock/download icon for cards
```

### All Gated Download Surfaces
| Surface | Component | Gated |
|---------|-----------|-------|
| Story Video Pipeline | EntitledDownloadButton | Yes |
| My Space cards | EntitledDownloadIcon | Yes |
| Story Preview | EntitledDownloadButton | Yes |
| Browser Video Export | useMediaEntitlement | Yes |
| Video Export Panel | useMediaEntitlement | Yes |
| My Downloads | useMediaEntitlement | Yes |
| Smart Download | useMediaEntitlement | Yes |
| Social Share Download | useMediaEntitlement | Yes |
| Protected Content | useMediaEntitlement | Yes |
| Force Share Gate | No downloadUrl passed | Yes |
| Share Reward Bar | No downloadUrl passed | Yes |

### CTA Copy
- Button: "Upgrade to Download"
- Tooltip: "Downloads are available on paid plans"

## Branding Cleanup (DONE Mar 31 2026)
- All visible "Emergent" / "Powered by Emergent" branding removed from user-facing UI
- CSS + MutationObserver in index.html suppresses any platform-injected badges
- PrivacyPolicy.js: "Emergent Auth" reference replaced with generic "OAuth 2.0"
- Platform scripts (emergent-main.js) are functional infrastructure and remain for deployment

## Navigation Structure
```
/app/my-space, /app/create, /app/browse, /app/characters, /app/dashboard
```

## Quality Modes
| Mode | Max Scenes | ETA | Use Sora |
|------|-----------|-----|----------|
| Fast | 3 | 1-2 min | No |
| Balanced | 5 | 2-4 min | Yes |
| High Quality | 7 | 4-8 min | Yes |

## Test Credentials
- Test User: test@visionary-suite.com / Test@2026# (free plan)
- Admin User: admin@creatorstudio.ai / Cr3@t0rStud!o#2026 (admin role)

## Completed (This Session — Mar 31 2026)
- [x] P0 Media Entitlement Gating — 16/16 backend tests, 100% frontend verification
- [x] Branding removal — 0 Emergent/Powered by visible across all pages

## Upcoming
- (P1) Anti-crop watermark improvements (dynamic per-user watermarks)
- (P1) Telemetry pipeline for abnormal access patterns
- (P1) Notification Center Improvements
- (P1) A/B test hook text on public pages

## Future/Backlog
- (P2) Invisible forensic watermarking
- (P2) Admin leak dashboard
- (P2) Remix Variants, Story Chain leaderboard
- (P2) Admin dashboard WebSocket upgrade
