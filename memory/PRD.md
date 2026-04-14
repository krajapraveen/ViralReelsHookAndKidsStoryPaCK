# Visionary Suite — PRD

## Architecture
- React + FastAPI + MongoDB + Cloudflare R2 + Cashfree
- URL: https://trust-engine-5.preview.emergentagent.com

## Credentials
- Test: test@visionary-suite.com / Test@2026#
- Admin: admin@creatorstudio.ai / Cr3@t0rStud!o#2026

---

## Production Control System (Complete)

### Kill Switches (`GET/POST /api/admin/kill-switch`)
| Switch | Effect | User Message |
|--------|--------|-------------|
| KS1: generation_disabled | Blocks all create endpoints | "Content generation temporarily disabled. Credits safe." |
| KS2: payments_disabled | Blocks checkout + webhook | "Payments temporarily disabled. No charges." |
| KS3: battle_disabled | Blocks quick-shot + submit | "Battle submissions paused." |
| KS4: readonly_mode | Blocks ALL writes | "System in read-only mode." |

Toggle: `POST /api/admin/kill-switch/{id}` with `{"enabled": true/false, "reason": "..."}`

### Guardrails (`GET /api/admin/guardrails`) — 9 Invariants
| # | Invariant | Severity | What It Catches |
|---|-----------|----------|-----------------|
| 1 | negative_credits | Critical | Users with balance < 0 |
| 2 | duplicate_credit_grants | Critical | Same order_id credited twice |
| 3 | multiple_active_drafts | High | >1 draft per user |
| 4 | orphan_processing_jobs | High | Jobs stuck >30min |
| 5 | analytics_session_duplication | Medium | session_started >1 per session |
| 6 | payment_without_credit | Critical | PAID order without ledger entry |
| 7 | private_content_leak | High | Non-READY in feed |
| 8 | credit_drift | Critical | purchased - used != balance |
| 9 | generation_integrity | Critical | Jobs without matching deductions |

### User Signals (`GET /api/admin/user-signals?days=N`)
- TTFV (median, p75, p90)
- Funnel (landing → typing → generate → completed → postgen with conversion %)
- Second Action Rate (breakdown by type)
- Return Behavior (2+ sessions, same-day, median delay)

---

## Monitoring Protocol During Traffic

```
# Every 30 min — system integrity
GET /api/admin/guardrails
→ If healthy: false → STOP TRAFFIC

# After 10/25/50 users — product truth
GET /api/admin/user-signals?days=1

# Emergency — instant disable
POST /api/admin/kill-switch/generation_disabled {"enabled": true, "reason": "..."}
POST /api/admin/kill-switch/payments_disabled {"enabled": true, "reason": "..."}
```

---

## Ship Status: CONTROLLED RELEASE READY
- 9/9 guardrails PASS
- 4/4 kill switches verified (503 on all blocked actions)
- User signals endpoint live
- Kill switches audit-logged to system_alerts

## Backlog
- P0: Push 20-50 users with monitoring
- P1: Fix SV-007, WebP/AVIF, payment fault injection
- P2: Pipeline stress test, Celery, character continuity
