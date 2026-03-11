# Visionary Suite - PRD

## Original Problem Statement
Full-stack SaaS platform for creative content generation with monitoring, security, and admin analytics.

## LATEST UPDATE: 2026-03-11 — Session 12

### Session 12 Fixes (P0 Bug Fixes)

#### Bug #1: Blank Webpage on Navigation During Generation — FIXED
- **Root Cause**: No catch-all 404 route in App.js. Any unmatched route rendered blank.
- **Fix**: Added `<Route path="*" element={<Navigate to={isAuthenticated ? "/app" : "/"} replace />} />` to App.js
- **Additional**: WaitingWithGames "Explore while you wait" links already had `target="_blank"` from Session 11
- **Evidence**: 10/10 navigation tests passed, 404 routes redirect to dashboard

#### Bug #2: Kids Story Pack Generation Failure — FIXED
- **Root Cause**: Critical API response mismatch — `/credits/balance` returned `{credits: N}` but frontend read `response.data.balance` (undefined). Credits displayed as 0/undefined, `isFreeTier` was always falsy.
- **Fix 1**: Backend `/credits/balance` now returns both `balance` AND `credits` fields, plus `isFreeTier`
- **Fix 2**: Frontend `fetchCredits` in StoryGenerator.js and ReelGenerator.js uses `data.balance ?? data.credits ?? 0`
- **Fix 3**: `getCreditCost()` fixed to return 10 (matching backend STORY_COST=10, was returning 6/7/8)
- **Evidence**: 12 consecutive successful generations across 8 different genre/age combinations

### Test Results — Session 12
- Story Generator: 12/12 consecutive passes (25-55s each)
- Reel Generator: 1/1 pass
- Navigation: 10/10 pages load without blank pages
- 404 Route: Redirects to dashboard correctly
- Credits Display: Shows correct balance, isFreeTier banner visible
- History Persistence: 40+ story generations stored and retrievable
- Content Moderation: Blocks violent/inappropriate content (HTTP 400)
- Error Handling: Auth errors handled correctly

### Previous Session Fixes (Session 11)
1. P0 Cashfree Payment Gateway — PGCreateOrder SDK
2. P0 Story Generator Timeout — Background image generation
3. reCAPTCHA v3 — Signup, Login, ForgotPassword, Contact
4. Image parsing — Fixed character name extraction
5. reCAPTCHA soft-fail — Prevents blocking users on config issues

## Architecture
- Backend: FastAPI + MongoDB + Cashfree PG SDK + Emergent LLM
- Frontend: React + Shadcn UI + Cashfree JS SDK
- Storage: Cloudflare R2
- Queue: Redis workers

## Key Endpoints
| Endpoint | Status |
|----------|--------|
| POST /api/generate/story | FIXED (credits+response aligned) |
| POST /api/generate/reel | Working |
| GET /api/credits/balance | FIXED (returns balance+isFreeTier) |
| POST /api/subscriptions/recurring/create | Fixed (PGCreateOrder) |
| GET /api/auth/captcha-config | reCAPTCHA v3 |
| POST /api/auth/register | reCAPTCHA verified |

## Security Stack
- reCAPTCHA v3 (soft-fail mode)
- Payment webhook idempotency
- Atomic credit deduction (MongoDB)
- Rate limiting + content moderation
- Account lockout (5 failures)

## Known Issues
- SendGrid: requires plan upgrade (BLOCKED)
- Platform subscription: deployment blocked (user action needed)
- LLM key: budget may be low

## Backlog
- P0: Deploy fixes to production (user blocked on subscription)
- P1: Regenerate reCAPTCHA v3 keys if needed
- P1: Add Emergent LLM key balance
- P2: Video rendering test coverage
- P2: Job queue enhancement
- P2: R2 storage cleanup
- P2: Monitoring (Sentry/Prometheus)
