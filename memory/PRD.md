# Visionary Suite — PRD

## Product Vision
AI Creative Operating System: **Create -> Share -> View -> Remix**

### Golden Rules
1. **NO BUTTON SHOULD EXIST IF IT CANNOT GUARANTEE AN OUTPUT.**
2. **A job cannot be READY until the primary preview asset is validated and renderable.**
3. **Frontend must never lie about backend truth.**
4. **One authoritative UI state. No contradictory rendering.**

## UI State Machine (IMPLEMENTED)
```
IDLE → PROCESSING → VALIDATING → READY | PARTIAL_READY | FAILED
```

| uiState | Badge | Download | Share | Preview |
|---|---|---|---|---|
| PROCESSING | Progress bar | Hidden | Disabled | Hidden |
| VALIDATING | "Validating Assets" (amber) | "Verifying..." (disabled) | Disabled | Skeleton |
| READY | "Comic Ready" (green) | "Download PNG" (enabled) | Enabled | Real image |
| PARTIAL_READY | "Comic Saved" (amber) | Enabled if download_ready | Disabled | Gradient fallback + retry |
| FAILED | "Generation Issue" (red) | Disabled | Disabled | Retry button |

**Contradictory states structurally impossible in code.**

## Asset Truth Model (IMPLEMENTED)
Backend `/validate-asset` returns separate truth:
```json
{
  "download_ready": true,   // URL exists in DB → download will work
  "preview_ready": false,   // CDN HEAD check failed → preview broken
}
```
Frontend `resolveAssetState()`:
1. Tests preview renderability (loads image, 8s timeout)
2. Gets download_ready + preview_ready from backend
3. Both pass → READY. Download-only → PARTIAL_READY. Both fail → FAILED.

## Credits Truth (IMPLEMENTED)
- State initialized to `null` (loading), never `0`
- 3-tier fetch: `/credits/balance` → retry → `/auth/me` fallback
- `isUnlimited` for admin/exempt → bypasses all numeric gates
- Admin shows "∞", never "0"

## SafeImage Component (IMPLEMENTED)
Handles: null, empty, data URIs, placehold.co, broken CDN, CORS failures.
Gradient fallback + title overlay. No crossOrigin on data URIs. Deployed on all story chain surfaces.

## Image Fallback Sweep (IMPLEMENTED)
onError handlers on img tags in: Dashboard, Landing, ExplorePage, Gallery, CreatorProfile.
Failed images hidden, gradient fallback shown. Zero broken image icons.

## Generation Pipeline Safety (IMPLEMENTED)
- Stale-job detection (60s) → "Taking longer than usual"
- Hard 3-minute timeout
- Real errors on FAILED status

## Completed (All Sessions)
1-23. Previous work (resilience, upload, story chains, re-engagement)
24. Credits truth fix + SafeImage component
25. **STATE MACHINE FIX**: Strict uiState enum, separate preview/download truth, no contradictory states, asset readiness gate
26. **IMAGE FALLBACK SWEEP**: onError handlers on 5 high-visibility pages, gradient fallbacks everywhere

## Remaining Backlog
### P0
- [ ] R2 bucket CORS configuration (infra — will move PARTIAL_READY → READY for new generations)

### P1
- [ ] Downloads page: only show assets with status=READY
- [ ] Story Video chain view page
- [ ] Video chains in Resume drawer

### P2
- [ ] Style preset preview thumbnails
- [ ] Cashfree payments (live)
- [ ] Frontend admin dashboard for observability + metrics
- [ ] Email Notifications (BLOCKED — SendGrid)
