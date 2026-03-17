# Visionary Suite — PRD

## Product Vision
AI Creative Operating System: **Create -> Share -> View -> Remix**

### Golden Rules
1. **NO BUTTON SHOULD EXIST IF IT CANNOT GUARANTEE AN OUTPUT.**
2. **A job cannot be READY until the primary preview asset is validated and renderable.**
3. **Frontend must never lie about backend truth.**
4. **One authoritative UI state. No contradictory rendering.**

## UI State Machine (IMPLEMENTED — Photo-to-Comic + Story Video)
```
IDLE → PROCESSING → VALIDATING → READY | PARTIAL_READY | FAILED
```

| uiState | Badge | Download | Share | Preview |
|---|---|---|---|---|
| PROCESSING | Progress bar | Hidden | Disabled | Hidden |
| VALIDATING | "Validating Assets" (amber) | "Verifying..." (disabled) | Disabled | Skeleton |
| READY | "Video/Comic Ready" (green) | Enabled | Enabled | Real image/poster |
| PARTIAL_READY | "Video/Comic Saved" (amber) | Enabled if download_ready | Disabled | Gradient fallback + retry |
| FAILED | "Generation Issue" (red) | Disabled (unless partial assets) | Disabled | Retry/Resume button |

**Contradictory states structurally impossible in code.**

## Asset Truth Model (IMPLEMENTED — Both pipelines)
Backend `/validate-asset` returns separate truth:
```json
{
  "preview_ready": bool,
  "download_ready": bool,
  "share_ready": bool,
  "ui_state": "READY | PARTIAL_READY | FAILED",
  "poster_url": "...",
  "download_url": "...",
  "share_url": "...",
  "stage_detail": "Human-readable status"
}
```

## Story Video Bulletproof Pipeline (IMPLEMENTED — March 17, 2026)
- Strict useReducer state machine in StoryVideoPipeline.js
- Backend `GET /api/pipeline/validate-asset/{job_id}` — granular asset truth
- Separate preview/download/share readiness
- Download button gated: only enabled when `download_ready=true`
- Share buttons gated: only enabled when `share_ready=true`
- Reconnect safety: active jobs detected and resumed on page load
- Duplicate click guard: `createLockRef` prevents double submissions
- Hard 5-minute timeout + 90-second stale detection
- SafeImage for all scene thumbnails (ProgressiveGeneration, StoryPreview, Dashboard)
- ProgressiveGeneration delegates all status transitions to parent (no rogue navigation)
- PARTIAL_READY shows honest "Video saved — preview limited" with download enabled
- FAILED shows real error reason with Resume/Start Over options

## Credits Truth (IMPLEMENTED)
- State initialized to `null` (loading), never `0`
- 3-tier fetch: `/credits/balance` → retry → `/auth/me` fallback
- `isUnlimited` for admin/exempt → bypasses all numeric gates
- Admin shows "Unlimited", never "0"

## SafeImage Component (IMPLEMENTED)
Handles: null, empty, data URIs, placehold.co, broken CDN, CORS failures.
Gradient fallback + title overlay. Deployed on all major surfaces.

## Completed (All Sessions)
1-23. Previous work (resilience, upload, story chains, re-engagement)
24. Credits truth fix + SafeImage component
25. STATE MACHINE FIX: Strict uiState enum for Photo-to-Comic
26. IMAGE FALLBACK SWEEP: onError handlers + gradient fallbacks
27. **STORY VIDEO BULLETPROOF PIPELINE**: Full state machine, validate-asset endpoint, reconnect safety, timeout/stale detection, SafeImage sweep, ProgressiveGeneration fix

## Remaining Backlog
### P0
- [ ] R2 bucket CORS configuration (infra — will move PARTIAL_READY → READY)

### P1
- [ ] Consistent aspect ratios and card sizing across all surfaces
- [ ] Post-generation parity for Story Video (Continue/Remix/Share/View Chain)

### P2
- [ ] Style preset preview thumbnails
- [ ] Cashfree payments (live)
- [ ] Frontend admin dashboard for observability
- [ ] Email Notifications (BLOCKED — SendGrid)

### Blocked
- R2 CORS — requires manual infra config
- SendGrid — requires plan upgrade
