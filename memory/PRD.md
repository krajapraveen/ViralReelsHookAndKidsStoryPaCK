# Visionary Suite — PRD

## Product Vision
AI Creative Operating System: **Create -> Share -> View -> Remix -> Loop**

### Golden Rules
1. NO BUTTON SHOULD EXIST IF IT CANNOT GUARANTEE AN OUTPUT.
2. A job cannot be READY until the primary preview asset is validated.
3. Frontend must never lie about backend truth.
4. One authoritative UI state. No contradictory rendering.
5. Credits must NEVER show 0 due to loading or API failure.
6. Tests catch regressions. Health checks catch failures. Watchdog heals. Alerts notify.
7. **Every tool output screen must answer: "What should I do next?"**
8. **No tool should end in a dead-end state.**

## Self-Defending Infrastructure
- Regression Suite: 35 tests, run before/after every change
- Deep Health: `GET /api/health/deep`
- Watchdog: Auto every 5 min, SLA guardrails, max 3 retries, structured logs
- Alerts: Auto-triggers watchdog on critical issues
- Confidence Score: `GET /api/watchdog/confidence` (0-100)

## Engagement Loop Architecture
Every tool now follows the engagement loop pattern:
```
User -> Create -> [PRIMARY ACTION ZONE] -> Continue/Remix/Convert/Expand -> Create -> Loop
```

### Tool-Level Hook Coverage:
| Tool | Continue | Remix | Convert | Expand | Share |
|------|----------|-------|---------|--------|-------|
| Photo-to-Comic | 5 Directions | Style Swatches | Video, GIF | Story Chain | Copy/Twitter/WA |
| Story Video | 5 Directions | 6 Style Swatches | Comic, GIF | Story Chain | Copy/Twitter/WA |
| GIF Maker | Emotion Switch | Style Switch | Comic, Video, Reel | - | Copy/Share |
| Reel Generator | Tone Switch | - | Video, Comic, Story | Expand to Story | Copy/Share |
| Comic Storybook | Next Chapter | Art Style | Video, Bedtime | - | ShareCreation |
| Bedtime Story | Next Episode | Narration | Video, Comic | - | - |
| Caption Rewriter | Tone Switch | - | Reel, Video, Script | Expand Script | - |
| Brand Story | Website Copy | - | Reel, Video, Social | Expand Copy | - |
| Daily Viral Ideas | - | - | Reel, Video, Comic, Caption | - | Copy |

## Full Platform UAT Status (March 17, 2026)
### ALL 13 SECTIONS PASS (from previous UAT)

## Completed Work (All Sessions)
1-26. Core platform + Credits truth + SafeImage + State machines
27. Story Video Bulletproof Pipeline
28. Full Platform Hardening (all-module UAT, SafeImage sweep)
29. Self-Defending Infrastructure (regression, health, watchdog, alerts)
30. Continuous Self-Healing (scheduled watchdog, logs, alert-action coupling, SLA, confidence)
31. Full-Depth Destructive UAT (all 13 sections verified, zero critical issues)
32. **Story Video Post-Generation Parity** (Feb 2026) — Rich engagement loop with 5 Continue Directions, Visual Style Remix, Story Chain
33. **Next Action Hooks Across ALL Tools** (Feb 2026) — Reusable NextActionHooks component deployed to all 7 remaining tools:
    - GIF Maker: Try Different Reaction, Turn Into Comic, Create Story Video, Make a Reel Script
    - Reel Generator: Generate Video, Rewrite Different Tone, Expand Into Story, Turn Into Comic
    - Comic Storybook: Add Next Chapter, Change Art Style, Convert to Video, Make Bedtime Story
    - Bedtime Story: Convert to Video, Next Episode, Change Narration, Create Illustrations
    - Caption Rewriter: Generate Reel Script, Rewrite Again, Expand to Full Script, Create Story Video
    - Brand Story: Create Reel Script, Generate Video Ad, Expand Website Copy, Create Social Series
    - Daily Viral Ideas: Generate Reel Script, Create Story Video, Generate Captions, Make a Comic
    - Testing: iteration_298 — all pages load, hooks verified, bug fixed (CaptionRewriter selectedPack)

## Remaining Backlog
### P0
- [ ] R2 bucket CORS configuration (infra)

### P1
- [x] ~~Post-generation parity for Story Video~~ DONE
- [x] ~~Next Action Hooks across ALL tools~~ DONE
- [ ] UI Consistency (aspect ratios, card sizing, grid alignment)

### P2
- [ ] Style preset preview thumbnails for Photo-to-Comic
- [ ] Admin dashboard for observability APIs (health, watchdog, alerts, confidence)
- [ ] Cashfree payments (live — depends on traffic)
- [ ] Email Notifications (BLOCKED — SendGrid)

### Future (Growth & Viral)
- [ ] Viral growth loop design (create -> share -> new users -> create)
- [ ] Instant Preview Mode for comics
- [ ] Export Packs (Instagram, etc.)
- [ ] Cross-tool remix data consumption (tools reading localStorage remix_data on load)

### Blocked
- R2 CORS — infra config
- SendGrid — plan upgrade
