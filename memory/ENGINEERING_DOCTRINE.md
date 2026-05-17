# CreatorStudio Engineering Doctrine

**Adopted:** 2026-05-19
**Authority:** Founder mandate.
**Scope:** Every contributor, every PR, every release. No exceptions.

---

## The single doctrine

> **Never allow unvalidated input, ambiguous state, or silent failure
> to cross a system boundary.**

If a change violates this sentence, the change does not ship. Not "ship
then fix" — not ship.

---

## The ten operational rules

### 1. Every boundary validates

Validate at the edge, every edge, every time.

| Boundary | Required gate |
|---|---|
| Frontend payloads | `coerceString` / `coerceEnum` / `coerceId` / `dropEventArg` before dispatch |
| Backend request models | `Literal[...]` / `IdStr` / `SlugStr` / `TokenStr` / `OrderIdStr` — never raw `str` for known-shape fields |
| Query params | typed `Annotated[...]` with regex or `Literal` |
| Path params | typed `Annotated[...]` — anything user-controlled |
| Webhooks | signature verification + Pydantic model + idempotency key |
| Third-party responses | parse through a Pydantic model; never trust `resp.json()` directly |
| Env vars | read once at boot; fail fast if missing/malformed |
| Feature flags | typed; default safe; fail closed |
| Uploads | MIME + size + magic-byte sniff + virus-scan hook |

### 2. Every critical flow has canonical state

* One source of truth per concept. Frontend reads it from the same
  endpoint that the click handler writes to.
* No "probably complete." A flow is either complete (with a written
  durable record) or not.
* No duplicate truth sources. If two collections / two state slots
  claim the same fact, they get reconciled before the next merge.
* No optimistic drift without a reconciler. Optimistic UI must be
  paired with a server-truth refresh on success/failure.

### 3. Every failure is observable

Mandatory on every code path that can fail:

* `request_id` stamped on the inbound request, included in every log
  line, mirrored back to the client in headers AND error envelope.
* Structured error envelope: `{code, message, request_id, retryable,
  field_errors?}`.
* Stage timing — every long-running pipeline emits durations per stage.
* Retry counts — every retry increments a counter; runaway retries fire
  an alert.
* Stuck-job metric — anything that should finish in N minutes but
  hasn't is visible.
* Invalid-payload counter — `frontend_event_trap_blocked_total`,
  `error_toast_without_request_id_total`, the validation-envelope
  drop counts.
* Webhook-lag metric — gap between provider timestamp and our ingest.
* Frontend/backend build correlation — `X-Frontend-Build` on every
  client request; backend logs the build hash.

### 4. Every async action is idempotent

* Retries are safe. Replaying the same job ID twice produces the same
  outcome, not two outcomes.
* Duplicate webhooks are harmless. Provider redelivery on a 5xx must
  not double-grant credits, double-charge users, or double-create jobs.
* Partial failure recovers cleanly. A job that crashed at stage 3
  resumes at stage 3, not stage 1, and never at stage 5.
* Locks have TTLs. Stale locks auto-release; no human ever clicks
  "release lock."

### 5. Every user-facing error is sanitized

The user reads a sentence, not a debugger.

Never leak:
* stack traces / `Traceback`
* internal enum names / class names / Pydantic field paths
* validator names / regex patterns
* raw object dumps (`[object Object]`, `<Model name=…>`)
* framework internals (`fastapi.exceptions`, `pydantic.errors`)
* SDK internals (`OpenAI.APIError(…stacktrace…)`)

The user-facing surface is `{message: <safe sentence>, request_id:
<correlate-with-support>}`. Everything else goes to logs.

### 6. Every new feature must pass boundary audits

Merge gate, not nice-to-have. A PR is mergeable only if:

* `make audit-boundaries` is GREEN locally and in CI.
* `request_id` is wired through every new error path.
* New payload fields have a typed validator, not raw `str`.
* New URL builders use `safePathId` / `safeQueryParam` / `safeDownloadUrl`.
* New handlers with default args have a `dropEventArg` or `coerce*`
  guard as the first executable statement.

### 7. Freeze before expansion

When reliability signals degrade, feature work stops. Period.

Degradation signals:
* P0 user-trust failure surface ("frontend rejected style=object").
* Spike in `error_toast_without_request_id_total` or boundary-block
  counters.
* Stuck-job rate above its rolling baseline.
* New 5xx on a path that was 0% the prior week.

The order is: **stabilize → instrument → only then innovate.** Never
the other way around.

### 8. Complexity is a liability

Default to less:
* Fewer states. (Five canonical job states beats nineteen ad-hoc ones.)
* Fewer abstractions. (One `IdStr` beats four ID validators.)
* Fewer async hops. (A direct call beats a queued task that queues
  another task.)
* Fewer duplicated registries. (One `COMIC_STYLES` constant beats five
  scattered arrays.)
* Fewer hidden couplings. (Explicit dependencies, no module-level
  globals that mutate.)

Every PR that adds abstraction must justify why the existing primitive
isn't enough.

### 9. CI enforces stability automatically

```bash
make audit-boundaries
```

Runs every boundary audit. No human memory dependency. Exit code is
the merge gate.

