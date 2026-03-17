# Visionary Suite — PRD

## Product Vision
AI Creative Operating System: **Create -> Share -> View -> Remix**

### Golden Rules
1. NO BUTTON SHOULD EXIST IF IT CANNOT GUARANTEE AN OUTPUT.
2. A job cannot be READY until the primary preview asset is validated.
3. Frontend must never lie about backend truth.
4. One authoritative UI state. No contradictory rendering.
5. Credits must NEVER show 0 due to loading or API failure.
6. Tests catch regressions. Health checks catch failures. Watchdog heals. Alerts notify.

## Self-Defending Infrastructure
- Regression Suite: 35 tests, run before/after every change
- Deep Health: `GET /api/health/deep`
- Watchdog: Auto every 5 min, SLA guardrails, max 3 retries, structured logs
- Alerts: Auto-triggers watchdog on critical issues
- Confidence Score: `GET /api/watchdog/confidence` (0-100)

## Full Platform UAT Status (March 17, 2026)
### ALL 13 SECTIONS PASS:
| Section | Status | Key Verifications |
|---|---|---|
| Navigation | PASS | Logo, nav links, credits, profile, logout |
| Dashboard | PASS | Quick create, prompts, More Tools (8 cards), credits |
| Story Video | PASS | Full state machine, 6 styles, validate-asset, postgen engagement loop |
| Photo to Comic | PASS | Upload, history, validate-asset truth |
| Comic Storybook | PASS | 5-step wizard, 8 genres, credits |
| Reel Generator | PASS | All form fields, 422 on empty |
| GIF Maker | PASS | 4-step wizard, emotions, credits |
| Bedtime Story | PASS | 4-step wizard, 422 on empty |
| My Downloads | PASS | Only ready assets, download URLs valid |
| Gallery/Explore | PASS | 58 items, SafeImage, filters |
| Credits All Pages | PASS | on Dashboard, P2C, CSB, Reel, GIF |
| UI Alignment | PASS | Cards uniform, grids aligned |
| Admin Panel | PASS | 18 sections, stats, charts |
| Health/Watchdog | PASS | All endpoints operational |
| My Stories | PASS | 8 chains, SafeImage fallbacks |

### Test Infrastructure:
- Regression: 35/35 PASS
- Full UAT: 38/41 backend (93%), 100% frontend
- Watchdog: Healthy, 0 active alerts
- Confidence: 70/100 (good, improving)

## Completed Work (All Sessions)
1-26. Core platform + Credits truth + SafeImage + State machines
27. Story Video Bulletproof Pipeline
28. Full Platform Hardening (all-module UAT, SafeImage sweep)
29. Self-Defending Infrastructure (regression, health, watchdog, alerts)
30. Continuous Self-Healing (scheduled watchdog, logs, alert-action coupling, SLA, confidence)
31. Full-Depth Destructive UAT (all 13 sections verified, zero critical issues)
32. **Story Video Post-Generation Parity** (Feb 2026) — Rich engagement loop:
    - 5 Continue Directions (Continue, Plot Twist, Raise Stakes, New Episode, Custom)
    - Visual Style Remix swatches (6 animation styles)
    - Story Chain link
    - Cross-tool conversions via CreationActionsBar
    - All verified by testing agent (iteration 297)

## Remaining Backlog
### P0
- [ ] R2 bucket CORS configuration (infra)

### P1
- [ ] Consistent aspect ratios and card sizing refinement
- [x] ~~Post-generation parity for Story Video (Continue/Remix/Share)~~ DONE

### P2
- [ ] Style preset preview thumbnails for Photo-to-Comic
- [ ] Admin dashboard for observability APIs (health, watchdog, alerts, confidence)
- [ ] Cashfree payments (live)
- [ ] Email Notifications (BLOCKED — SendGrid)

### Future (Engagement Loop Expansion)
- [ ] "Next Action Hooks" on ALL generation tools (not just Story Video)
- [ ] Instant Preview Mode for comics
- [ ] Export Packs (Instagram, etc.)
- [ ] Viral growth loop (create -> share -> new users -> create)

### Blocked
- R2 CORS — infra config
- SendGrid — plan upgrade
