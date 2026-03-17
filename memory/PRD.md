# Visionary Suite — PRD

## Product Vision
AI Creative Operating System: **Create -> Share -> View -> Remix**
Every output is a permanent CDN-backed asset. Every creation is a living object, not a one-time result.

### Golden Rule
> **NO BUTTON SHOULD EXIST IF IT CANNOT GUARANTEE AN OUTPUT.**
> A job cannot be READY until the primary preview asset is validated and renderable.
> Frontend must never lie about backend truth.

## UI State Machine (IMPLEMENTED — March 2026)

### Job UI States
```
IDLE → PROCESSING → VALIDATING → READY | PARTIAL_READY | FAILED
```

### Rendering Rules
| uiState | Badge | Download | Share | Preview |
|---|---|---|---|---|
| PROCESSING | Progress bar | Hidden | Disabled | Hidden |
| VALIDATING | "Validating Assets" (amber) | "Verifying..." (disabled) | Disabled | Skeleton |
| READY | "Comic Ready" (green) | "Download PNG" (enabled) | Enabled | Real image |
| PARTIAL_READY | "Comic Saved" (amber) | Enabled if download ok | Disabled | Gradient fallback + retry |
| FAILED | "Generation Issue" (red) | Disabled | Disabled | Retry button |

### Asset State Resolution
`resolveAssetState()` determines final uiState by:
1. Testing preview renderability (loads image, 8s timeout)
2. Validating download via backend API
3. Both must pass for READY. Download-only = PARTIAL_READY. Both fail = FAILED.

**It is structurally impossible for "Comic Ready" and "Verifying..." to appear simultaneously.**

## SafeImage Component (IMPLEMENTED)
Bulletproof image renderer. Handles: null, empty, data URIs, placehold.co, broken CDN, CORS failures.
- Gradient fallback with title overlay (no crossOrigin on data URIs)
- Locked aspect ratios, skeleton loading
- Deployed on ALL user-facing surfaces

## Credits Truth (IMPLEMENTED)
- State initialized to `null` (loading), never `0`
- 3-tier fetch: `/credits/balance` → retry → `/auth/me` fallback
- `isUnlimited` for admin/exempt — bypasses all numeric gates
- Admin shows "∞", never "0"

## Generation Pipeline Safety (IMPLEMENTED)
- Stale-job detection: 60s no progress → "Taking longer than usual"
- Hard 3-minute timeout (90 polls × 2s)
- Real error messages on FAILED
- Stage-based progress from backend

## Re-Engagement System (IMPLEMENTED)
- Login Interstitial, Action Banner, Active Chains Nav Chip + Resume Drawer
- Momentum Messaging, Metrics Instrumentation (6 key metrics)

## Story Chain Progression (IMPLEMENTED)
- Progress indicators, AI suggestions (context-aware, validated, cached)
- Direction-based continuation, Story Video chain model

## 5-Layer Resilience Architecture (IMPLEMENTED)
- Idempotency, Cost Guardrails, Tier-Aware Degradation, Multi-Queue, Observability

## Completed (All Sessions)
1-23. [Previous work]
24. Trust Repair: Credits truth, SafeImage, generation polling safety
25. **STATE MACHINE FIX**: Strict uiState enum replacing independent booleans. Contradictory states impossible. Preview/download truth separated. Asset readiness gate before success UI.

## Remaining Backlog
### P0
- [ ] Configure R2 bucket CORS (fixes CDN image CORS → moves PARTIAL_READY to READY for new generations)

### P1
- [ ] Sweep remaining raw img tags (explore, creator profiles, landing, downloads)
- [ ] Download button only when asset.status === READY (backend enforcement)
- [ ] Story Video chain view page
- [ ] Video chains in Resume drawer

### P2
- [ ] Style preset preview thumbnails
- [ ] Cashfree payments (live)
- [ ] Frontend admin dashboard for observability + metrics
- [ ] Email Notifications (BLOCKED — SendGrid)
