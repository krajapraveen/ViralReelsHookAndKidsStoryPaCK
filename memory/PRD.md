# Visionary Suite - Product Requirements Document

## Original Problem Statement
Full-stack SaaS platform for creative content generation with comprehensive monitoring, security, and admin analytics.

## LATEST UPDATE: 2026-03-11 (Session 11 - P0 PAYMENT FIX + RECAPTCHA v3)

### Fix 1: P0 Cashfree Payment Gateway — RESOLVED
**Date:** 2026-03-11
**Issue:** Subscribe Now and Upgrade Now buttons on `/app/subscription` did not open Cashfree payment gateway.
**Root Cause:** `cashfree_subscription_service.py` used raw HTTP calls to Cashfree Subscriptions API which returned `internal_error`.
**Fix:** Replaced with PGCreateOrder via Cashfree PG SDK. Returns `paymentSessionId` for Cashfree JS SDK checkout modal.
**Files:** `backend/routes/subscriptions.py`, `frontend/src/pages/SubscriptionManagement.jsx`
**Test:** 22/22 backend tests passed, frontend verified

### Fix 2: Google reCAPTCHA v3 Integration — COMPLETED
**Date:** 2026-03-11
**Scope:** Signup (mandatory), Login (after 3 failures), Forgot Password, Contact Form
**NOT applied to:** Dashboard, generation tools, subscription, payment pages
**Keys:** Site Key in frontend/.env, Secret Key in backend/.env
**Files Modified:**
- `backend/routes/auth.py` — reCAPTCHA v3 config, verify_recaptcha(), updated register/login/forgot-password
- `backend/routes/feedback.py` — reCAPTCHA on contact form
- `backend/models/schemas.py` — Added captcha_token to UserCreate/UserLogin
- `frontend/src/hooks/useRecaptcha.js` — Shared hook for loading & executing reCAPTCHA v3
- `frontend/src/pages/Signup.js` — Replaced hCaptcha with reCAPTCHA v3
- `frontend/src/pages/Login.js` — Added reCAPTCHA after failed attempts
- `frontend/src/pages/ForgotPassword.js` — Added reCAPTCHA
- `frontend/src/pages/Contact.js` — Added reCAPTCHA
- `frontend/public/index.html` — CSP updated for google.com + gstatic.com
**Test:** 15/15 backend tests passed, all 4 frontend pages verified

### Previous Session Fixes (2026-03-10):
- P0 Video Pipeline Bug Fix
- UI: "Beta Release" label for Story to Video
- P0 Billing Page Fix
- Critical XSS Vulnerability Fix
- Credit Deduction Race Condition Fix (atomic MongoDB)
- P0 Subscription UI Fix

## Architecture
```
/app/
├── backend/
│   ├── routes/
│   │   ├── auth.py                   # reCAPTCHA v3 integration
│   │   ├── subscriptions.py          # Cashfree PGCreateOrder for subscriptions
│   │   ├── cashfree_payments.py      # Credit pack purchases + webhooks
│   │   ├── feedback.py               # Contact form with reCAPTCHA
│   │   ├── reels_routes.py           # XSS-secured reel generation
│   │   └── story_video_generation.py # Video pipeline (fixed)
│   ├── services/
│   │   ├── cashfree_subscription_service.py  # Plan definitions
│   │   └── auto_scaling_service.py   # Job queue/worker system
│   ├── models/schemas.py             # UserCreate/UserLogin with captcha_token
│   ├── shared.py                     # Atomic credit operations
│   └── server.py
└── frontend/
    └── src/
        ├── hooks/useRecaptcha.js      # Shared reCAPTCHA v3 hook
        ├── pages/
        │   ├── Signup.js              # reCAPTCHA v3 on signup
        │   ├── Login.js               # reCAPTCHA v3 after 3 failures
        │   ├── ForgotPassword.js      # reCAPTCHA v3
        │   ├── Contact.js             # reCAPTCHA v3
        │   ├── SubscriptionManagement.jsx  # Cashfree JS SDK checkout
        │   ├── Billing.js             # Credit purchases
        │   └── Pricing.js             # Redirects to Billing
        ├── utils/api.js               # API endpoints
        └── public/index.html          # CSP with Google reCAPTCHA domains
```

## Key API Endpoints
| Endpoint | Status | reCAPTCHA |
|----------|--------|-----------|
| GET /api/auth/captcha-config | ✅ | Returns v3 config |
| POST /api/auth/register | ✅ | Always verified |
| POST /api/auth/login | ✅ | After 3 failures |
| POST /api/auth/forgot-password | ✅ | Always verified |
| POST /api/feedback/contact | ✅ | Always verified |
| POST /api/subscriptions/recurring/create | ✅ | No CAPTCHA |
| POST /api/subscriptions/recurring/verify | ✅ | No CAPTCHA |
| POST /api/cashfree/create-order | ✅ | No CAPTCHA |

## Security Stack
| Feature | Status |
|---------|--------|
| Google reCAPTCHA v3 | ✅ Implemented |
| Payment webhook idempotency | ✅ Implemented |
| Credit race condition protection | ✅ Atomic MongoDB |
| Rate limiting (API) | ✅ Implemented |
| XSS protection | ✅ Fixed |
| Account lockout | ✅ After 5 failures |
| Anti-abuse (fingerprint) | ✅ On signup |

## Known Issues
- **SendGrid Email Service**: User's plan needs upgrade (non-code issue)
- **Emergent Deployment**: User blocked by platform subscription issue
- **Preview Domain**: Not in reCAPTCHA whitelist (production domain is whitelisted)

## Backlog (Prioritized)
- P0: Deploy to production (payment fix + reCAPTCHA)
- P1: Test coverage for video rendering + payment webhooks
- P2: Enhance job queue & worker architecture
- P2: File storage cleanup for Cloudflare R2
- P2: Monitoring & observability (Sentry/Prometheus/Grafana)

## Test Credentials
- Test User: test@visionary-suite.com / Test@2026#
- Admin: admin@creatorstudio.ai / Cr3@t0rStud!o#2026

## 3rd Party Integrations
| Service | Status |
|---------|--------|
| Cashfree (Payments) | ✅ Fixed |
| Google reCAPTCHA v3 | ✅ New |
| Cloudflare R2 (Storage) | ✅ Working |
| Redis (Job Queue) | ✅ Working |
| SendGrid (Email) | ⚠️ Blocked |
| Emergent LLM Key | ✅ Working |
| FFmpeg (Video) | ✅ Working |
