# Visionary Suite - PRD

## Original Problem Statement
Full-stack SaaS platform for creative content generation with monitoring, security, and admin analytics.

## LATEST UPDATE: 2026-03-11 — Session 11

### Session Fixes
1. **P0 Cashfree Payment Gateway** — Replaced broken Subscription API with PGCreateOrder SDK
2. **P0 Story Generator Timeout** — Background image generation via FastAPI BackgroundTasks
3. **reCAPTCHA v3** — Signup, Login (3+ failures), ForgotPassword, Contact form
4. **Image parsing** — Fixed character name extraction (dict vs string handling)
5. **reCAPTCHA soft-fail** — Prevents blocking users on config issues

### Test Results
- Story Generator: 5/5 passes (24-48s)
- Reel Generator: 3/3 passes
- Payment: 6/6 payment flows working
- Admin: All endpoints working
- Frontend: 12/12 pages loading
- Credits: Exact deduction verified (560→530 after 3 stories)

## Architecture
- Backend: FastAPI + MongoDB + Cashfree PG SDK + Emergent LLM
- Frontend: React + Shadcn UI + Cashfree JS SDK
- Storage: Cloudflare R2
- Queue: Redis workers

## Key Endpoints
| Endpoint | Status |
|----------|--------|
| POST /api/generate/story | ✅ Fixed (background images) |
| POST /api/generate/reel | ✅ Working |
| POST /api/subscriptions/recurring/create | ✅ Fixed (PGCreateOrder) |
| POST /api/subscriptions/recurring/verify | ✅ New |
| POST /api/cashfree/create-order | ✅ Working |
| GET /api/auth/captcha-config | ✅ reCAPTCHA v3 |
| POST /api/auth/register | ✅ reCAPTCHA verified |
| POST /api/auth/login | ✅ reCAPTCHA after 3 failures |

## Security Stack
- reCAPTCHA v3 (soft-fail mode)
- Payment webhook idempotency
- Atomic credit deduction (MongoDB)
- Rate limiting
- XSS protection
- Account lockout (5 failures)
- Device fingerprinting

## Known Issues
- Story image gen: intermittent library error (background, non-blocking)
- reCAPTCHA keys: may be v2 (soft-fail prevents blocking)
- SendGrid: requires plan upgrade
- Emergent LLM key: budget briefly exceeded

## Backlog
- P0: Deploy to production
- P1: Regenerate reCAPTCHA v3 keys
- P1: Add Emergent LLM key balance
- P2: Video rendering test coverage
- P2: Job queue enhancement
- P2: R2 storage cleanup
- P2: Monitoring (Sentry/Prometheus)
