# Visionary Suite — PRD

## Architecture
- React + FastAPI + MongoDB + Cloudflare R2 + Cashfree
- URL: https://trust-engine-5.preview.emergentagent.com

## Credentials
- Test: test@visionary-suite.com / Test@2026#
- Admin: admin@creatorstudio.ai / Cr3@t0rStud!o#2026

---

## Production Control System (Final)

### Kill Switches (`POST /api/admin/kill-switch/{id}`)
| Switch | What It Blocks | User Sees |
|--------|---------------|-----------|
| generation_disabled | All create endpoints | "Content generation temporarily disabled. Credits safe." |
| payments_disabled | Cashfree create-order | "Payments temporarily disabled. No charges." |
| battle_disabled | Quick-shot + submit | "Battle submissions paused." |
| readonly_mode | ALL writes (drafts, gen, payments) | "System in read-only mode." |

**Webhook exception**: Payment callbacks bypass readonly mode — reconciliation always works.
**Frontend**: 503 responses show honest toast (no spinner, no retry storm).

### Guardrails — 10 Invariants
| # | Invariant | Severity | Endpoint |
|---|-----------|----------|----------|
| 1 | negative_credits | Critical | full + critical |
| 2 | duplicate_credit_grants | Critical | full + critical |
| 3 | multiple_active_drafts | High | full only |
| 4 | orphan_processing_jobs | High | full only |
| 5 | analytics_session_duplication | Medium | full only |
| 6 | payment_without_credit | Critical | full + critical |
| 7 | private_content_leak | High | full only |
| 8 | credit_drift | Critical | full + critical |
| 9 | generation_integrity | Critical | full + critical |
| 10 | orphan_deductions | Critical | full + critical |

### Monitoring Endpoints
```
# Every 1-5 min — money/credit/generation (fast, 6 critical checks)
GET /api/admin/guardrails/critical

# Every 30 min — full system health (10 checks)
GET /api/admin/guardrails

# After 10/25/50 users — product truth
GET /api/admin/user-signals?days=1

# Emergency controls
GET /api/admin/kill-switch
POST /api/admin/kill-switch/{id} {"enabled": true, "reason": "..."}
```

---

## Current Status: 10/10 PASS, 4 kill switches operational, frontend 503 handled

## Backlog
- P0: Push 20-50 users with monitoring
- P1: SV-007 auth fix, WebP/AVIF, payment fault injection in staging
- P2: Pipeline stress, Celery, character continuity
