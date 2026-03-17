# Visionary Suite — PRD

## Product Vision
AI Creative Operating System: **Create -> Share -> Remix -> Loop -> Grow -> Measure -> Optimize**

### Golden Rules
1. Every tool output must answer: "What should I do next?"
2. Zero-friction transitions: Click -> Prefill -> Generate.
3. Every shared creation is a user acquisition channel.
4. Growth must be measured, not assumed.
5. The dashboard tells you what to fix, not just what happened.
6. Speed of learning > quality of code. Ship experiments fast.

## Architecture

### Viral Growth Engine
```
User creates -> shares /v/{slug} -> viewer sees A/B-tested conversion page -> clicks CTA
-> auto-prefilled tool -> login (timed by experiment) -> generates -> shares -> loop
```

### A/B Testing System (NEW)
```
Session -> deterministic hash -> variant assignment (cached in sessionStorage)
Experiments: cta_copy, hook_text, login_timing
Events tracked: remix_click, generate_click, signup_completed, share_click
Winner heuristic: 20%+ uplift after 200 sessions per variant
Dashboard: /app/admin/growth -> A/B Experiments section
```

### Growth Intelligence System
```
Events: page_view -> remix_click -> tool_open_prefilled -> generate_click -> signup -> creation -> share
Metrics: Conversion rates at each stage, K factor, drop-off detection, auto-diagnosis
Alerts: Threshold-based (remix <5%, signup <10%, etc.)
Dashboard: /app/admin/growth
```

### Self-Defending Infrastructure
- Regression Suite: 35 tests | Watchdog: Auto every 5 min | Health: /api/health/deep
- Confidence Score: /api/watchdog/confidence

### Payment System (Cashfree)
- Status: Production, fully wired | Products: 5 | Currency: INR
- Flow: Billing -> create-order -> Cashfree SDK -> verify -> credits

## Production UAT History
- Iteration 301: PRODUCTION GO (Backend 94%, Frontend 100%)
- Iteration 302: Growth Intelligence (Backend 36/36, Frontend 17/17)
- Iteration 303: A/B Testing System (Backend 26/26 - 100%)

## Completed Work
1-31. Core platform + Stability + Self-defending + Original UAT
32. Story Video Post-Gen Parity
33. Next Action Hooks — ALL 9 tools
34. Cross-Tool Auto-Prefill — useRemixData + RemixBanner + TTL
35. Share -> Remix Growth Loop — Public conversion funnel
36. Cashfree E2E Verification
37. Story Video Quality — Prompt engineering
38. Growth Analytics — Full event tracking pipeline + viral K
39. Full Platform UAT — PRODUCTION GO APPROVED
40. Growth Intelligence Dashboard
41. **Lean A/B Testing System** (Feb 2026):
    - Backend: POST /api/ab/assign, /api/ab/assign-all, /api/ab/convert, GET /api/ab/results
    - 3 experiments seeded: CTA Copy, Hook Text, Login Gate Timing
    - Deterministic session-based variant assignment (MD5 hash)
    - Conversion tracking with deduplication
    - Winner heuristic: 20%+ uplift after 200 sessions
    - Frontend: PublicCreation.js renders A/B variants for hook + CTA copy
    - Login gate timing: before_generate (-> /signup), after_generate (-> tool), after_preview (-> preview section)
    - Growth Dashboard: A/B Experiments section with per-variant results table
    - Testing: iteration_303 — Backend 100% (26/26)

## Active A/B Experiments
1. **cta_copy** — Primary: remix_click
   - cta_a: "Create This in 1 Click"
   - cta_b: "Make Your Own Now"
   - cta_c: "Generate This in Seconds"
2. **hook_text** — Primary: remix_click
   - hook_a: "Made in 30 seconds. No skills needed."
   - hook_b: "This video was created with AI — try it yourself."
   - hook_c: "Anyone can make this. Click and see."
3. **login_timing** — Primary: signup_completed
   - gate_before: Send to /signup immediately
   - gate_after: Navigate to tool (auth redirect)
   - gate_preview: Show preview section on page

## Remaining Backlog
### P0
- [ ] CTA Placement experiment (after first 3 experiments are running)
- [ ] Monitor experiment data, declare winners when 200+ sessions reached

### P1
- [ ] UI Consistency (aspect ratios, card sizing, grid alignment)

### P2
- [ ] Style preset preview thumbnails for Photo-to-Comic
- [ ] Admin Observability Dashboard (health/watchdog visualization)
- [ ] Cashfree: Enable USD on merchant

### Future
- [ ] Export Packs (Instagram, etc.)

### Blocked
- R2 CORS — infra config (graceful fallback in place)
- SendGrid — plan upgrade
