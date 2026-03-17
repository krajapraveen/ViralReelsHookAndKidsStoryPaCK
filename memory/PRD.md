# Visionary Suite — PRD

## Product Vision
AI Creative Operating System: **Create -> Share -> Remix -> Loop -> Grow -> Measure**

### Golden Rules
1. NO BUTTON SHOULD EXIST IF IT CANNOT GUARANTEE AN OUTPUT.
2. Frontend must never lie about backend truth.
3. Every tool output must answer: "What should I do next?"
4. Zero-friction transitions: Click → Prefill → Generate.
5. Every shared creation is a user acquisition channel.
6. Growth must be measured, not assumed.

## Architecture

### Viral Growth Engine
```
User creates → shares public link (/v/{slug}) → viewer sees conversion page
→ clicks "Remix This" → auto-prefilled tool → login (soft gate)
→ generates → shares → next viewer → loop
```

### Growth Analytics Pipeline
```
Events tracked: page_view → remix_click → tool_open_prefilled → generate_click → signup_completed → creation_completed → share_click
Endpoints: /api/growth/event, /events/batch, /metrics, /funnel, /viral-coefficient, /trends
Viral Coefficient: K = avg_shares_per_user × conversion_rate_per_share
```

### Self-Defending Infrastructure
- Regression Suite: 35 tests
- Watchdog: Auto every 5 min, self-healing
- Health: /api/health, /api/health/deep
- Confidence Score: /api/watchdog/confidence

### Payment System (Cashfree)
- Status: Production, fully wired
- Products: 5 (2 subs + 3 top-ups)
- Currency: INR
- Flow: Billing → create-order → Cashfree SDK → verify → credits

## Full Platform UAT (Feb 2026 — Iteration 301)
### PRODUCTION GO DECISION: APPROVED
| Module | Status | Tests |
|--------|--------|-------|
| All 9 Tools | PASS | 14 pages load clean |
| Public Conversion Funnel | PASS | All 12 elements verified |
| Cashfree Payment | PASS | 6/6 |
| Growth Analytics | PASS | 6/6 |
| Cross-Tool Prefill | PASS | Verified iteration 299 |
| Next Action Hooks | PASS | Verified iteration 298 |
| Downloads & Gallery | PASS | 2/2 |
| Credits & Billing | PASS | 2/2 |
| Edge Cases | PASS | 3/3 (422 on invalid, auth) |
| Navigation | PASS | 2/2 |
| **Overall Backend** | **94%** | 34/36 |
| **Overall Frontend** | **100%** | All pages verified |

## Completed Work (All Sessions)
1-31. Core platform + Stability + Self-defending + Original UAT
32. Story Video Post-Gen Parity
33. Next Action Hooks — ALL 9 tools
34. Cross-Tool Auto-Prefill — useRemixData + RemixBanner
35. Share → Remix Growth Loop — Public conversion funnel
36. Cashfree E2E Verification
37. Story Video Quality — Prompt engineering for character consistency
38. **Growth Analytics Tracking** (Feb 2026):
    - Backend: growth_events collection + 6 API endpoints
    - Frontend: growthAnalytics.js with batched event tracking
    - Funnel: page_view → remix_click → tool_open → generate → signup → creation
    - Viral coefficient: K = shares × conversion
    - Integrated in: PublicCreation, useRemixData, Signup
39. **Full Platform UAT** (Feb 2026):
    - Production Go Decision: APPROVED
    - Backend 94% (34/36), Frontend 100%
    - Zero critical issues, zero blocking issues

## Remaining Backlog
### P1
- [ ] UI Consistency (aspect ratios, card sizing, grid alignment)

### P2
- [ ] Style preset preview thumbnails for Photo-to-Comic
- [ ] Admin Observability Dashboard (health/watchdog/alerts/confidence UI)
- [ ] Growth Analytics Dashboard (funnel visualization, K tracking)

### Future
- [ ] Cashfree: Enable USD on merchant
- [ ] Viral growth loop optimization (A/B test CTAs, landing pages)
- [ ] Export Packs (Instagram, etc.)

### Blocked
- R2 CORS — infra config (graceful fallback in place)
- SendGrid — plan upgrade
