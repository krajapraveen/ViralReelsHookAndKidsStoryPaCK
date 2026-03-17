# Visionary Suite — PRD

## Product Vision
AI Creative Operating System: **Create -> Share -> Remix -> Loop -> Grow -> Measure -> Optimize**

### Golden Rules
1. Every tool output must answer: "What should I do next?"
2. Zero-friction transitions: Click → Prefill → Generate.
3. Every shared creation is a user acquisition channel.
4. Growth must be measured, not assumed.
5. The dashboard tells you what to fix, not just what happened.

## Architecture

### Viral Growth Engine
```
User creates → shares /v/{slug} → viewer sees conversion page → clicks Remix
→ auto-prefilled tool → login (soft gate) → generates → shares → loop
```

### Growth Intelligence System
```
Events: page_view → remix_click → tool_open_prefilled → generate_click → signup → creation → share
Metrics: Conversion rates at each stage, K factor, drop-off detection, auto-diagnosis
Alerts: Threshold-based (remix <5%, signup <10%, etc.)
Dashboard: /app/admin/growth — "Where are users dropping? What to fix next."
```

### Self-Defending Infrastructure
- Regression Suite: 35 tests | Watchdog: Auto every 5 min | Health: /api/health/deep
- Confidence Score: /api/watchdog/confidence

### Payment System (Cashfree)
- Status: Production, fully wired | Products: 5 | Currency: INR
- Flow: Billing → create-order → Cashfree SDK → verify → credits

## Production UAT History
- Iteration 301: PRODUCTION GO — APPROVED (Backend 94%, Frontend 100%)
- Iteration 302: Growth Intelligence — 100% (Backend 36/36, Frontend 17/17)

## Completed Work
1-31. Core platform + Stability + Self-defending + Original UAT
32. Story Video Post-Gen Parity — 5 directions + 6 style swatches
33. Next Action Hooks — ALL 9 tools with engagement loops
34. Cross-Tool Auto-Prefill — useRemixData + RemixBanner + TTL
35. Share → Remix Growth Loop — Public conversion funnel
36. Cashfree E2E Verification
37. Story Video Quality — Prompt engineering for character consistency
38. Growth Analytics — Full event tracking pipeline + viral K
39. Full Platform UAT — PRODUCTION GO APPROVED
40. **Growth Intelligence Dashboard** (Feb 2026):
    - Funnel visualization with conversion % and BIGGEST DROP detection
    - Viral K badge (WEAK/CLOSE/VIRAL) with interpretation
    - Growth Alerts with threshold-based auto-diagnosis
    - Top Performing Content by remix rate
    - Daily Trends table
    - Period selector (7d/14d/30d)
    - Testing: iteration_302 — Backend 100% (36/36), Frontend 100% (17/17)

## Remaining Backlog
### P1
- [ ] UI Consistency (aspect ratios, card sizing, grid alignment)
- [ ] A/B Testing System (CTA variations on public pages)

### P2
- [ ] Style preset preview thumbnails for Photo-to-Comic
- [ ] Admin Observability Dashboard (health/watchdog visualization)
- [ ] Cashfree: Enable USD on merchant

### Future
- [ ] Funnel drop-off optimization (data-driven CTA changes)
- [ ] Export Packs (Instagram, etc.)

### Blocked
- R2 CORS — infra config (graceful fallback in place)
- SendGrid — plan upgrade
