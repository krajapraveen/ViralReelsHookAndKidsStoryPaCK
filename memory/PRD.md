# Visionary Suite — PRD

## Product Vision
AI Creative Operating System: **Create -> Share -> View -> Remix**
Every output is a permanent CDN-backed asset. Every creation is a living object, not a one-time result.

### Strategic Principle
> 1 flagship feature, 2 supporting features, everything else secondary.
> Build continuity, not surface area.
> **NO BUTTON SHOULD EXIST IF IT CANNOT GUARANTEE AN OUTPUT.**

## Architecture Principles
1. DB must never claim success before storage confirms success
2. Downloads are permanent CDN assets — no temp expiry
3. Stage-based pipelines — not monolithic jobs
4. Per-panel/per-page retries — never rerun entire job
5. Assets validate before exposing download
6. Every job goes through: idempotency -> guardrails -> admission -> degradation -> queue
7. Partial success > total failure — deliver what works, heal the rest
8. Upload-first UX — reduce clicks to conversion
9. Every output is a living object with continue/remix/share
10. **Frontend must never lie about backend truth** — no fake progress, no false 0 credits, no broken images
11. **SafeImage everywhere** — no raw `<img>` tags for user content

## Trust Repair Architecture (March 2026 — IMPLEMENTED)

### Credits Truth
- Credits state initialized to `null` (loading), never `0` as default
- 3-tier fetch: `/credits/balance` → retry → `/auth/me` fallback
- `isUnlimited` flag for admin/exempt users — bypasses all numeric gates
- Generate button disabled only when `credits === null` or `!canAfford`
- Admin always shows "∞" or large number, never "0"

### SafeImage Component
Bulletproof image renderer handling: null, empty, data URIs, placehold.co, broken CDN, CORS failures.
- Gradient fallback with title overlay
- No `crossOrigin` on data URIs
- Locked aspect ratios
- Deployed on ALL user-facing surfaces: Dashboard, Story Chains, My Stories, Post-gen panels

### Generation Pipeline Safety
- Polling with stale-job detection: if no progress for 60s → "Taking longer than usual"
- Hard timeout: 3 minutes (90 polls × 2s)
- Real error messages on FAILED status
- Stage-specific backend progress messages

### Re-Engagement System
- Login Interstitial: Modal on first session visit
- Action Banner: Persistent with 4h resurface
- Active Chains Nav Chip + Resume Drawer
- Momentum Messaging: Milestone targets, episodes remaining
- Metrics: continue_rate, 24h_return_rate, avg_chain_length, suggestion_ctr, resume_from_banner_rate

### Story Chain Progression
- Progress indicators: episode count, panel count, completion %
- AI suggestions: context-aware (references characters, scenes, tone), validated, cached 1h
- Direction-based continuation: Next/Twist/Escalate/Custom

### Story Video Chain Model
- story_projects extended with chain fields
- POST /continue-video: Quick Continue
- GET /active-video-chains, GET /video-chain/{chain_id}
- Post-gen panel: Quick Continue + Remix

## 5-Layer Resilience Architecture (IMPLEMENTED)
- Idempotency, Cost Guardrails, Tier-Aware Degradation, Multi-Queue, Observability

## Completed (All Sessions)
1-18. [Previous work — see CHANGELOG.md]
19. Story Chain Progression System
20. Re-Engagement System (interstitial, banner, nav chip, drawer, momentum)
21. Metrics Instrumentation (6 key retention metrics)
22. Story Video Chain Model (continuation, chains, post-gen panel)
23. Context-Aware AI Suggestions (character refs, scene continuity, tone, validation, caching)
24. **TRUST REPAIR SPRINT:**
    - Fixed credits truth: never defaults to 0, admin shows Unlimited, 3-tier fetch with fallback
    - Built SafeImage component: bulletproof image rendering, gradient fallbacks
    - Replaced ALL raw img tags on high-visibility surfaces
    - Fixed generation flow: proper polling, stale-job detection, timeout messaging
    - Fixed admin generate button: was disabled due to false 0 credits

## Remaining Backlog
### P0
- [ ] Configure R2 bucket CORS (enables direct PUT uploads + fixes CDN image CORS)

### P1
- [ ] Sweep remaining img tags across entire app (explore, creator profiles, landing)
- [ ] Download button only when asset.status === READY
- [ ] Story Video chain view page
- [ ] Video chains in Resume drawer

### P2
- [ ] Style preset preview thumbnails
- [ ] Cashfree payments (live)
- [ ] Instant Preview Mode, Export Packs
- [ ] Frontend admin dashboard for observability + metrics
- [ ] Email Notifications (BLOCKED — SendGrid)
