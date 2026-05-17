# Bug-Class Elimination Report

> Copy this file into the PR description for every production bug fix.
> Fill in **all eight** sections. A PR without a complete report is
> not mergeable.
>
> Authority: `/app/memory/ENGINEERING_DOCTRINE.md` — "The Bug-Class
> Elimination Mandate" (adopted 2026-05-22).

---

**Bug ID / ticket:** _e.g. P0-2026-05-22-strip-completion_
**Affected surface:** _Photo-to-Comic, Storybook, Payments, Auth, …_
**Severity at discovery:** _P0 outage / P1 user-visible / P2 silent_
**Date mitigated (preview):** _YYYY-MM-DD_
**Date mitigated (production):** _YYYY-MM-DD or "pending redeploy"_

---

## 1. Root cause

> The single deepest "why." Not the symptom. Not the proximate
> cause. The reason the proximate cause was even possible.

…

## 2. Exact broken boundary

> Name the boundary the bug crossed. Cite the file path and the
> line / function. There is always exactly one primary boundary.

- **File:** `…`
- **Function / line:** `…`
- **What crossed it without validation / canonicalization / idempotency:** `…`

## 3. Boundary class

> Tick exactly one primary class. Tick secondary classes only if
> the bug compounded across boundaries.

- [ ] Frontend payload
- [ ] Backend request model
- [ ] URL / path / query
- [ ] Async job (worker / queue / scheduler)
- [ ] Payment / wallet / ledger
- [ ] Cache (browser, CDN, server-side)
- [ ] Third-party contract (provider response, webhook, SDK)
- [ ] DB invariant / state machine

## 4. Why existing tests missed it

> Be specific. "We didn't test this path" is not enough — explain
> *why* the audit registry didn't catch it.

- [ ] Untested code path
- [ ] Audit existed but assertion was too narrow
- [ ] Audit existed but file not in `BOUNDARY_AUDIT_SUITES`
- [ ] Mocked dependency hid the real contract
- [ ] Test ran but did not assert on the failing field
- [ ] No audit existed for this boundary class at all
- [ ] Other: `…`

**Explanation:** `…`

## 5. Regression test / scanner

> The new test, audit, or static scanner that makes recurrence
> impossible to merge. Must be registered in `make audit-boundaries`
> unless it is a unit test colocated with new logic.

- **File:** `backend/tests/test_…_2026_…_.py`
- **Registered in Makefile?** Yes / No (justify)
- **What recurrence it blocks:** `…`
- **Synthesized negative case included?** Yes / No

## 6. Observability signal added

> The metric, structured log, `request_id` correlation, or alert
> that surfaces the next occurrence in minutes, not days.

- **Signal name:** `…_total` / `…_seconds` / `…_lag`
- **Where emitted:** `…`
- **Where consumed (dashboard / log query / alert):** `…`
- **`request_id` propagated end-to-end?** Yes / No

## 7. Similar-pattern sweep

> Grep / scan results for the same class elsewhere. A single fixed
> callsite with identical unfixed siblings is a regression filed
> as a new ticket.

- **Scan command / scanner used:** `…`
- **Other sites found:** `n`
- **Sites fixed in this PR:** `…`
- **Sites deferred (with ticket link):** `…`
- **"Scan ran, no other sites" — confirmed?** Yes / No

## 8. Scope confirmation

> Explicit statement that no unrelated features, refactors, or
> "while I'm here" cleanups were included.

- [ ] No unrelated feature work
- [ ] No unrelated refactors
- [ ] No incidental UI changes
- [ ] No incidental dependency bumps
- [ ] `git diff` reviewed line-by-line for this confirmation

**Reviewer attestation:** `…`

---

## Success definition (read before signing off)

> Success is **not** "this bug is fixed."
> Success is: **"this entire class of bug is now impossible, or is
> automatically detected the next time it tries to recur."**

If section 5 does not make the class impossible or detectable, the
report is incomplete and the fix does not ship.