Today's audit composition:
* `test_event_trap_audit_2026_05.py` — frontend bare-handler wirings
* `test_payload_boundary_audit_2026_05.py` — request-body payloads
* `test_url_boundary_audit_2026_05.py` — URL/path/query
* `test_backend_payload_acceptance_2026_05.py` — Pydantic enforcement
* `test_payment_auth_batch_a_2026_05.py` — payment/auth boundary
* `test_diagnostics_beacon_2026_05.py` — observability counters
* All existing P2C / storybook regression suites

Adding a new audit:
1. Land the test under `backend/tests/test_*_audit_*.py`.
2. Add the path to the `BOUNDARY_AUDIT_SUITES` list in `Makefile`.
3. The next merge automatically enforces it.

### 10. Stability > velocity theater

A feature that ships unreliably is not a feature. It is **delayed
technical debt with marketing attached.**

Visibility, correctness, and predictability beat ship-count.

---

## Living document

This file is the source of truth for engineering posture. Updates
require an explicit founder greenlight and a dated changelog entry
below.

### Changelog
* **2026-05-19** — Initial doctrine. Adopted after the P0 Photo-to-Comic
  event-trap hotfix and the Batch A payment/auth tightening.
* **2026-05-22** — Added the **Bug-Class Elimination Mandate** below.
  Production bugs are no longer treated as isolated patches; every
  fix must eliminate the entire class of failure or render it
  automatically detectable.

---

## The Bug-Class Elimination Mandate

**Adopted:** 2026-05-22
**Authority:** Founder mandate.

> Production bugs are not isolated bug fixes. Every production bug is
> a **bug-class elimination task**. One-off patches are forbidden
> except during a live P0 outage, and even then they are followed by
> the full elimination workflow within 24 hours.

### Success definition

Success is **not** "this bug is fixed."
Success is: **"this entire class of bug is now impossible, or is
automatically detected the next time it tries to recur."**

A change that closes one ticket without closing the class is a
half-fix and is rejected at review.

### Stability doctrine — the eight non-negotiables

1. Validate every boundary.
2. Canonicalize all critical state.
3. Make async jobs idempotent.
4. Never trust client payloads.
5. Never expose internal errors.
6. Every failure carries a `request_id`.
7. Every recurring issue becomes a CI rule.
8. No new feature work during an instability freeze.

These are not aspirations. They are merge gates.

### The mandatory 8-section bug report

Every production bug, before being marked resolved, must produce a
structured report addressing **all eight** of the following. A fix
without this report is incomplete and does not ship.

| # | Section | What it answers |
|---|---|---|
| 1 | **Root cause** | The single deepest "why" — not the symptom, not the proximate cause |
| 2 | **Exact broken boundary** | Which boundary (frontend payload / backend request / URL / async job / cache / 3rd-party contract / DB invariant) let the bug through |
| 3 | **Boundary class** | Frontend ▪ Backend ▪ Async job ▪ Payment ▪ Cache ▪ Third-party contract ▪ DB invariant — exactly one is primary |
| 4 | **Why existing tests missed it** | Was it untested code, a gap in the audit registry, a too-narrow assertion, or a mocked-away dependency? |
| 5 | **Regression test / scanner** | The new test, audit, or static scanner — registered in `make audit-boundaries` — that makes recurrence impossible to merge |
| 6 | **Observability signal added** | The metric / structured log / `request_id` correlation / alert that surfaces the next occurrence within minutes, not days |
| 7 | **Similar-pattern sweep** | Result of grepping / scanning for the same class elsewhere in the codebase — with a list of additional sites fixed in the same PR, or an explicit "scan ran, no other sites" |
| 8 | **Scope confirmation** | Explicit statement that **no unrelated features, refactors, or "while I'm here" cleanups** were included in the PR |

The canonical template lives at
`/app/memory/BUG_CLASS_ELIMINATION_TEMPLATE.md`. Copy it, fill it
in, attach it to the PR description. No PR without it.

### How this interacts with the existing 10 rules

The mandate is the **operational procedure** that gives teeth to
Rule 6 (Boundary audits) and Rule 9 (CI enforcement). Specifically:

* Section 5 (regression test/scanner) **must** be added to the
  `BOUNDARY_AUDIT_SUITES` list in `/app/Makefile` if it is a static
  or runtime audit. The next `make audit-boundaries` run executes it
  with no human memory dependency.
* Section 6 (observability) reinforces Rule 3 — no failure is
  observable until its `request_id` survives the full failure chain.
* Section 7 (similar-pattern sweep) enforces "fix the class, not the
  instance." A single fixed callsite with five identical unfixed
  siblings is a regression waiting to be filed as a new ticket.
* Section 8 (scope) protects the freeze. Bug fixes during freeze do
  not become Trojan horses for feature work.

### The only exception

A live P0 outage may ship a one-off patch **before** the report is
written, to stop bleeding. The full 8-section report and its CI
scanner must follow within 24 hours of the outage being mitigated.
"We'll do it next sprint" is not an acceptable answer.

### Enforcement

This mandate is pinned by
`backend/tests/test_bug_class_elimination_mandate_2026_05.py`,
which is part of `make audit-boundaries`. The test fails any change
that weakens or removes:

* the mandate's 8 numbered sections,
* the stability doctrine's 8 non-negotiables,
* the success-definition sentence,
* the canonical template file.

Modifying any of the above requires an explicit founder greenlight
and a dated changelog entry above.
