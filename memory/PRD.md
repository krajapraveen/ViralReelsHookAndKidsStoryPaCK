# Visionary Suite — PRD

## Architecture
- React + FastAPI + MongoDB + Cloudflare R2 + Cashfree
- URL: https://trust-engine-5.preview.emergentagent.com

## Credentials
- Test: test@visionary-suite.com / Test@2026#
- Admin: admin@creatorstudio.ai / Cr3@t0rStud!o#2026

---

## Monitoring Endpoints (Use During Traffic Push)

### Guardrails — System Integrity
```
GET /api/admin/guardrails
Authorization: Bearer <admin_token>
```
Returns pass/fail for 7 invariants. If `healthy: false` → STOP traffic.

### User Signals — Product Truth
```
GET /api/admin/user-signals?days=1
Authorization: Bearer <admin_token>
```
Returns 4 core signals:
1. **TTFV**: median, p75, p90, reached vs not-reached counts
2. **Funnel**: landing → typing → generate → completed → postgen (with conversion %)
3. **Second Action Rate**: users who did anything after first generation
4. **Return Behavior**: 2+ session users, same-day returns, median return delay

### How to Interpret (First 50 Users)
- TTFV > 3min → friction problem (fix UX, not backend)
- Landing→typing < 40% → hero/CTA not compelling
- Generate→completed < 60% → pipeline trust issue
- Second action < 20% → weak product pull
- Return rate < 10% → forgettable product

---

## All Systems Built This Session

| System | Status | Files |
|--------|--------|-------|
| Red Flag Alerts (7 invariants) | LIVE | `/app/backend/routes/guardrails.py` |
| Guardrail Endpoint | LIVE | Same file |
| User Signals Endpoint | LIVE | `/app/backend/routes/user_signals.py` |
| XSS Hardening (15 vectors) | VERIFIED | `/app/backend/routes/drafts.py` |
| Draft Race Fix (unique index) | VERIFIED | Same + MongoDB index |
| Analytics Dedup (server-side) | VERIFIED | `/app/backend/routes/funnel_tracking.py` |
| Funnel Tracking V3 (7 events) | LIVE | `funnel_tracking.py` + `useSessionTracker.js` |
| R2 Media Proxy | LIVE | `/app/backend/routes/r2_proxy.py` |

## All Bugs Found & Fixed

| # | Bug | Severity | Fix |
|---|-----|----------|-----|
| 1 | XSS in drafts (script/onerror) | Critical | bleach + html.escape |
| 2 | Draft race condition | High | Unique partial index + fallback |
| 3 | Analytics dedup missing | Medium | Server-side DEDUP_EVENTS |
| 4 | javascript: bypass (exact case) | Critical | Case-insensitive regex |
| 5 | JaVaScRiPt: mixed case | Critical | Same regex (IGNORECASE) |
| 6 | R2 HEAD 403 | Low | R2 limitation (GET works) |

## Ship Status
**READY FOR LIMITED TRAFFIC** — Guardrails + User Signals active.

## Backlog
- P0: Push 20-50 users, check guardrails every 30min, analyze user-signals
- P1: WebP/AVIF, payment fault injection in staging
- P2: Celery, category AI hooks, battle recomputation
