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
9. **Zero-friction transitions: Click → Prefill → Generate. No thinking. No typing.**

## Self-Defending Infrastructure
- Regression Suite: 35 tests
- Deep Health: `GET /api/health/deep`
- Watchdog: Auto every 5 min, SLA guardrails
- Alerts + Confidence Score

## Engagement Loop Architecture
Every tool now follows the engagement loop pattern:
```
User -> Create -> [PRIMARY ACTION ZONE] -> Continue/Remix/Convert/Expand -> Create -> Loop
```

### Cross-Tool Auto-Prefill System
```
Tool A (hook click) → localStorage.remix_data (with timestamp) → Tool B → useRemixData hook → mapRemixToFields → Prefill inputs → RemixBanner("Prefilled from Tool A") → Clear localStorage
```
- TTL: 10 minutes
- Single consumption: cleared after first read
- Type validation: field mapping per target tool
- Visual: amber "Prefilled from..." banner with dismiss

### Tool-Level Coverage:
| Tool | Hooks | Prefill Consumer | RemixBanner |
|------|-------|-----------------|-------------|
| Photo-to-Comic | Custom (5 dir + style swatches) | N/A (image-based) | N/A |
| Story Video | Custom (5 dir + 6 styles) | Yes (remix_data + remix_video) | Yes |
| GIF Maker | 4 hooks | Yes (emotion, style, bg) | Yes |
| Reel Generator | 4 hooks | Yes (topic, niche, tone, duration) | Yes |
| Comic Storybook | 4 hooks | Yes (storyIdea, genre) | Yes |
| Bedtime Story | 4 hooks | Yes (theme, ageGroup, moral) | Yes |
| Caption Rewriter | 4 hooks | Yes (text, tone) | Yes |
| Brand Story | 4 hooks | Yes (mission, industry, tone) | Yes |
| Daily Viral Ideas | 4 hooks | N/A (display only) | N/A |

## Completed Work (All Sessions)
1-31. Core platform + Stability + Self-defending infrastructure + Full UAT
32. Story Video Post-Generation Parity — Rich engagement loop
33. Next Action Hooks Across ALL Tools — 7 tools with 4 hooks each
34. **Cross-Tool Auto-Prefill** (Feb 2026) — Zero-friction transitions:
    - Created `useRemixData` hook with TTL (10min), type validation, auto-clear
    - Created `RemixBanner` component ("Prefilled from [Tool] — [Title]")
    - Updated `NextActionHooks` to include timestamp in payload
    - Integrated consumption in 8 tools: Story Video, Reel Generator, GIF Maker, Comic Storybook, Bedtime Story, Caption Rewriter, Brand Story (+ Daily Viral Ideas has hooks but no prefill since display-only)
    - Testing: iteration_299 — Backend 100% (12/12), Frontend 100% (all pages load, all remix features verified)

## Remaining Backlog
### P0
- [ ] R2 bucket CORS configuration (infra)

### P1
- [x] ~~Post-generation parity for Story Video~~ DONE
- [x] ~~Next Action Hooks across ALL tools~~ DONE
- [x] ~~Cross-tool auto-prefill~~ DONE
- [ ] UI Consistency (aspect ratios, card sizing, grid alignment)

### P2
- [ ] Style preset preview thumbnails for Photo-to-Comic
- [ ] Admin dashboard for observability APIs (health, watchdog, alerts, confidence)
- [ ] Cashfree payments (live — depends on traffic)
- [ ] Email Notifications (BLOCKED — SendGrid)

### Future (Growth & Viral)
- [ ] Viral growth loop (create → share → new users → create)
- [ ] Instant Preview Mode for comics
- [ ] Export Packs (Instagram, etc.)

### Blocked
- R2 CORS — infra config
- SendGrid — plan upgrade
