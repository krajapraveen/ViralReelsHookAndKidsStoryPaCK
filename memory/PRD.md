# Visionary Suite — PRD

## Product Vision
AI Creative Operating System: **Create -> Share -> Remix -> Loop -> Grow**

### Golden Rules
1. NO BUTTON SHOULD EXIST IF IT CANNOT GUARANTEE AN OUTPUT.
2. A job cannot be READY until the primary preview asset is validated.
3. Frontend must never lie about backend truth.
4. Every tool output must answer: "What should I do next?"
5. No tool should end in a dead-end state.
6. Zero-friction transitions: Click → Prefill → Generate.
7. Every shared creation is a user acquisition channel.
8. Credits must NEVER show 0 due to loading or API failure.

## Architecture: Viral Growth Loop
```
User creates → shares public link → viewer sees conversion page
→ clicks "Remix This" → auto-prefilled tool → login (soft gate)
→ generates own version → shares → next viewer → loop
```

### Public Page = Conversion Funnel (/v/{slug})
- Above-fold viral hook: "Created using AI in seconds"
- PRIMARY CTA: "Remix This" (gradient, prominent)
- SECONDARY CTA: "Try This Exact Prompt" (1-click)
- TERTIARY CTA: "Create Your Own" (fresh start)
- Social proof: views + remix count (loud)
- Prompt display: shows exact prompt used
- CTA branding footer: "Create yours → visionary-suite.com"
- Share menu: X/Twitter, LinkedIn, WhatsApp, Reddit, Copy
- Multi-tool routing: detects tool_type → routes to correct tool
- Auto-prefill: stores remix_data + remix_return_url in localStorage
- No login wall: remix click → tool → prefilled → THEN soft login gate

### Cross-Tool Auto-Prefill System
```
Tool A hook → localStorage.remix_data (timestamp) → Tool B → useRemixData → mapRemixToFields → Prefill → RemixBanner → Clear
```
- TTL: 10 minutes | Single consumption | Type validation per tool

### Tool Coverage
| Tool | Hooks | Prefill | Banner | Public Remix |
|------|-------|---------|--------|-------------|
| Story Video | 5 dirs + 6 styles | Yes | Yes | Yes |
| Photo-to-Comic | 5 dirs + style swatches | N/A (image) | N/A | Yes |
| GIF Maker | 4 hooks | Yes | Yes | Yes |
| Reel Generator | 4 hooks | Yes | Yes | Yes |
| Comic Storybook | 4 hooks | Yes | Yes | Yes |
| Bedtime Story | 4 hooks | Yes | Yes | Yes |
| Caption Rewriter | 4 hooks | Yes | Yes | Yes |
| Brand Story | 4 hooks | Yes | Yes | Yes |
| Daily Viral Ideas | 4 hooks | N/A | N/A | N/A |

## Cashfree Payment System
- **Status**: Fully wired, PRODUCTION mode
- **Products**: 5 (2 subscriptions + 3 top-ups)
- **Currency**: INR (USD not enabled on merchant)
- **Flow**: Billing page → create-order → Cashfree SDK checkout → verify → credits added
- **Safety**: Duplicate webhook protection, failed payment handling, payment history logging
- **Endpoints**: /api/cashfree/products, /create-order, /verify, /webhook, /history

## Story Video Quality (Prompt Engineering)
- Character consistency: EXACT physical descriptions repeated in every scene
- Motion/cinematic: Action verbs, camera angles, emotions, lighting in every visual_prompt
- Scene continuity: "characters" field persisted and prepended to image prompts
- Legal: BLOCKED_TERMS + LEGAL_NEGATIVE in all image prompts

## Self-Defending Infrastructure
- Regression Suite: 35 tests
- Deep Health: GET /api/health/deep
- Watchdog: Auto every 5 min
- Alerts + Confidence Score

## Completed Work
1-31. Core platform + Stability + Self-defending + Full UAT
32. Story Video Post-Gen Parity — 5 directions + 6 style swatches
33. Next Action Hooks — ALL 9 tools with engagement loops
34. Cross-Tool Auto-Prefill — useRemixData + RemixBanner + TTL
35. **Share → Remix Growth Loop** (Feb 2026):
    - PublicCreation.js rebuilt as conversion funnel
    - Above-fold CTA, social proof, multi-tool routing
    - No-login-wall: remix_return_url in localStorage
    - Login.js + AuthCallback.js redirect to tool after auth
    - Backend: tool_type field, /remix count endpoint
    - Testing: iteration_300 — 100% backend (20/20), 100% frontend
36. **Cashfree E2E Verification** (Feb 2026):
    - Order creation, verification, webhook, duplicate safety all verified
    - Products endpoint: 5 products, configured=true
    - INR orders work, USD not enabled on merchant
37. **Story Video Quality Improvements** (Feb 2026):
    - Enhanced scene generation: character consistency, motion, camera angles
    - Enhanced image generation: character sheet prepended to every prompt
    - Scene-to-scene continuity via "characters" field

## Remaining Backlog
### P1
- [ ] UI Consistency (aspect ratios, card sizing, grid alignment)

### P2
- [ ] Style preset preview thumbnails for Photo-to-Comic
- [ ] Admin dashboard for observability APIs
- [ ] Cashfree: Enable USD currency on merchant account

### Future
- [ ] Viral growth loop analytics (track remix→signup conversion)
- [ ] Instant Preview Mode for comics
- [ ] Export Packs (Instagram, etc.)

### Blocked
- R2 CORS — infra config
- SendGrid — plan upgrade
