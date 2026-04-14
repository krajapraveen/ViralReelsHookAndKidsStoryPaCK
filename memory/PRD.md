# Visionary Suite — PRD

## Architecture
- React + FastAPI + MongoDB + Cloudflare R2 + Cashfree
- URL: https://trust-engine-5.preview.emergentagent.com

## Credentials
- Test: test@visionary-suite.com / Test@2026#
- Admin: admin@creatorstudio.ai / Cr3@t0rStud!o#2026

---

## Systems Built This Session (Apr 14)

### 1. Red Flag Alert System
- **7 invariant checks** running on every guardrail request
- Alerts persist in `system_alerts` collection with severity, count, first_seen_at, last_seen_at, sample_entity_ids
- Auto-dedup: same invariant/entity doesn't spam
- Auto-resolve: when invariant returns healthy, open alerts close

### 2. Guardrail Endpoint (`GET /api/admin/guardrails`)
- Admin-only (403 for standard users)
- Returns per invariant: status, name, severity, count, sample_ids, last_triggered_at, trigger_count
- Overall healthy/unhealthy flag
- Sub-endpoints: `/alerts` (open), `/history` (N-day history)

### Invariants Monitored:
| Key | Severity | What It Catches |
|-----|----------|-----------------|
| negative_credits | Critical | Any user with credits < 0 |
| duplicate_credit_grants | Critical | Same order_id credited twice |
| multiple_active_drafts | High | User with >1 draft (status=draft) |
| orphan_processing_jobs | High | Jobs stuck PROCESSING >30min |
| analytics_session_duplication | Medium | session_started >1 per session_id |
| payment_without_credit | Critical | PAID order without ledger entry |
| private_content_leak | High | Non-READY content in public queries |

### 3. XSS Hardening (15 vectors tested)
- Case-insensitive regex: `(?i)(javascript|vbscript|data)\s*:`
- bleach.clean() strips all HTML tags
- html.escape() escapes remaining chars
- 15/15 vectors pass: URL-encoded, entity-encoded, mixed-case, whitespace, tab, newline, href, data URI, markdown link, double-encoded, SVG, img, body, style, unicode

### 4. Draft Race Condition Fix
- MongoDB unique partial index: `one_active_draft_per_user`
- Upsert with DuplicateKeyError fallback
- Tested: 50 concurrent saves → exactly 1 draft

### 5. Analytics Server-Side Dedup
- DEDUP_EVENTS: session_started, session_ended, typing_started
- Checks existing event before insert
- Cleaned 25 duplicate events from pre-fix testing

---

## All Bugs Found & Fixed Across All Phases

| # | Bug | Severity | Phase | Status |
|---|-----|----------|-------|--------|
| 1 | XSS in draft save (script/onerror) | Critical | P2 | FIXED |
| 2 | Draft race (50 concurrent → 2 drafts) | High | P2 | FIXED (unique index) |
| 3 | Analytics dedup (5x session_started) | Medium | P2 | FIXED (server dedup) |
| 4 | `javascript:` bypass (exact case) | Critical | P2 | FIXED (regex) |
| 5 | `JaVaScRiPt:` mixed case bypass | Critical | P3 | FIXED (case-insensitive regex) |
| 6 | R2 HEAD 403 | Low | P2 | Known (R2 limitation, GET works) |
| 7 | Draft race under network instability | High | P3 | FIXED (unique index) |

## Ship Status
**READY FOR LIMITED TRAFFIC** with guardrails active.

## Backlog
- P0: Push 20-50 users with monitoring
- P1: WebP/AVIF, threshold tuning, staging payment fault injection
- P2: Celery, category AI hooks, battle recomputation testing
