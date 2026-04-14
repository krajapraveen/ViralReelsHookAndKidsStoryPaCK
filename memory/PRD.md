# Visionary Suite - Product Requirements Document

## Architecture
- **Frontend**: React (CRA) + TailwindCSS + Shadcn/UI
- **Backend**: FastAPI + MongoDB
- **Payments**: Cashfree (production + sandbox)
- **URL**: https://trust-engine-5.preview.emergentagent.com

## Credentials
- Test: test@visionary-suite.com / Test@2026#
- Admin: admin@creatorstudio.ai / Cr3@t0rStud!o#2026

---

## Phase 2 Destruction Testing (Apr 14)
### Bugs Found & Fixed
1. **BUG-P2-001 (High)**: Draft race condition — 10 concurrent saves created 2 drafts instead of 1. FIX: Replaced upsert with delete_many + insert_one pattern. RETESTED: PASS.
2. **BUG-P2-002 (Medium)**: Analytics event dedup — session_started stored 5x per session. FIX: Added server-side DEDUP_EVENTS check in funnel_tracking.py. RETESTED: PASS.
3. **BUG-P2-003 (Critical)**: XSS — `javascript:` URI scheme bypassed bleach sanitizer. FIX: Added explicit `javascript:` and `vbscript:` stripping in drafts.py. RETESTED: PASS.
4. **BUG-P2-004 (Low)**: R2 presigned URLs reject HEAD requests. Not user-facing (GET works). R2 limitation.

### What Passed Under Destruction
- Stale token: All critical endpoints reject invalid JWT (401)
- IDOR: Job status returns 403 for non-owners
- Webhook replay: Both rejected with 403 (signature validation)
- No negative credit balances
- Credit gate blocks generation when insufficient
- 15 concurrent dashboard requests: 100% success
- Admin API blocked for non-admin users
- Frontend: Double-click, rapid nav, back-button, refresh all stable

## Previous Systems (all remain operational)
- Funnel Tracking V3 (7 critical events with dedup)
- R2 Media Proxy (presigned URLs, 1hr cache)
- Studio Creation Engine V2
- Battle System with BattlePulse
- Performance: sub-2s dashboard loads
- 30 seeded real videos
- XSS sanitization (bleach + escape + javascript: strip)

## Backlog
### P0 (Immediate)
- Push 20-50 real users via Instagram reel

### P1
- Optimize thresholds based on traffic data
- WebP/AVIF image optimization

### P2
- Category AI hooks, Celery queue, QA dashboard
