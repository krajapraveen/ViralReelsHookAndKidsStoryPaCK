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
