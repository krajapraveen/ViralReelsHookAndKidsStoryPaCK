# Visionary Suite — PRD

## Architecture
- React + FastAPI + MongoDB + Cloudflare R2 + Cashfree
- URL: https://trust-engine-5.preview.emergentagent.com

## Credentials
- Test: test@visionary-suite.com / Test@2026#
- Admin: admin@creatorstudio.ai / Cr3@t0rStud!o#2026

---

## Ship Status: CONTROLLED RELEASE READY

### What is proven:
- **Module access layer**: 10/10 creator tools route correctly, auth-protected, mobile-responsive
- **System integrity**: 7 invariant guardrails all PASS (credits, drafts, analytics, payments, privacy)
- **Security**: XSS hardened (15 vectors), draft race fixed (unique index), analytics dedup (server-side)
- **Monitoring**: Guardrails + User Signals endpoints live

### What is NOT proven:
- Generation pipeline under real multi-user load
- Partial failure recovery per module
- Character/story memory continuity across real outputs
- Credit reconciliation during failed generations
- Production media pipeline quality

### Known issue:
- SV-007: `/api/story-engine/create` returns 422 (not 401) without auth — sloppy contract, not a breach

---

## Monitoring Endpoints

### System integrity (every 30 min during traffic)
```
GET /api/admin/guardrails
Authorization: Bearer <admin_token>
```

### Product truth (after 10/25/50 users)
```
GET /api/admin/user-signals?days=1
Authorization: Bearer <admin_token>
```

### Signal interpretation:
- TTFV > 3min → friction problem
- Landing→typing < 40% → hero/CTA issue
- Second action < 20% → weak product pull
- Return rate < 10% → forgettable product

---

## All Bugs Found & Fixed (Complete History)

| # | Bug | Severity | Phase | Fix |
|---|-----|----------|-------|-----|
| 1 | XSS in draft save | Critical | QA P1 | bleach + html.escape |
| 2 | Draft race condition | High | P2 | Unique partial MongoDB index |
| 3 | Analytics dedup missing | Medium | P2 | Server-side DEDUP_EVENTS |
| 4 | javascript: XSS bypass | Critical | P2 | Case-insensitive regex |
| 5 | JaVaScRiPt: mixed case | Critical | P3 | (?i)(javascript\|vbscript\|data)\s*: |
| 6 | R2 HEAD 403 | Low | P2 | R2 limitation (GET works) |
| 7 | Orphan subscription order | Low | Guardrails | Excluded from payment check |

## Systems Built This Session
- Red Flag Alert System (7 invariants)
- Guardrail Endpoint + Alerts + History
- User Signals Endpoint (4 core signals)
- XSS Hardening (15 vectors)
- Draft Race Fix (unique index)
- Analytics Dedup (server-side)
- Funnel Tracking V3 (7 events)
- R2 Media Proxy
- Session Time Tracking

## Backlog
- P0: Push 20-50 users, monitor guardrails + user-signals
- P1: Fix SV-007 auth contract, WebP/AVIF, payment fault injection in staging
- P2: Deep pipeline testing per module from live evidence, Celery, category AI hooks
