# Visionary Suite — PRD (Updated Apr 14, 2026)

## Architecture
- React + FastAPI + MongoDB + Cloudflare R2 + Cashfree
- URL: https://trust-engine-5.preview.emergentagent.com

## Credentials
- Test: test@visionary-suite.com / Test@2026#
- Admin: admin@creatorstudio.ai / Cr3@t0rStud!o#2026

---

## Phase 3+4 Testing Summary (Apr 14)

### Kill-Sheet Results: 38 tests | PASS: 36 | FAIL: 1 (fixed) | BLOCKED: 2

### Bugs Found Across All Phases

| Bug | Severity | Status | Fix |
|-----|----------|--------|-----|
| Draft race (50 concurrent) | High | FIXED | MongoDB unique partial index + upsert with DuplicateKey fallback |
| Analytics dedup (session_started) | Medium | FIXED | Server-side DEDUP_EVENTS check |
| XSS: `javascript:` bypass | Critical | FIXED | Case-insensitive regex for javascript/vbscript/data URI schemes |
| XSS: `JaVaScRiPt:` mixed case | Critical | FIXED | Same regex fix (re.IGNORECASE) |
| R2 HEAD 403 | Low | Known | R2 limitation, GET works, not user-facing |

### What Survived Destruction
- 50 concurrent draft saves → 1 draft (unique index enforced)
- 10x session_started → 1 stored (server dedup)
- Webhook replay → 403 (signature validation)
- Stale token → 401 on all endpoints
- IDOR → 403 on non-owner job access
- No negative credits in DB
- No duplicate feed cards
- No private content in feed
- Admin APIs blocked for standard users
- Media re-fetchable via presigned URLs
- Event ordering preserved chronologically
- Attribution correct (direct/instagram/share_link)
- 6/6 XSS vectors sanitized (script, onerror, onload, javascript:, svg, data:)
- Credits consistent across repeated requests
- Battle scores correctly ordered

### Ship Recommendation
READY FOR LIMITED TRAFFIC with monitoring on:
- Credits/ledger drift
- Analytics event counts
- Error rates
- Session durations

## Backlog
- P0: Push 20-50 real users via Instagram reel
- P1: WebP/AVIF optimization, threshold tuning
- P2: Celery queue, category AI hooks
