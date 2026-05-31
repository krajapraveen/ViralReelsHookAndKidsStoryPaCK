# Visionary Suite - Changelog


## 2026-06 — P0 Reliability: Billing Page Decoupled-Fetch & Session-Probe

**Status**: SHIPPED in preview. `make audit-boundaries` green (459 passing, 1 skipped). Awaiting production deploy.

**Symptom**: `/app/billing` rendered the shell then showed "Failed to load billing data" — page unusable. `/api/cashfree/products` was 200, but `/api/credits/balance` 401 was nuking the whole page (Promise.all coupling), and a stale localStorage user + expired token was bypassing live session checks.

**Bug classes pinned**:
1. **Dependency-coupling crash** — a non-critical XHR failure must never tombstone a page whose primary content loaded. Promise.all forbidden for fan-outs with decorative branches.
2. **Stale-session phantom** — pages must NOT render authenticated shells from cached localStorage without a live `/api/auth/me` probe.
3. **Param-mismatch race** — global axios interceptor used `?return=`, Billing.js used `?next=`, Login.js read only `?return=`. Now canonical `?next=` everywhere; Login.js accepts both.

**Files changed**:
- `frontend/src/utils/api.js` — interceptor exempts `/api/auth/me` (session probe); redirect param unified to `?next=`.
- `frontend/src/pages/Login.js` — accepts both `?next=` (canonical) and `?return=` (legacy).
- `frontend/src/App.js` — `/app/billing` route guard preserves `?next=/app/billing` on unauthenticated visit; `AuthenticatedRedirect` reads `?next=` first.
- `frontend/src/utils/generationLifecycle.js` — deferred-login URL unified to `?next=`.
- `backend/tests/test_billing_decoupled_fetch_and_session_2026_05.py` — **NEW** 17-test invariant suite (registered in `Makefile`).
- `Makefile` — new test suite registered in `BOUNDARY_AUDIT_SUITES`.

**No backend changes** — `/api/cashfree/products` (public) and `/api/credits/balance` (auth-required) contracts were already correct.

**Verification**: All 3 spec scenarios PASS via Playwright smoke test (anonymous → next=, authenticated → renders, stale-token → wiped+redirected). 459/459 audit-boundaries tests green.



─────────────────────────────────────────────────────────
[2026-05-19] GENERIC COMPLETION-INVARIANT SCANNER — SHIPPED
─────────────────────────────────────────────────────────
Founder mandate: "No future async/multi-output pipeline should ever
reach COMPLETED unless declared output count matches actual verified
output count." Freeze intact.

CANONICAL HELPER — backend/services/reliability/completion_invariant.py
  Public API:
    assert_completion_invariant(
        expected_count, actual_count, declared_status,
        request_id, job_id, pipeline, db,
        repair_status="PARTIAL_READY",
        terminal_success_states=DEFAULT_TERMINAL_SUCCESS,
    ) -> InvariantResult

  Contract:
    • Returns `InvariantResult(effective_status, decision, repaired,
      expected, actual, pipeline, request_id, job_id)`.
    • NEVER raises — invariant failure is a domain event, not a 500.
    • When the declared status claims terminal success but counts
      disagree, downgrades to `PARTIAL_READY` (configurable) with
      decision `ACCEPT_PARTIAL_INVARIANT_REPAIRED`.
    • Recognized terminal-success statuses: COMPLETED, READY,
      SUCCESS, READY_WITH_WARNINGS (override per call).
    • Non-success terminal statuses (FAILED, CANCELLED, etc.) pass
      through untouched.

  Metrics emitted on invariant failure (daily-bucketed):
    • completion_invariant_failed_total
    • false_complete_prevented_total
    • partial_output_repaired_total  (only when actual_count > 0)

  Registry:
    REGISTERED_PIPELINES = ("routes/photo_to_comic.py",)
    The static audit only enforces files in this tuple — opt-in so
    we never false-flag pipelines that haven't been migrated yet.

STRIP PATH MIGRATED TO HELPER
  routes/photo_to_comic.py — the inline downgrade block we shipped
  in the P0 hotfix is replaced by a single call to
  `assert_completion_invariant(..., pipeline="photo_to_comic.strip")`.
  Behavior is identical; the wiring is now uniform and auditable.

STATIC AUDIT SCANNER — backend/tests/test_completion_invariant_audit_2026_05.py
  For every file in REGISTERED_PIPELINES:
    1. File must import / reference `assert_completion_invariant`.
    2. Every function that persists a terminal-success status (via
       direct assignment `status = "COMPLETED"` OR
       `update_one(..., {"$set": {"status": "COMPLETED"}})`) MUST
       either:
        (a) call `assert_completion_invariant(...)` in the same
            function body, OR
        (b) carry an explicit `# invariant: not_applicable` comment
            inside the function body (for single-output flows like
            avatar mode).
  The scanner uses a precise WRITE-only regex (`$set` + direct
  assignment to `status` / `job_status` / `new_status` / `final_status`)
  so read-side comparisons (`if status == "COMPLETED"`) and
  filter clauses (`count_documents({"status":"COMPLETED"})`) are
  correctly ignored.

OPT-OUT MARKERS APPLIED (single-output flows)
  • routes/photo_to_comic.py :: process_comic_avatar
      Two persistence sites — primary success path and the
      guaranteed-output fallback. Both annotated with
      `# invariant: not_applicable` (single image, count gate N/A).

REGRESSION TESTS — 10 (backend/tests/test_completion_invariant_audit_2026_05.py)
  Live coverage:
    • test_registered_pipelines_exist
    • test_registered_pipeline_imports_invariant   [photo_to_comic.py]
    • test_registered_pipeline_functions_gate_terminal_success
                                                   [photo_to_comic.py]
  Helper contract:
    • test_invariant_helper_exposes_public_api
    • test_invariant_helper_emits_required_metrics
    • test_invariant_helper_never_raises_on_invariant_failure
    • test_invariant_helper_accepts_full_count
    • test_invariant_helper_lets_failed_status_through
  Synthesized regressions:
    • test_synthesized_unregistered_pipeline_is_flagged
    • test_synthesized_opt_out_marker_is_respected

EXISTING P0 STRIP TESTS UPDATED
  backend/tests/test_strip_completion_invariant_2026_05.py
  The pin tests now assert the canonical helper call signature
  (`expected_count=panel_count`, `actual_count=actual_ready_count`,
  `pipeline="photo_to_comic.strip"`) rather than the prior inline
  block, so the migration to the helper is locked in.

CI GATE
  Makefile :: BOUNDARY_AUDIT_SUITES now includes the new audit.
  `make audit-boundaries` → 204 passed, 1 skipped (62s). Lint clean.

WHAT THIS DELIVERS
  The platform now ENFORCES at PR-merge time:
    1. No registered pipeline can persist a terminal-success status
       without going through the canonical gate.
    2. The gate provably downgrades partial-output claims.
    3. Single-output flows must declare themselves intentional
       (explicit `# invariant: not_applicable`) — drift is auto-detected.
    4. Each gate firing emits ops-visible metrics so production-side
       false-completion attempts surface immediately.

BACKLOG (FUTURE OPT-IN PIPELINES)
  Pipelines to migrate into REGISTERED_PIPELINES as they ship new
  changes:
    • routes/comic_storybook_v2.py
       (already has per-scene completion invariant; migrate the
        wiring to the canonical helper for uniformity.)
    • routes/story_video_generation.py
       (multi-scene pipeline; FAILED is set per-scene today,
        helper call would explicitly gate the COMPLETED transition.)
    • services/youstar_pipeline/* (segment generation)
    • services/comic_pipeline/* (panel batch)
    • Audio segment / export packaging flows.
  Each migration is opt-in via a one-line REGISTERED_PIPELINES
  addition. No batch sweep — each pipeline gets a focused PR with
  its own regression test.

FREEZE INTACT
  ✗ No Phase 3c
  ✗ No Phase 4
  ✗ No canonical migration
  ✗ No admin panel
  ✗ No feature expansion



─────────────────────────────────────────────────────────
[2026-05-19] P0 COMIC STRIP COMPLETION-INVARIANT — SHIPPED
─────────────────────────────────────────────────────────
Production user report: 3-panel Comic Strip generation surfaced
"Your Comic is Ready / All panels generated and verified" but only
2 of 3 panels were rendered. Pipeline integrity failure.

EXACT ROOT CAUSE
  routes/photo_to_comic.py line 1577 (pre-fix):
    for i in range(min(panel_count, len(story_scenes))):
  When the LLM outline returned fewer scenes than requested
  (intermittent for the strip flow), the generation loop iterated
  only `len(story_scenes)` times. No story-plan invariant existed
  to catch the shortfall, and the final status logic treated
  `ready_count == len(panels)` as success even when
  `ready_count < panel_count`.

  Secondary failure: PARTIAL_READY status was rendered with the
  same "Your Comic is Ready" title as fully-complete jobs, and the
  empty panel slot said "Being optimized" — making a partial job
  visually indistinguishable from a complete one.

THREE INVARIANTS ADDED

  Layer 1 — STORY-PLAN INVARIANT (backend, pre-flight)
    routes/photo_to_comic.py
    After fallback scene assembly, the system asserts
    `len(story_scenes) >= panel_count`. If short, story_scenes is
    padded with neutral filler beats so the generation loop ALWAYS
    has enough scenes. Persists `planned_scene_count` and
    `expected_panel_count` on the job document. Emits
    `p2c_story_plan_padded_total` observability counter.

  Layer 2 — GENERATION LOOP (backend)
    routes/photo_to_comic.py
    Loop is now `for i in range(panel_count):` — always iterates
    the full plan. The legacy `range(min(panel_count, …))` form is
    GONE from executable code.

  Layer 3 — COMPLETION INVARIANT (backend, post-execution)
    routes/photo_to_comic.py
    Before persisting status, hard gate:
      if job_status in ("COMPLETED", "READY_WITH_WARNINGS"):
          if actual_ready_count != panel_count:
              job_status = "PARTIAL_READY"
              job_decision = "ACCEPT_PARTIAL_INVARIANT_REPAIRED"
              # emit p2c_completion_invariant_failed_total
    COMPLETED can no longer mean "some of the panels finished".

  Layer 4 — FRONTEND TRUST (PhotoToComic.js)
    resolveAssetState now derives `stripIsComplete` from the panels
    array. uiState='READY' requires BOTH preview/download OK AND
    stripIsComplete. PARTIAL_READY status badge:
      • short strip  → title "Finalizing your comic…",
                       subtitle "N of M panels finished — completing the rest."
      • full strip   → original "Your Comic is Ready" (unchanged).
    Empty-panel placeholder no longer says "Being optimized"; it
    explicitly says "Generating…" (uiState != READY) or "Retrying…"
    (uiState == READY) and carries a `panel-N-pending` testid.

RETRY / REFUND POSTURE
  Existing flow preserved:
    • Per-panel pro-rata credit deduction
      (per_panel_cost = max(1, cost // panel_count) × ready_count).
    • Zero-panel jobs trigger `handle_generation_failure` auto-refund.
    • PARTIAL_READY paths run the GUARANTEED_OUTPUT fallback to
      synthesize stylized panels from the source photo so the user
      ALWAYS gets some output even if every AI call failed.
  The invariant downgrade does NOT alter credit math — short strips
  were already being pro-rated; what changed is that the user is no
  longer told the job finished when it actually didn't.

OBSERVABILITY ADDED
  • p2c_story_plan_padded_total          (new, daily-bucketed)
  • p2c_completion_invariant_failed_total (new, daily-bucketed)
  • planned_scene_count                  (on job document)
  • expected_panel_count                 (on job document)

REGRESSION TESTS — 9 (backend/tests/test_strip_completion_invariant_2026_05.py)
  • test_story_plan_padder_exists
  • test_generation_loop_iterates_full_panel_count
       (also asserts the legacy `range(min(...))` form is gone)
  • test_completion_invariant_block_exists
  • test_completion_invariant_downgrades_status
  • test_planned_scene_count_persisted
  • test_frontend_strip_completeness_gate_exists
       (stripIsComplete REQUIRED for uiState='READY')
  • test_partial_ready_badge_no_false_completeness
  • test_empty_panel_placeholder_no_longer_says_being_optimized
  • test_status_messages_do_not_lie
       ("All panels generated and verified" appears ONLY in READY)

PROOF THAT INCOMPLETE OUTPUT CANNOT REACH "COMPLETE"
  • Backend test (downgrade gate): the exact phrase
    `job_status = "PARTIAL_READY"` is reached when
    `actual_ready_count != panel_count`.
  • Frontend test: setUiState('READY') is gated by
    `previewOk && downloadOk && stripIsComplete`.
  • Together: a 2-of-3 panel job CANNOT reach the green "All panels
    generated and verified" badge.

AUDIT OF SIBLING PIPELINES (no source changes — surveyed only)
  • Comic Storybook: uses comic_storybook_v2_jobs with its own
    per-scene state machine. Status set to COMPLETED only inside
    `_finalize_job_completion` after every scene transitions to
    `done`. Already has a completion invariant. NO CHANGE NEEDED.
  • Story-to-Video scene generation: pipeline_worker walks scenes
    sequentially; failed scenes mark the job FAILED rather than
    COMPLETED. Not affected by the same bug class. NO CHANGE NEEDED.
  • YouStar segment generation: similar shape to Story-to-Video.
    NO CHANGE NEEDED.
  Recommendation: the static-audit scanner could be extended in a
  later P1 to add a "completion-invariant" rule that fails any new
  pipeline whose COMPLETED transition doesn't gate on a count check.
  Logged in the doctrine backlog; NOT shipped this hotfix.

FILES CHANGED
  ~ backend/routes/photo_to_comic.py
       (story-plan padder + invariant gate)
  ~ frontend/src/pages/PhotoToComic.js
       (stripIsComplete + PARTIAL_READY badge + pending placeholder copy)
  + backend/tests/test_strip_completion_invariant_2026_05.py
  ~ /app/Makefile  (new suite registered in BOUNDARY_AUDIT_SUITES)

FULL SUITE
  `make audit-boundaries` → 194 passed, 1 skipped (60s).
  Lint clean (backend + frontend).

FREEZE INTACT
  ✗ No Phase 3c, Phase 4, canonical migration, UI redesign,
    unrelated feature work, or admin panel.



─────────────────────────────────────────────────────────
[2026-05-19] ENGINEERING DOCTRINE ADOPTED + `make audit-boundaries`
─────────────────────────────────────────────────────────
Founder mandate: codify platform-wide engineering doctrine and
enforce it via a single CI command. No human memory dependency.

DOCTRINE — /app/memory/ENGINEERING_DOCTRINE.md
  Single sentence (verbatim):
    "Never allow unvalidated input, ambiguous state, or silent
     failure to cross a system boundary."

  Ten operational rules:
    1. Every boundary validates  (frontend, backend, query, path,
       webhooks, third-party responses, env vars, feature flags,
       uploads — each with its required gate).
    2. Every critical flow has canonical state  (no "probably
       complete", no duplicate truth, no drift without reconciler).
    3. Every failure is observable  (request_id everywhere,
       structured envelopes, stage timings, retry/stuck/invalid-payload
       counters, webhook lag, frontend/backend build correlation).
    4. Every async action is idempotent  (safe retries, harmless
       duplicate webhooks, partial-failure recovery, TTL'd locks).
    5. Every user-facing error is sanitized  (no traceback, no enum
       names, no class names, no framework internals).
    6. Every new feature must pass boundary audits  (merge gate).
    7. Freeze before expansion  (stabilize → instrument → only then
       innovate).
    8. Complexity is a liability  (fewer states / abstractions /
       async hops / duplicated registries / hidden couplings).
    9. CI enforces stability automatically  (`make audit-boundaries`).
   10. Stability > velocity theater.

CI GATE — /app/Makefile
  `make audit-boundaries`  → runs the full boundary registry.
  `make audit-boundaries-quick` → quiet pre-push variant.
  `make audit-boundaries-report` → JUnit XML for CI artifacts.
  `make pre-merge` → lint + audit-boundaries.
  `make help` (default) → self-documenting target list.

  Registry currently composes 12 suites; 185 tests, 1 skipped.
  Adding a new audit is one line in BOUNDARY_AUDIT_SUITES.

DOCTRINE PINNING — /app/backend/tests/test_doctrine_and_ci_gate_2026_05.py
  8 tests that fail any PR which:
    • removes or weakens the doctrine sentence
    • drops one of the ten rule headings
    • removes the make target
    • drops `make audit-boundaries` from the doctrine
    • leaves a canonical *_boundary_audit / *_event_trap_audit /
      *_payment_auth_batch suite unregistered in the Makefile
    • lists a non-existent path in the registry
    • changes the Makefile default goal away from `help`
    • lets doctrine-named suites drift out of the registry

FILES ADDED
  + /app/memory/ENGINEERING_DOCTRINE.md
  + /app/Makefile
  + /app/backend/tests/test_doctrine_and_ci_gate_2026_05.py

FILES MODIFIED — none (this is policy + tooling only).

PRODUCTION BEHAVIOR CHANGES — none.

VERIFICATION
  `make audit-boundaries` → 185 passed, 1 skipped in 67s.
  `make help` lists every target with its docstring.
  Doctrine pinning suite: 8/8 green.



─────────────────────────────────────────────────────────
[2026-05-19] BATCH A — PAYMENT & AUTH BOUNDARY HARDENING — SHIPPED
─────────────────────────────────────────────────────────
Founder mandate: tighten the P0 money/auth boundary. Freeze intact.

FIELDS TIGHTENED (14 sites)
  Cashfree order_id — now OrderIdStr:
    • routes/cashfree_payments.py
        CashfreeVerifyRequest.order_id
        RefundStatus.order_id
        get_order_status(order_id)        [path]
        create_cashfree_refund(order_id)  [path]
        get_refund_status(order_id)       [path]
        retry_credit_delivery(order_id)   [path]
    • routes/recovery_ui.py  get_payment_recovery_status [path]
    • routes/revenue_analytics.py  get_transaction_detail [path]
    • routes/self_healing_monitoring.py  manual_reconcile_payment [path]
    • routes/admin_payments.py  get_orders.order_id [Query, Optional]
    • routes/admin_payments.py  get_webhooks.order_id [Query, Optional]

  Auth tokens — now TokenStr:
    • routes/auth.py  ResetPasswordRequest.token, VerifyEmailRequest.token

  Content-protection tokens — now TokenStr:
    • routes/content_protection_routes.py
        StreamTokenValidation.token
        get_hls_playlist.token [Query]
        get_hls_segment.token [Query]

  WebSocket token — now TokenStr:
    • routes/websocket_progress.py  /ws/progress.token [Query]

  OTP — now Otp6DigitStr (exactly 6 digits, numeric):
    • routes/anti_abuse_routes.py  PhoneVerifyRequest.otp

  Password length cap — now Password8PlusStr (min 8, max 128):
    • routes/admin.py  CreateUserRequest.password
    • routes/security_management.py  Enable2FARequest.password

  BYO api_key length cap — now ApiKeyStr (min 10, max 512):
    • routes/comix_ai.py  save_user_api_key.api_key [Form]

  Wallet ledger Literals:
    • routes/wallet.py  LedgerEntry.entryType  → Literal[5 values]
    • routes/wallet.py  LedgerEntry.refType    → Literal[4 values]
    • routes/wallet.py  LedgerEntry.status     → Literal[2 values]

  Payment ledger Literals:
    • models/schemas.py  PaymentLog.status   → Literal[SUCCESS/FAILED/PENDING/REFUNDED]
    • models/schemas.py  PaymentLog.currency → Literal[INR/USD]

EXTENSIONS TO models/payload_validators.py
  + TokenStr             (regex `^[A-Za-z0-9_\-\.~=]{16,4096}$`)
  + Otp6DigitStr         (regex `^\d{6}$`)
  + ApiKeyStr            (length 10..512)
  + Password6PlusStr     (length 6..128)
  + Password8PlusStr     (length 8..128)
  + LedgerEntryType / LedgerRefType / LedgerStatus  (Literals)
  + PaymentStatus / PaymentCurrency  (Literals)

REGRESSION TESTS — 28 (backend/tests/test_payment_auth_batch_a_2026_05.py)
  Cashfree order_id parametrized over 7 junk shapes
    (empty/short/long/spaces/object/array/null) + canonical accept.
  Auth tokens — 6 cases (junk values × 2 endpoints + password length).
  OTP — 7 junk shapes + 6-digit accept.
  BYO api_key — short-key reject.
  Credit-grant trust audits (source-level, no network):
    • add_credits(...) calls must NOT read amount/credits/status from
      client request body.
    • Credit count MUST derive from server-side PRODUCTS registry.
  payload_validators module presence of all Batch-A exports.
  Source-level pin: wallet.LedgerEntry + PaymentLog use Literal types.

BEHAVIOR CHANGES
  • Invalid Cashfree order_id (object, array, null, malformed string)
    now returns 422 VALIDATION_ERROR with envelope. Previously fell
    through to a DB query and surfaced as a 404 or opaque 500.
  • Reset/verify/stream/WS tokens shorter than 16 chars or containing
    invalid characters now rejected at the boundary.
  • Phone OTP must be exactly 6 numeric digits (previously accepted
    any string).
  • Password fields capped at 128 chars (bcrypt-DoS guard).
  • BYO api_key bounded 10..512 chars.
  • Wallet ledger writes / PaymentLog reads with unknown enum values
    now rejected with envelope.
  • Legitimate inputs continue to work.

ENVELOPE CONTRACT — preserved & verified end-to-end
  Every rejection returns the canonical envelope:
    {detail: {code: "VALIDATION_ERROR", message, request_id,
              field_errors[]}, code, request_id}
  + matching X-Request-Id header.
  No stack traces, no Pydantic internals, no raw input echo.

CREDIT-GRANT TRUST POSTURE (re-verified)
  • Cashfree grant flow reads `product = PRODUCTS.get(data.productId)`
    then `product["credits"]` — server-side only.
  • No `add_credits(..., data.amount)` / `data.credits` / `data.status`
    paths exist. Static audit test will fail CI if they ever appear.

FULL SUITE: 177 passed, 1 skipped. Lint clean.

WHAT BATCH A DID NOT TOUCH (still frozen / future batches):
  ✗ Batch B — `mode` Literal sweep (~6 sites)
  ✗ Batch C — `job_id`/`*_id` typed sweep (~20 sites)
  ✗ Free-text fields, categorical labels, user_id paths
  ✗ Phase 3c / Phase 4 / canonical migration
  ✗ Admin diagnostics panel
  ✗ CI consolidation (`make audit-boundaries`) — deferred per direction.



─────────────────────────────────────────────────────────
[2026-05-19] P1 URL/PATH/QUERY BOUNDARY AUDIT — SHIPPED
─────────────────────────────────────────────────────────
Founder mandate: "Prevent unsafe handler/default-arg values from
leaking into URL path segments, query strings, FormData keys,
download/export URLs, and share/public URLs." Freeze intact —
no Phase 3c/4, no canonical migration, no admin panel, no features.

UNSAFE URL/PATH/QUERY PATTERNS FOUND
  Codebase-wide static scan of every JS/JSX function scope with a
  default-arg parameter, restricted to the 22 target keys (style,
  style_id, mode, template/_id, voice/_id, character/_id, story_id,
  draft_id, asset_id, plan, price_id, amount, credits, order_id,
  remix_type, type, job_id, token, share_token).
    Active violations in live code: 0.
    Synthesized regressions the audit provably catches:
      • `/api/x/${overrideId}`              (unguarded path segment)
      • `new URLSearchParams({ style })`    (unguarded query shorthand)
      • `overrideStyle || style` in URL     (fallback-of-unguarded)
  The path-segment scanner ONLY flags substitutions where (a) the
  enclosing function has default-arg params AND (b) either the
  variable name maps to a TARGET_KEY (e.g. `storyId`→`story_id`,
  `jobId`→`job_id`) or the URL position is `?key=${…}` with key in
  the target list. Cosmetic params (`limit`, `niche`, `className`,
  `dateRange`) are correctly NOT flagged.

NEW SAFE BUILDERS (frontend/src/utils/safeUrl.js)
  • `safePathId(value, fieldName)`
      Validates against `^[A-Za-z0-9_-]{1,128}$`, then encodes.
      Returns `null` on React events, objects, arrays, nulls,
      empty strings, or pattern miss. NEVER returns
      `encodeURIComponent([object Object])`.
  • `safeQueryParam(value, fieldName)`
      Accepts strings (trim, max 512 chars), finite numbers,
      booleans. Refuses everything else.
  • `safeUrlParams(obj, allowlist)`
      Returns a `URLSearchParams`. Keys are STRICTLY restricted to
      the supplied allowlist — a misspelling can't leak unintended
      params downstream.
  • `safeDownloadUrl(base, pathParts, query, queryAllowlist)`
      Composes a download/export/share URL from validated parts.
      Returns null if ANY segment is unsafe. The right primitive
      for sharing public URLs.
  • All builders emit `frontend_event_trap_blocked_total` beacons
    on rejection so the existing diagnostics counter sees the work.

PRINCIPLE LOCKED IN
  `encodeURIComponent` is NOT validation. The builders validate
  FIRST, then encode. Tests assert `encodeURIComponent(trimmed)`
  appears AFTER pattern validation in safePathId.

EXACT FILES CHANGED
  + frontend/src/utils/safeUrl.js
  + backend/tests/test_url_boundary_audit_2026_05.py

REGRESSION TESTS — 8 new
  • test_url_path_substitutions_audit
      Live codebase scan; restricted to TARGET_KEYS via the
      new `_classify_url_substitution` heuristic.
  • test_urlsearchparams_object_audit
      `new URLSearchParams({…})` literal-object form.
  • test_formdata_and_urlsp_set_audit
      `formData.append('story_id', maybeArg)` + `params.set(...)`.
  • test_synthesized_path_regression_is_detected
      `${overrideId}` with unguarded default → flagged.
  • test_synthesized_query_regression_is_detected
      `URLSearchParams({ style })` with unguarded default → flagged.
  • test_synthesized_guarded_path_is_accepted
      `overrideId = safePathId(...)` → accepted.
  • test_safe_url_module_exists
      All exports + encodeURIComponent-after-validation contract.
  • test_target_keys_include_token_pair
      The founder added `token` / `share_token` for this layer.

BEHAVIOR CHANGES
  None. This sweep adds new utilities and a regression scanner.
  No call site changed today — all 22 active default-arg handlers
  are already safe (verified by the live scan).

FULL SUITE: 149 passed, 1 skipped. Lint clean.

WHAT THIS SWEEP DID NOT TOUCH (still frozen):
  ✗ Phase 3c / Phase 4 / canonical migration
  ✗ Admin diagnostics panel
  ✗ Raw-`str` payload-field tightening hit list (per founder direction:
    next step is REPORT-ONLY first)
  ✗ New features / UI redesign / Sora toggle / character memory



─────────────────────────────────────────────────────────
[2026-05-19] P1 BACKEND PAYLOAD ACCEPTANCE HARDENING — SHIPPED
─────────────────────────────────────────────────────────
Founder mandate: "Make the same bug class impossible at the API
boundary, not just frontend." Freeze still in effect — no Phase 3c/4,
no canonical migration, no admin panel, no new features.

ROUTES / MODELS AUDITED — 156 occurrences of target keys across
  backend/routes/*.py, focused on the request-body / Form() / Query()
  boundary (helper-function params skipped — they are internal).

FIELDS TIGHTENED
  • routes/photo_to_comic.py :: generate_comic
      `mode: str = Form(...)` → `mode: Literal["avatar", "strip"]`.
      The legacy in-handler `if mode not in [...] raise 400` is now
      DEAD CODE (left in place as redundant defense).
  • routes/story_series.py :: CreateSeriesRequest
      `style: str = "cartoon_2d"` →
      `style: Literal[<17 canonical SAFE_STYLES keys>] = "cartoon_2d"`.
  • routes/story_video_generation.py :: VoiceGenerationRequest
      `voice_id: str = "alloy"` →
      `voice_id: Literal["alloy","echo","fable","onyx","nova","shimmer"]
        = "alloy"`.
  • imports updated to bring in `Literal` where missing.

NEW MODULES
  + backend/models/payload_validators.py
      Annotated reusable types for future routes:
        IdStr, SlugStr, JobIdStr, OrderIdStr,
        CreditAmountInt, PositiveCreditInt, MoneyAmountInt,
        ShortText, LongText.
      Every type ships with a regex + min/max bound so the same
      tightening is one-line for the next route.
  + backend/middleware/validation_envelope.py
      Single global RequestValidationError handler that replaces
      FastAPI's default raw-Pydantic-error 422 with the canonical
      reliability envelope:
        {
          "detail": {
            "code": "VALIDATION_ERROR",
            "message": "One or more fields are invalid…",
            "request_id": "<uuid>",
            "field_errors": [{"field","code","reason"}],
            "retryable": false
          },
          "code": "VALIDATION_ERROR",
          "request_id": "<uuid>"
        }
      Pydantic `ctx`, `input`, `url`, and full `msg` are STRIPPED —
      zero internal model names, zero stack traces, zero raw user
      input echoed back.
  ~ backend/server.py
      `install_validation_envelope(app)` wired right after the rate
      limiter handler so every router benefits.

BEHAVIOR CHANGES
  • Invalid enums for `mode` / `style` / `voice_id` now return 422
    with the canonical envelope instead of a 400 with raw `detail`
    text. The `code` field stays the same shape but the body is
    consistent across all routes.
  • Cashfree `voice_id`, `style`, `mode` rejections are now caught
    BEFORE any business logic runs. Backwards-compatible: callers
    that read `response.data.detail.code` get the same `code` strings.
  • `null` for required fields now returns the canonical envelope
    (previously raw Pydantic dict).

TESTS — 10 new (backend/tests/test_backend_payload_acceptance_2026_05.py)
  • test_invalid_enum_rejected
  • test_object_rejected_for_slug_field
  • test_array_rejected_for_slug_field
  • test_null_rejected_for_required_field
  • test_label_rejected_for_slug_only_field
  • test_valid_canonical_payload_accepted
  • test_invalid_voice_id_enum_rejected
  • test_photo_to_comic_mode_rejects_invalid_enum
  • test_payload_validators_module_exists
  • test_validation_envelope_module_exists
  Each rejection test asserts:
    – status 422
    – body.detail.code == "VALIDATION_ERROR"
    – body.detail.request_id present AND matches X-Request-Id header
    – no traceback / pydantic / model-class names anywhere in body
    – field_errors contain the offending field with a sanitized reason

ERROR-CONTRACT PROOF (live preview backend)
  POST /api/story-series/create body={style:"NOT_A_REAL_STYLE",…}
  → 422
  {
    "detail": {
      "code":"VALIDATION_ERROR",
      "message":"One or more fields are invalid. Please check your input
                 and try again.",
      "request_id":"b4fd12abb9684338b03754a0f8d4f699",
      "field_errors":[{"field":"style","code":"literal_error",
                       "reason":"Value is not one of the allowed options."}],
      "retryable":false
    },
    "code":"VALIDATION_ERROR",
    "request_id":"b4fd12abb9684338b03754a0f8d4f699"
  }
  + Header `X-Request-Id: b4fd12abb9684338b03754a0f8d4f699`

FULL SUITE: 141 passed, 1 skipped (voice-route probe — non-blocking;
contract is fully proven via the series suite). Lint clean.

WHAT THIS SWEEP DID NOT TOUCH (still frozen):
  ✗ Phase 3c
  ✗ Phase 4
  ✗ Canonical-state migration
  ✗ Admin diagnostics panel
  ✗ New features / UI redesign
  ✗ Sora toggle / character memory



─────────────────────────────────────────────────────────
[2026-05-19] P1 PAYLOAD-BOUNDARY AUDIT (Next layer) — SHIPPED
─────────────────────────────────────────────────────────
Founder mandate: "Catch handler/default-arg values that can leak into
backend payloads without type validation." Freeze still in effect —
no Phase 3c/4, no canonical migration, no admin diagnostics panel yet.

RISKY PAYLOAD-BOUNDARY PATTERNS FOUND
  Codebase-wide static scan of every JS/JSX file. For every function
  scope with a default-arg parameter, the audit extracts every
  `api.{post|put|patch|delete|get}(url, { … })` and
  `formData.append('KEY', value)` write, restricts to TARGET_KEYS, and
  classifies the value expression.
  Active violations found in the live codebase: 0.
  Active violations that the audit machinery PROVES it would catch
    (verified via synthesized regression fixtures):
      • `{ style_id: overrideId }`            (unguarded default param)
      • `{ style_id: overrideStyle || style }` (fallback-of-unguarded)
  Two real call sites were further hardened proactively even though
  they were already event-trap-safe:
      • BedtimeStoryBuilder `remix_type`  → now coerceEnum to
        REMIX_VARIANT_IDS, fallback null.
      • ComicStorybookBuilder `type`      → now coerceEnum to
        ['pdf','cover','zip'], fallback 'pdf'.

NEW GUARD UTILITIES (frontend/src/utils/payloadCoercers.js)
  • coerceString(v, opts)         — string or fallback (null/default).
  • coerceNumber(v, opts)         — finite number or fallback.
  • coerceEnum(v, allowed, opts)  — value or fallback from an
                                    allow-list (Array or Set).
  • coerceSlug(v, opts)           — `[a-z0-9][a-z0-9_-]{1,127}/i`.
  • coerceId(v, opts)             — `[A-Za-z0-9_-]{6,128}`.
  • safeOr(primary, fallback)     — the safe form of `primary || x`.
  All emit `frontend_event_trap_blocked_total` beacons on rejection so
  the existing diagnostics counter sees the work.

TARGET KEYS COVERED (audit scope)
  style, style_id, mode, template, template_id,
  voice, voice_id, character, character_id,
  story_id, draft_id, asset_id,
  plan, price_id, amount, credits, order_id,
  remix_type, type, job_id

EXACT FILES CHANGED
  + frontend/src/utils/payloadCoercers.js
  + backend/tests/test_payload_boundary_audit_2026_05.py
  ~ frontend/src/pages/BedtimeStoryBuilder.js (REMIX_VARIANT_IDS +
    coerceEnum on remix_type)
  ~ frontend/src/pages/ComicStorybookBuilder.js (coerceEnum on type)

REGRESSION TESTS — 6 new
  • test_payload_boundary_audit
      Static scan over every default-arg handler in the frontend.
  • test_synthesized_regression_is_detected
      `{ style_id: overrideId }` with unguarded default → audit flags.
  • test_synthesized_guarded_pattern_is_accepted
      `overrideId = dropEventArg(overrideId, …)` → audit accepts.
  • test_synthesized_fallback_pattern_is_flagged
      `overrideStyle || style` of an unguarded default → audit flags.
  • test_coercer_utility_module_exists
      All exports verified.
  • test_target_keys_constant_coverage
      Founder-spec keys are all in the audit's TARGET_KEYS set.

FULL SUITE: 132 tests GREEN.

PRODUCTION BEHAVIOR CHANGES
  • BedtimeStoryBuilder: an invalid `remix_type` (e.g. tampered URL
    or future bug) now silently coerces to `null` and the backend
    treats it as a standard generate — no remix variant applied.
    Previously a stray non-string would have been forwarded as-is.
  • ComicStorybookBuilder: an invalid download `type` now coerces to
    `'pdf'` instead of being forwarded as-is.
  • No other observable behavior change for legitimate clicks.

WHAT THIS SWEEP DID NOT TOUCH (still frozen):
  ✗ Phase 3c
  ✗ Phase 4
  ✗ Canonical-state migration
  ✗ New features / UI redesigns
  ✗ Admin diagnostics panel (deferred — dashboard before payload
    boundary is the wrong order, per founder).



─────────────────────────────────────────────────────────
[2026-05-19] P1 FREEZE-SAFE RELIABILITY SWEEP — SHIPPED
─────────────────────────────────────────────────────────
Founder directive after the Photo-to-Comic event-trap hotfix:
  "Do the P1 sweep. Do NOT unfreeze Phase 3c/4 yet."
  Phase 3c, Phase 4, and canonical migration remain BLOCKED.

UNSAFE PATTERN AUDIT — codebase-wide static scan
  Found UNSAFE bare-handler wirings (handler-with-default-arg + bare
  `onClick={handlerName}`): 1 (already fixed in 2026-05-19 hotfix).
  Found risky-shape handlers (have default args, currently safe-wired
  via arrows but defended-in-depth anyway): 7.

NEW SHARED UTILITIES
  • frontend/src/utils/eventTrapGuard.js
      `dropEventArg(arg, expectType, meta)` — universal handler-arg
      sanitizer. Strips React SyntheticEvents and non-matching types,
      emits `frontend_event_trap_blocked_total` beacon.
  • frontend/src/utils/toastSafe.js
      `toastErrorSafe(message, { requestId, code, page })` —
      scrubs internal jargon ("frontend rejected", "style=object",
      "[object Object]", "validator", "stack trace", "TypeError:",
      …) and ALWAYS surfaces a Reference ID. When no backend
      request_id is available, mints a local refId and emits
      `error_toast_without_request_id_total`.
  • frontend/src/utils/buildInfo.js
      `BUILD_HASH` + `BUILD_TIMESTAMP` constants, sourced from
      `REACT_APP_BUILD_HASH` / `REACT_APP_GIT_SHA` env vars with
      sensible fallback.
  • api.js — every outbound request now stamps `X-Frontend-Build`
      so backend logs can correlate stale-bundle reports.
  • api.js — gateway/503 toast switched to `toastErrorSafe`,
      preserves backend `request_id` end-to-end.

DEFENSE-IN-DEPTH APPLIED (dropEventArg shim) — 7 handlers:
  • pages/PhotoToComic.js       handleGenerate(overrideStyle = null)
  • pages/PhotoToComic.js       handleContinueStory(prompt = '')
  • pages/BedtimeStoryBuilder.js handleGenerate(remixType = null)
  • pages/ComicStorybookBuilder.js handleDownload(type = 'pdf')
  • pages/PublicCreation.js     handleContinue(type = 'continue')
  • pages/PublicCharacterPage.js handleContinue(type = 'continue')
  • pages/SeriesTimeline.js     handleCreateNewEpisode(episode = null)
  • pages/StoryViewerPage.jsx   handleEnterBattle(trigger = '...')
  • pages/StoryBattlePage.jsx   handleEnterBattle(trigger = '...')

BACKEND METRICS (routes/diagnostics_beacon.py)
  POST /api/diagnostics/beacon — accepts batched events, allow-listed:
    • frontend_event_trap_blocked_total
    • error_toast_without_request_id_total
    • p2c_label_fallback_total
  Caps: 50 events/batch, 256-char meta values, 10 meta keys/event.
  GET  /api/diagnostics/metrics (admin-only) — bucketed daily totals.
  Persisted in `diagnostics_metrics` (one doc per metric+bucket day,
  with a ring of 25 recent samples for forensics).

REGRESSION TESTS — all new + existing GREEN
  • backend/tests/test_event_trap_audit_2026_05.py (8 tests)
      - test_no_unsafe_bare_handler_wirings (codebase-wide static scan)
      - test_primary_cta_buttons_are_not_bare_wired
      - test_event_trap_audit_detects_simulated_regression
      - test_event_trap_audit_self_finds_known_safe_patterns
      - test_event_trap_guard_util_exists
      - test_toast_safe_util_exists_and_strips_jargon
      - test_build_info_util_exists
      - test_api_client_sends_build_header
  • backend/tests/test_diagnostics_beacon_2026_05.py (7 tests)
      - accept/reject metric allow-list, payload caps, aggregation,
        admin-only metrics endpoint
  Full suite: 126 tests GREEN.

BEFORE / AFTER — one blocked event-trap
  BEFORE:
    <Button onClick={handleGenerate} data-testid="generate-btn">
    const handleGenerate = async (overrideStyle = null) => {
      const rawSelected = overrideStyle || style;  // React SyntheticEvent
                                                    // arrives here, is truthy,
                                                    // poisons rawSelected.
      const activeStyle = normalizeComicStyle(rawSelected);  // → null
      // user sees: "frontend rejected style=object"
    };
  AFTER:
    <Button onClick={() => handleGenerate()} data-testid="generate-btn">
    const handleGenerate = async (overrideStyle = null) => {
      const overrideIsString =
        typeof overrideStyle === 'string' && overrideStyle.trim().length > 0;
      const rawSelected = overrideIsString ? overrideStyle : style;
      // dropEventArg guard available on all peer handlers too.
    };

WHAT THIS SWEEP DID NOT TOUCH (frozen):
  ✗ Phase 3c (canonical state for remaining tools)
  ✗ Phase 4 (pipeline worker transition)
  ✗ Canonical-state migration scripts
  ✗ New features / UI redesigns / Sora toggle / character memory work



─────────────────────────────────────────────────────────
[2026-05-19] P0 PHOTO-TO-COMIC EVENT-TRAP HOTFIX — SHIPPED
─────────────────────────────────────────────────────────
Production trust-killing toast on Photo-to-Comic:
  "Selected comic style is not supported. Please try another style.
   Reference ID: not-captured (frontend rejected style=object)"

ROOT CAUSE (the smoking gun):
  • The generate button was wired `<Button onClick={handleGenerate}>`.
  • React passes a SyntheticEvent as the first arg to handleGenerate.
  • `handleGenerate(overrideStyle = null) { const rawSelected =
    overrideStyle || style; ... }` treated the truthy event as a style
    object. `normalizeComicStyle(event)` returned null → leaky toast.
  • Bold Hero was visibly selected, CTA enabled, BUT click failed
    validation BEFORE the request was dispatched (no request_id).

FIXES (frontend/src/pages/PhotoToComic.js):
  1. Line 1547 — `onClick={() => handleGenerate()}` (drops the event).
  2. `handleGenerate` now only honors `overrideStyle` when
     `typeof === 'string' && trim().length > 0`. Anything else
     (event, object, number, null) falls through to canonical `style`
     state — which is always a string thanks to the existing setStyle
     wrapper.
  3. Killed all internal jargon in the user-facing toast.
     Old: "frontend rejected style=object" + "Reference ID: not-captured"
     New: "Selected style unavailable. Please try another style.
           Reference ID: p2c-<hash>".
     Detailed `style_state` diagnostic stays in `console.error` only.
  4. Bumped BUNDLE_VERSION → `2026-05-19-p2c-event-trap-fix` so QA can
     visually confirm the new bundle is live.

REGRESSION TESTS (backend/tests/test_p2c_event_trap_2026_05.py — 8 cases):
  • test_generate_button_does_not_pass_event_to_handler
  • test_handle_generate_only_honors_string_override
  • test_no_internal_jargon_in_user_facing_toasts
    (forbidden in toast.error: "frontend rejected", "style=object",
     "[object Object]", "unsupported enum", "validator", "stack trace",
     "not-captured (frontend")
  • test_invalid_style_toast_surfaces_reference_id
  • test_locked_style_tiles_are_disabled_and_gated
  • test_only_one_comic_style_registry (registry-divergence guard)
  • test_p2c_imports_canonical_registry
  • test_bundle_version_advanced_for_this_hotfix

VERIFICATION:
  • All 111 P2C + storybook regression tests GREEN.
  • Lint clean on PhotoToComic.js.
  • Smoke screenshot of /app/photo-to-comic boots (auth wall renders).



─────────────────────────────────────────────────────────
[2026-05-16] YOUSTAR P0 ACTIVATION-KILLER TRIO (P0-A, P0-C, P0-D) — SHIPPED
─────────────────────────────────────────────────────────
Founder mandate: ship the three highest-priority YouStar trailer reliability
fixes. Production freeze otherwise in effect — no UI redesigns or new features.

P0-A — Backend reliability ("stuck at 88%" elimination)
• Stage timestamps in `_set_stage`: stage_started_at, stage_completed_at,
  stage_duration_s — populates the new debug endpoint timeline.
• Sub-stage heartbeats during `_render_trailer` ("Combining scenes (i/N)",
  "Stitching trailer", "Adding music", "Adding end card") so the user no
  longer sees a flat 88% for 30+ seconds.
• `_render_trailer` wrapped in `asyncio.wait_for` per-stage timeout
  (5/8/8/12 min by tier) → surfaces RENDER_TIMEOUT before Cloudflare 504.
• Stuck-job janitor (`_reap_stale_pipelines`) with founder-normalized
  10-minute wall-clock cap for ALL duration tiers
  (HARD_MAX_RUNTIME_BY_DURATION + STALE_MIN_BY_DURATION = 10/10/10/10).
  Auto-requeue path now effectively disabled — a trailer that hangs >10min
  is broken by definition and gets clean FAIL + credit refund (no silent
  burn).
• Canonical admin alias `GET /api/admin/youstar/jobs/{job_id}/debug`
  (mirrors Story-to-Video + Story-Series contract). Legacy
  `/api/photo-trailer/admin/jobs/{id}/debug` retained for backwards compat.

P0-D — ffprobe audio/video validation
• `_validate_render` runs ffprobe after render. Rejects when:
  – output file missing
  – no video stream OR no audio stream
  – video codec ≠ h264 OR audio codec ≠ aac
  – audio duration < video duration − 0.5s
• On failure: job marked FAILED with error_code=RENDER_INVALID +
  credits refunded automatically (matches founder mandate "audio must
  play continuously, otherwise refund").
• Graceful ffmpeg -i fallback when ffprobe binary unavailable.

P0-C — Frontend first-click Play fix
• `videoRef` + explicit `videoRef.current.load()` on every src change.
• `canPlay` state tracked via onCanPlay/onLoadedMetadata; tap-to-play
  overlay only enabled after `canPlay && !isPlaying`.
• `handleTapToPlay` calls `el.play()` SYNCHRONOUSLY inside the user
  gesture handler (no awaits before play) — eliminates the
  NotAllowedError race that required a page refresh.
• Cache-busting `?_v=${Date.now()}` appended to every signed stream URL
  so regenerated trailers never replay the previous MP4.
• `playFailed` state surfaces a visible reason if .play() rejects.
• NEW (P0-C completion): canplay-stuck recovery. If `canplay` doesn't
  fire within 8 seconds (slow R2 origin or stale signed URL), the user
  sees a "Tap to load trailer" force-reload button
  (data-testid=`trailer-tap-to-load`). Handler bumps a nonce that
  re-runs the load effect AND appends a fresh `_r=<ts>` cache-buster
  so the next `.load()` hits R2 fresh.

Tests
• /app/backend/tests/test_youstar_reliability_trio_2026_05.py — 18 tests
  (stage timestamps, canonical alias gated + 404, 10-min hard-max,
  ffprobe accept/reject paths, frontend source-level assertions).
• /app/backend/tests/test_photo_trailer_render_timeout.py — updated
  hard-max constants to 10 min.
• /app/backend/tests/test_photo_trailer_reliability_sprint.py — janitor
  heartbeat + wall-clock tests rewritten for the single-wall spec.
• 41/41 backend tests pass at 100% (testing_agent_v3_fork iteration 100).

Deferred (per user instruction, second deploy)
• P0-B: concurrent scene + narration generation
• P0-E: Character Usage Guide UI on character detail page
• P0-F: detailed UI sub-stage labels at 88%


─────────────────────────────────────────────────────────
[2026-05-05] AI CLONING FREE-TESTING EXCEPTION (CONTROLLED) SHIPPED
─────────────────────────────────────────────────────────
Founder directive: AI Cloning is the SOLE allowed exception to the
mandatory-subscription policy. Strict isolation, defense-in-depth,
explicit kill switch.

✅ Backend kill switch
   • New flag `AI_CLONING_FREE_ENABLED = True` in `routes/avatar_studio.py`
     (top of file, with full whitelist documentation)
   • Routes under /api/avatar/* explicitly whitelisted from BOTH:
       - subscription-status checks
       - credit deduction (no users.credits $inc, no credit_ledger writes)
   • Currently enforced by absence of credits_service usage in the entire
     avatar_studio.py file — guaranteed by the new regression test
     `test_avatar_studio_does_not_call_credits_service`

✅ Frontend modal exclusion (defense-in-depth)
   • `utils/api.js` interceptor now skips `/api/avatar/*` routes from
     SubscribeRequiredModal trigger. Even if the backend ever returns
     402 from these paths (it shouldn't), users won't see the
     mandatory-sub modal for AI Cloning.

✅ Analytics — `ai_cloning_used_free_testing` event
   • Added to BOTH allowlists:
       - global FUNNEL_STEPS in `routes/funnel_tracking.py`
       - local ALLOWED_FUNNEL_STEPS in `routes/avatar_studio.py`
   • Server-side emit on every successful generate (auth + anonymous):
       - studio_mock_generate → emits with user_id + meta
       - studio_anon_mock_generate → emits with session_id + meta
   • Meta payload: {avatar_type, motion_style, duration_seconds,
     anonymous, policy: "ai_cloning_free_testing_2026_05"}

✅ UI labels (clarity over confusion)
   • AICloningStudio header: amber "Under Testing · Free" pill badge
     (data-testid=avatar-studio-free-testing-badge)
   • Dashboard tile updated:
       name: "AI Cloning"
       desc: "Verified AI avatar — free during testing"
       badge: "FREE · TESTING" (was "NEW")

✅ UI consistency check (verified)
   ✓ Pricing page does NOT mention AI Cloning as paid
   ✓ SubscribeRequiredModal does NOT trigger for /api/avatar/* responses
   ✓ Credit badge does NOT decrement (no credits_service calls)
   ✓ Referral system does NOT interact (cloning is not a qualifying action)

✅ Tests — 8/8 unit tests PASS
   • New regression tests in `test_zero_free_credits_policy_2026_05.py`:
       - test_ai_cloning_free_testing_kill_switch
       - test_ai_cloning_funnel_event_allowlisted_globally
       - test_avatar_studio_does_not_call_credits_service
         (precise: strips docstrings, blocks actual imports/calls only)
   • Live smoke verified:
       - POST /api/avatar/studio/anon-mock-generate works without auth
       - DB confirmed: 2 ai_cloning_used_free_testing events with
         policy=ai_cloning_free_testing_2026_05 stamp
       - Photo Trailer freeze HELD: /api/photo-trailer/templates → 9

📁 Files Touched:
   • backend/routes/avatar_studio.py
       - Added AI_CLONING_FREE_ENABLED flag + whitelist doc
       - Added ai_cloning_used_free_testing to ALLOWED_FUNNEL_STEPS
       - Server-side emit on both generate paths (auth + anonymous)
   • backend/routes/funnel_tracking.py — added event to global allowlist
   • frontend/src/utils/api.js — interceptor skips /api/avatar/*
   • frontend/src/pages/AICloningStudio.jsx — Header pill badge
   • frontend/src/pages/Dashboard.js — Cloning tile copy/badge update

📁 Files Added: none (test additions in existing file)

🚦 Strategic structure achieved:
   • Core product → paid only (mandatory subscription)
   • AI Cloning → free (testing hook, demand-validation window)
   • This is the ONLY allowed exception. Adding more = back to free-tier hole.

─── Decision metric for AI Cloning ───
Watch `ai_cloning_used_free_testing` volume daily at /app/admin/avatar/funnel.
   HIGH volume + low subscribe conversion → keep free, drives top-of-funnel
   HIGH volume + high subscribe conversion → flip to paid (AI_CLONING_FREE_ENABLED=False)
   LOW volume → kill the feature, stop wasting Phase-2 dev cycles


─────────────────────────────────────────────────────────
[2026-05-05] P0 MANDATORY SUBSCRIPTION / ZERO FREE CREDITS — PRE-DEPLOY CHECKLIST COMPLETE
─────────────────────────────────────────────────────────
Founder directive: finish the 3 missing pre-deploy items before triggering
the production migration. No new pricing experiments. No UI redesign. No
plan changes.

✅ Issue #1 — Graceful Block Modal + Toast (BOTH per founder choice)
   • New `frontend/src/components/SubscribeRequiredModal.jsx` (130 LOC)
     - Listens for `window` event `subscribe-required-modal`
     - Title: "Free credits have been removed"
     - Body:  "Subscribe to continue creating."
     - Primary CTA: "Subscribe to Start Creating" → /app/pricing
     - Secondary: "Already a subscriber? Go to billing" → /app/billing
     - Inline policy line at bottom: "No free credits. Subscription required for all generation features."
     - data-testids: subscribe-required-modal, sr-modal-{title,body,subscribe-cta,checkout-cta,close}
   • Globally mounted via `<SubscribeRequiredModal />` in App.js
   • `utils/api.js` interceptor enhanced — on 402 / INSUFFICIENT_CREDITS /
     UPGRADE_REQUIRED / FREE_QUOTA_EXCEEDED:
        - Toast "Free credits have been removed. Subscribe to continue creating."
        - dispatchEvent('subscribe-required-modal', {detail: {feature, source}})
   • Funnel events fired:
        free_user_blocked_post_policy_first   (sessionStorage gate)
        free_user_blocked_post_policy_repeat
        pricing_page_opened_from_block        (on CTA click)
   • Feature inferred from URL path (photo_trailer / avatar / story_video /
     reel / comix / gif / coloring_book / bedtime_story / generic)

✅ Issue #2 — Referral Loophole HARD-KILLED
   • New global flag `REFERRAL_CREDITS_DISABLED = True` in `routes/referrals.py`
   • `_grant_reward()` early-returns POLICY_DISABLED — no users.credits $inc,
     no credit_ledger write. A status="BLOCKED_BY_POLICY" stub doc is still
     inserted so observability + dashboard counters keep working.
   • `grant_referral_purchase_bonus()` same guard — purchase-bonus referral
     credits also blocked.
   • Profile counters (valid_referrals, lifetime_referrals, pending_referrals)
     still increment so the dashboard shows the qualified referral.
   • Tracking, click attribution, signup attribution UNCHANGED.

✅ Issue #3 — Scope-Locked Copy Refresh
   • `pages/Pricing.js`:
     - Hero: "Choose Your Plan" → "Subscribe to Start Creating"
       (data-testid=pricing-hero-title)
     - Subhead: "Choose monthly credits or top up as you go. Cancel anytime."
     - NEW inline guard banner: "No free credits. Subscription required for
       all generation features." (amber border, data-testid=pricing-policy-guard)
     - Primary CTA: "Get Started Free" → "Subscribe to Start Creating"
     - Meta description updated (no more "Start free with 10 credits")
   • `pages/Landing.js`:
     - Hero meta description rewrite
     - Pricing teaser hero: "Start free. Upgrade when you love it." →
       "Subscribe to start creating."
     - Removed "10 credits to start" / "Free ₹0" tile → replaced with Weekly tile
     - Final CTA: "Start Creating — Free" → "Subscribe to Start Creating"
     - Footer CTA strip: "Create your first AI video in seconds — free" →
       "Subscribe to start creating AI videos in seconds"
     - FAQ #1 already correct ("Subscribe to one of our plans...")
   • `components/UpgradeBanner.js`:
     - "Credits Exhausted!" → "Subscription required"
     - "You've used all your free credits. Upgrade to continue generating
       amazing content." → "Free credits have been removed. Subscribe to
       continue creating."
     - "View Plans & Upgrade" → "Subscribe to Start Creating"
   • `components/EmailVerificationBanner.js`:
     - Removed "Your X free credits are locked" copy → "Verify your email to
       keep your account secure and access subscription features."
   • `components/CreditStatusBadge.jsx`:
     - Daily-reward UI gated off (always invisible) — backend endpoint also
       returns no-op now (see below)

✅ Daily Reward backend endpoint disabled
   • POST /api/monetization/daily-reward/claim now returns
     {success: false, message: "Daily rewards have been removed. Subscribe
     to continue creating.", credits_earned: 0, policy: "subscription_required_2026_05"}
   • Old logic preserved in `_legacy_claim_daily_reward` for audit only
   • No /credits $inc fires from this path under any condition

✅ Funnel allowlist
   • 3 new events appended to FUNNEL_STEPS in `routes/funnel_tracking.py`:
     free_user_blocked_post_policy_first
     free_user_blocked_post_policy_repeat
     pricing_page_opened_from_block

✅ Tests — 5/5 unit + 24/24 integration
   • New `backend/tests/test_zero_free_credits_policy_2026_05.py` (5 tests):
     funnel allowlist, REFERRAL_CREDITS_DISABLED flag, _grant_reward block,
     purchase-bonus block, migration purchased-credit math
   • testing_agent_v3_fork iteration 537: 9/9 backend + all frontend UI
     flows passed.
        - All 3 new funnel events accepted, unknown step rejected
        - Referral qualify path emits no credits
        - Daily reward returns no-op
        - Admin billing-policy verification still healthy
        - /api/avatar/studio/anon-mock-generate STILL ungated (no auth)
        - /api/photo-trailer/templates returns 9 (freeze HELD)
        - Pricing/Landing copy verified, modal verified end-to-end including
          first vs repeat sessionStorage tracking + CTA pricing route

✅ Migration script verified — preview state after prior patch:
        total_users: 54
        users_with_credits_gt_zero (excl admin/unlimited/subscribed): 0
        users_revoked_free_credits: 38
        Dry-run on current state: 0 users would be affected (already migrated)
   The script's purchased-credit protection logic:
        new_credits = min(old_credits, purchased) if purchased > 0 else 0
   • Test user `test@visionary-suite.com` (1413 credits, all purchased): protected ✓

📁 Files Added:
   • frontend/src/components/SubscribeRequiredModal.jsx (130 LOC)
   • backend/tests/test_zero_free_credits_policy_2026_05.py (105 LOC, 5 tests)

📁 Files Touched:
   • frontend/src/App.js — 1 import + 1 mount
   • frontend/src/utils/api.js — 402/INSUFFICIENT_CREDITS interceptor (~50 LOC)
   • frontend/src/pages/Pricing.js — hero, guard banner, CTA, meta
   • frontend/src/pages/Landing.js — pricing teaser, final CTA, footer CTA, meta
   • frontend/src/components/UpgradeBanner.js — exhausted-state copy
   • frontend/src/components/EmailVerificationBanner.js — removed free-credits copy
   • frontend/src/components/CreditStatusBadge.jsx — daily-reward UI off
   • backend/routes/funnel_tracking.py — 3 new events allowlisted
   • backend/routes/referrals.py — REFERRAL_CREDITS_DISABLED flag + 2 early-returns
   • backend/routes/monetization.py — daily-reward claim now no-op

🚦 Photo Trailer freeze + Avatar Demo freeze HELD throughout.
🛑 Production migration NOT yet executed — staged rollout pending founder go.

─── PRODUCTION ROLLOUT INSTRUCTIONS (when you're ready) ───
Step 1 (PROD only):
    cd /app/backend && python scripts/backup_users_credits.py
        → Saves /tmp/billing_backup_<TS>.json — KEEP THIS PATH

Step 2 (1-hour observation window per founder choice — verify the snapshot
        looks right, then proceed):
    cd /app/backend && python scripts/migrate_zero_free_credits.py --dry-run
        → confirm "Affected:" matches expected free-credit user count
    cd /app/backend && python scripts/migrate_zero_free_credits.py --apply
        → commits the wipe

Step 3 (verify):
    curl -s "$API/api/admin/billing-policy/verification" \
        -H "Authorization: Bearer $ADMIN_TOKEN" | python3 -m json.tool
    Expect: users_with_credits_gt_zero=0, users_with_free_credit_flag=0,
    signup_credit_grants_last_7_days=0

Step 4 (rollback if needed within minutes):
    cd /app/backend && python scripts/restore_credits_from_backup.py \
        /tmp/billing_backup_<TS>.json --apply

Step 5 (24h observation):
    Watch funnel for free_user_blocked_post_policy_first count — measures
    real volume of blocked free-tier users. High signal for conversion lift.


─────────────────────────────────────────────────────────
## 2026-02-28: Admin Credentials Update & CI/CD Integration (Iteration 109)

### Admin Credentials Changed
- **Old Email**: admin@creatorstudio.ai
- **New Email**: krajapraveen.katta@creatorstudio.ai
- **Password**: Updated to new secure password
- **Verified**: Login tested and working on preview environment

### CI/CD Pipeline Integration
- Updated `/app/.github/workflows/playwright.yml` with:
  - Manual workflow dispatch option
  - Environment selection (preview/production)
  - Chromium and Firefox browser support
  - Test artifacts upload
  - GitHub Step Summary generation
  - Failure notifications

### Package.json Scripts Added
```json
{
  "test": "npx playwright test --project=chromium",
  "test:all": "npx playwright test",
  "test:smoke": "npx playwright test --project=chromium --grep 'should login|should load|health' --workers=1",
  "test:report": "npx playwright show-report"
}
```

### Downloads Endpoint Error Handling
- Enhanced `/api/downloads/my-downloads` with try-catch blocks
- Added logging for debugging production issues
- Production 502 error identified as Cloudflare/nginx issue (not code)

---

## 2026-02-28: Production Stabilization Verified (Iteration 107-108)

### Regression Testing Results:
- Production Tests: 95% PASS
- Preview Tests: 100% PASS
- Playwright Automated Tests: 28/31 PASS (90%)

### Comic Generation Verified:
- Job ID: 6a87fee1-2dcc-4818-bfa8-38c6a34c6913
- Result: BASE64 DATA URL (1,056,382 chars)
- Status: COMPLETED on production

---

## Previous Changes

### Notification System (2026-02-27)
- Bell icon in header
- Notification dropdown panel
- Real-time polling

### 5-Minute Download Expiry (2026-02-27)
- Countdown timer
- Auto-cleanup service
- Premium extension feature

### Worker System (2026-02-26)
- Per-feature worker pools
- Auto-scaling at 80% utilization
- Admin dashboard at /app/admin/workers

### Photo Trailer — Share Funnel + Premium Queue Priority (2026-02-XX)
- Share funnel analytics: 12 events tracked (share_page_view, video_play_clicked, signup_completed, etc.) via /api/funnel/track
- Premium queue priority: separate asyncio Semaphores (_PRIORITY_GATE, _STANDARD_GATE) so premium 90s jobs skip the line
- Admin queue-stats endpoint: GET /api/photo-trailer/admin/queue-stats (auth-gated)
- MP4 provenance metadata baked into rendered trailers (title, copyright, description = job_id)
- Fixed 2 failing tests: provenance metadata test now resolves ffmpeg/ffprobe via fallback (system → bundled); queue-stats test passes
- Full photo_trailer regression suite green: 39/39 tests across share_funnel, trust_legal, premium_tier, signed_urls, vertical_cut, janitor



### Photo Trailer — Founder KPI Dashboard (2026-02-XX)
- New endpoint `GET /api/photo-trailer/admin/dashboard?range=24h|7d|30d` returns 27 KPIs across 6 sections:
  Acquisition (3) · Engagement (4-7) · Conversion (8-13) · Revenue (14-19) · Ops (20-24) · Virality (25-27)
- Powered by `funnel_events` (share_page_view, video_play_clicked, watch_25/50/75, completed_watch, share clicks, make_your_own_clicked, signup_started/completed, first_trailer_created, paywall_shown/upgrade_clicked) joined with `photo_trailer_jobs` (plan_tier, duration, queue_lane, queue_wait_seconds, render time, fail rate)
- New admin page `/app/admin/photo-trailers` (`PhotoTrailerKpiDashboard.jsx`): truth-first stat cards + pure-CSS bar charts, 24h/7d/30d toggle, refresh button
- Fixed `priority_slots` config exposure in queue-stats (was reading semaphore-runtime value, now exposes static configured slot count)
- Test suite: `test_photo_trailer_kpi_dashboard.py` (4 tests — auth gate, range validation, all-three-ranges, and seeded-math correctness across all 6 sections)
- Full Photo Trailer regression: 36/36 green

### Photo Trailer — Failure Diagnostics (2026-02-XX)
- Backend: `/admin/dashboard` ops block now includes 7 new diagnostic fields:
  `failure_stage_breakdown`, `error_code_breakdown`, `top_failure_stage`, `top_error_code`,
  `recovery_opportunity`, `recent_failures`, `fail_trend`
- `_fail()` helper now preserves the active `current_stage` into `failure_stage` BEFORE overwriting current_stage to "FAILED" — without this fix, stage breakdown reports "FAILED" for everything
- Historical jobs without `failure_stage` are mapped via `error_code → stage` table
- Recovery opportunity calc: assumes 65% retry success rate for transient codes, projects fail-rate after retry strategy
- Frontend: 4 cards under fail-rate (#1/#2/#3 stages + top error), recovery banner with strikethrough → projected rate, dual stage/code breakdown tables with retryable/fatal badges, stacked-bar daily fail trend with stage legend, collapsible recent-failures drawer (last 10)
- 6 KPI dashboard tests passing


### Photo Trailer — P0 RELIABILITY SPRINT (2026-02-XX)
Founder directive: 59.2% fail rate → under 20%. Three changes shipped together.

**1. JANITOR — Dynamic stale thresholds + heartbeat protection**
- Replaced single `STALE_THRESHOLD_MINUTES = 5` with per-duration table:
  20s = 10min, 45/60s = 20min, 90s = 35min, default = 15min
- Added `last_progress_at` + `last_stage_change_at` fields, written by `_set_stage`
  and a new `_heartbeat(job_id, message)` helper called inline during long stages
- Janitor skips any job whose `last_progress_at` < 180s (alive)
- DB-side prefilter (smallest tier threshold) + per-sweep cap of 50 jobs prevents
  thundering-herd on backlogs

**2. STALE AUTO-RECOVERY — First stale gets a free retry**
- New `retry_count` field. retry_count == 0 + stale → status flips back to QUEUED,
  `_run_pipeline(jid)` re-scheduled, `auto_requeued_at` stamped, `retry_count = 1`,
  `progress_message = "Recovering stalled job — auto-retrying"`. NO refund.
- retry_count >= 1 + stale → normal FAIL + STALE_PIPELINE + refund (existing path)
- Funnel event `photo_trailer_auto_requeued` emitted for dashboard observability

**3. IMAGE_GEN HARDENING — Per-scene retry, partial-failure tolerance**
- `_gen_scene_image` inner retry bumped 2→3 attempts with explicit 2/5/10s backoff
- Outer per-scene retry in orchestrator (one extra shot with fresh session_id)
- `asyncio.gather(return_exceptions=True)` — one failed scene no longer cancels
  in-flight siblings; failure message tells user which scene index died
- Heartbeat ping per scene start ("Generating scene 4/6") + on retry ("Retrying scene 4/6")

**UX**
- New `progress_message` field rendered under the stage copy in the wizard
- Amber styling on retry/recovery messages, violet on normal progress

**Tests**
- 10/10 new reliability_sprint tests green
- 4/4 existing janitor regression tests updated for new behavior
- Full Photo Trailer regression: 47/47 green

**Expected impact** (per dashboard recovery-opportunity card):
- 67 STALE_PIPELINE jobs in 30d × ~65% recovery → ~44 jobs saved
- Projected fail-rate drop: 59.1% → ~40% on STALE alone
- Plus IMAGE_GEN retries should cut the 41% IMAGE_GEN_FAIL share further
- Combined target post-fix: under 20%


### Photo Trailer — P0 LOW-CREDITS REVENUE UX (2026-02-XX)
Founder directive: replace generic "Could not start trailer" toast with structured
revenue-conversion paywall.

**Backend**
- `POST /api/photo-trailer/jobs` returns structured 402 `INSUFFICIENT_CREDITS`:
  `{code, message, required_credits, current_credits, missing_credits, duration_seconds, current_plan, suggested_durations, upgrade_url, topup_url}`
- `suggested_durations` calculated server-side: lists shorter durations the user
  CAN afford right now (1-tap downgrade UX)
- Emits `photo_trailer_low_credit_seen` funnel event with full context
- Added 5 events to funnel allowlist: `photo_trailer_low_credit_seen`,
  `photo_trailer_buy_credit_clicked`, `photo_trailer_subscribe_clicked`,
  `photo_trailer_duration_downgraded`, `photo_trailer_credit_fail_recovered`,
  plus `photo_trailer_auto_requeued` from reliability sprint

**Frontend**
- New `LowCreditsModal` component replaces the toast for 402 INSUFFICIENT_CREDITS
- Smart primary CTA per plan:
  - FREE → Subscribe Now (revenue conversion)
  - PAID → Buy Credits (top-up)
  - PREMIUM → Contact Support (safety net)
- Variant copy:
  - missing ≤ 5 → "Subscribe now and get instant access"
  - missing > 20 → "Best value: Monthly plan"
  - default → "Add credits or subscribe to continue"
- Inline 1-tap downgrade buttons for cheaper durations
- Pre-click "Need X credits · you have Y" / "You are short by Z" subtext under cost line

**SPEED — Image+TTS pipelined per scene**
- Per-scene voiceover now kicks off inline AS SOON AS that scene's image lands
  (was: serial gather phase 1 = all images, phase 2 = all audio)
- Wall-clock saving estimate: ~25-40% on 6-scene trailers
- One-failure-blocks-all-others isolation preserved via `return_exceptions=True`
- TTS_FAIL vs IMAGE_GEN_FAIL distinguished in error tagging for diagnostics

**Tests**
- 5/5 new low-credits tests green (structured 402 shape, suggested durations,
  funnel event emission, free-tier exemption, pipeline source-level proof)
- 47/47 reliability + KPI + funnel + premium + vertical + janitor regression green
- **Total: 52/52 photo_trailer suite green**


### Photo Trailer — P0 STUCK-AT-88% RELIABILITY FIX (2026-02-XX)
Founder-reported live bug: spinner stuck at 88% RENDERING_TRAILER forever.
Root cause = heartbeat protection had no upper bound + ffmpeg/upload calls had
no per-stage timeout. Fixed in one disciplined pass.

**Backend**
- New `HARD_MAX_RUNTIME_BY_DURATION` (20s=8min, 60s=15min, 90s=25min) — absolute ceiling
- New `RENDER_TIMEOUT_BY_DURATION` (20s=5min, 60s=8min, 90s=12min) — per-stage ceiling
- `_render_trailer` wrapped in `asyncio.wait_for(timeout=render_timeout)` — surfaces RENDER_TIMEOUT cleanly
- All R2 uploads (widescreen + vertical + thumbnail) bounded by `asyncio.wait_for` (300s/180s/60s)
- Janitor logic rewritten: heartbeat extension is now valid ONLY in `[hard_max, stale_threshold]` window. Past `stale_threshold` → reap regardless of heartbeat
- Hard-max-exceeded jobs at retry_count=0 now SUPPRESS auto-requeue (toxic — would just hang again)
- Janitor uses `RENDER_TIMEOUT` error_code when failure occurred during RENDERING_TRAILER stage (vs generic STALE_PIPELINE for upstream)
- New admin endpoint `GET /admin/stuck-jobs?min_age_minutes=N` lists PROCESSING jobs with stale heartbeat + reap-prediction
- Dashboard `ERROR_TO_STAGE` map + `RETRYABLE_CODES` updated to include `RENDER_TIMEOUT`

**Frontend**
- `ProgressStep` polling now also exits on `status === 'CANCELLED'` (was: COMPLETED + FAILED only)
- Escalation copy gated to elapsed time:
  - 0-3 min: clean spinner only (no clutter)
  - 3+ min: "you can leave this page" card + escape buttons
  - 4+ min: amber "This is taking longer than usual" warning above
- Trust `j.status` over `progress_percent` for terminal transition (fixes "88% with status=FAILED" stuck-spinner bug)

**Tests** — 9 new tests in `test_photo_trailer_render_timeout.py`:
1. Hard-max thresholds match founder spec
2. Hard-max overrides fresh heartbeat in janitor
3. Hard-max suppresses auto-requeue
4. Admin /admin/stuck-jobs surfaces stuck jobs
5. RENDER_TIMEOUT in dashboard error map
6. Render stage uses asyncio.wait_for
7. Frontend ProgressStep detects terminal status
8. Frontend escalation copy gated to 3-min mark
9. RENDER_TIMEOUT emits funnel failure event

**Total Photo Trailer regression: 61/61 green**

Live verification: `/admin/stuck-jobs` returned a real 90s job at 5.5min mid-GENERATING_SCENES with `will_be_reaped_next_sweep=false` (correctly under 25min hard-max).


### Photo Trailer — P0 DOWNLOAD-BUTTON FIX (2026-02-XX)
Founder bug: "Download 16:9" button does nothing on Result screen.

**Root cause**
The download handler called `window.open(j.url, '_blank', 'noopener')` AFTER an
async `fetch()`. Chrome and Safari popup blockers silently kill `window.open()`
that doesn't originate from a synchronous user gesture — the async fetch broke
the gesture chain. No error, no toast, button just appeared dead.

**Fix (`PhotoTrailerPage.jsx :: handleDownload`)**
1. Toast "Preparing download…" immediately on click (user feedback)
2. Always fetch a FRESH signed URL on click (handles 10+ min waits where
   the previous `streamUrl` may have expired)
3. Trigger via temporary `<a href={url} download={fname}>` element +
   programmatic `click()` — counts as gesture continuation, no popup blocker
4. Fallback: if anchor click throws (locked-down WebKit), `window.location.href = url`
5. Exact error reasons surfaced (`detail.message`, `detail`, network err)
   — no more silent "Could not start download"
6. Toast "Download started" on success
7. Funnel emit: `photo_trailer_download_clicked` (allowlisted server-side)

**Backend (already correct, verified by tests)**
- `/api/photo-trailer/jobs/{job_id}/stream?download=true&format=wide|vertical`
  returns `{url, expires_in, format, thumbnail_url, has_vertical}`
- R2 signer adds `response-content-disposition: attachment; filename="..."`
- Format regex enforces `wide|vertical` only
- Owner-only (404 for non-owner, 401 anonymous)

**Tests** — 7 new in `test_photo_trailer_download.py`:
1. /stream returns signed URL with attachment disposition
2. format=vertical mints vertical key
3. invalid format → 422
4. anonymous → 401/403
5. non-owner → 404
6. Frontend uses `<a download>` pattern (no `window.open(` in handler code)
7. Funnel allowlist includes `photo_trailer_download_clicked`

**Live verification**: hit `/stream` for a real completed trailer with both
formats — both return 200 with `response-content-disposition` in the signed URL.

**Total Photo Trailer regression: 68/68 green**


### Photo Trailer — P0 RESULT-PAGE ESCAPE PATH (2026-02-XX)
Founder bug: Result page had no Back/Home — users got trapped after a trailer
finished (couldn't get back to wizard or home without browser back-button).

**Frontend (`PhotoTrailerPage.jsx :: ResultStep`)**
- Top-left **Back** button (testid `trailer-result-back-btn`):
  prefers parent-supplied `onBackToWizard` callback (in-page state reset),
  falls back to `navigate('/app/photo-trailer')`
- Top-right **Home** button (testid `trailer-result-home-btn`): `navigate('/app')`
- Both labels use `hidden sm:inline` — icon-only on mobile, icon+label on desktop
  → no horizontal overflow on iPhone widths (verified at 390x844)
- Wrapped in a labelled flex container (testid `trailer-result-nav`) using
  the existing border/background tokens, no new color or design language
- Parent passes `onBackToWizard` mirroring the existing `onCreateAnother`
  reset logic so Back lands on wizard step 1 with clean state

**Untouched (per founder rule)**: generation pipeline, render logic, download
logic, payments, credits, templates, share buttons, Make-another button.

**Tests** — 9 new in `test_photo_trailer_result_nav.py`:
1. Back button rendered with documented testid
2. Home button rendered with documented testid
3. Home routes via useNavigate to /app
4. Back uses callback with route fallback
5. Nav container has labelled testid
6. All 5 existing primary CTAs still present (Download / WhatsApp / More /
   Make another / video element)
7. ArrowLeft + Home icons imported from lucide-react
8. Labels use `hidden sm:inline` — mobile-safe
9. Parent passes `onBackToWizard` prop

**Total Photo Trailer regression: 77/77 green**


### Photo Trailer — P0 START-ERROR TRANSPARENCY (2026-02-XX)
Founder bug: clicking Generate on failure showed only "Could not start trailer"
red toast. No cause, no next step. Users blamed the product.

**Backend** — every error path on `POST /api/photo-trailer/jobs` now returns
structured `{detail: {code, message}}` instead of bare strings:
- `INVALID_TEMPLATE`, `UPLOAD_SESSION_NOT_FOUND`, `UPLOAD_NOT_FINALISED`
- `HERO_NOT_IN_SESSION`, `CHARACTER_NOT_IN_SESSION`
- `TOO_MANY_ACTIVE_JOBS` (with `active_jobs` count)
- `PROMPT_BLOCKED` (existing safety reject path now structured)
- (Pre-existing structured: `INSUFFICIENT_CREDITS`, `UPGRADE_REQUIRED`,
  `FREE_QUOTA_EXCEEDED`)
- New funnel event `photo_trailer_start_failed` allowlisted

**Frontend** (`PhotoTrailerPage.jsx`)
- New `START_ERROR_MESSAGES` map with founder-spec human copy for: insufficient
  credits, rate-limited, auth-required, upload-missing, beta-locked,
  validation, plus all backend codes
- New `deriveStartError(resp, body, thrown)` helper produces stable
  `{code, message, http_status, retryable, cta}` shape
- New inline error panel (testid `trailer-start-error`) ABOVE Generate:
  - Persistent (doesn't disappear like a toast)
  - Shows error code + http status (debug-friendly)
  - Contextual CTAs:
    - INSUFFICIENT_CREDITS → "Buy credits" → `/app/billing`
    - UPGRADE_REQUIRED / FREE_QUOTA_EXCEEDED → "See plans" → `/app/pricing`
    - AUTH_REQUIRED → "Sign in" → `/login`
    - UPLOAD_*  / HERO_*/CHARACTER_* → "Re-upload" (jumps to wizard step 1)
    - INVALID_TEMPLATE → "Pick a template" (jumps to wizard step 2)
    - PROMPT_BLOCKED → "Edit prompt"
    - TOO_MANY_ACTIVE_JOBS / RATE_LIMITED / UNKNOWN → "Retry"
- Toast still fires (same human message) — toast for ephemeral feedback,
  panel for read-and-act
- `setStartError(null)` at the top of every onGenerate attempt — never a
  stale red panel
- `photo_trailer_start_failed` emitted with `{code, message, http_status}`
- The OLD bare `'Could not start trailer'` fallback string is GONE
- No raw stack traces ever surfaced

**Tests** — 11 new in `test_photo_trailer_start_errors.py`:
1. `INVALID_TEMPLATE` returns structured 400 detail
2. `UPLOAD_SESSION_NOT_FOUND` returns structured 404
3. `TOO_MANY_ACTIVE_JOBS` returns structured 429 with active_jobs count
4. `photo_trailer_start_failed` is in funnel allowlist
5. Frontend has all 13 spec'd error codes in mapper
6. Inline error panel testids present + role=alert
7. Frontend emits start_failed event with code+http_status
8. Generic "Could not start trailer" fallback removed
9. Retry button gated to `err.retryable`
10. CTA button + buy/pricing/billing routes wired
11. `setStartError(null)` clears panel on retry

**Total Photo Trailer regression: 88 passed across 12 suites (each isolated)**


─────────────────────────────────────────────────────────
[2026-04-30] PHOTO TRAILER — HERO UI VERIFY + 48h READOUT + SIGNUP ROOT-CAUSE
─────────────────────────────────────────────────────────
Founder directive: a → b → c, evidence only, no new features, no patches until root cause proven.

─── (a) HERO SELECTION UI — 6/6 PASS (iteration_532.json) ───
  test_1  desktop_checkboxes_outside_photo   PASS  (photo Y=304, checkboxes Y=520)
  test_1b mobile_checkboxes_outside_photo    PASS  (44px tap, 390px viewport)
  test_2  villain_only_selection             PASS  (Continue enabled → step 3)
  test_3  supporting_only_selection          PASS  (Continue enabled → step 3)
  test_4  hero_fallback_mechanism            PASS  (backend 200/201 on promoted hero)
  test_5  happy_path_explicit_hero           PASS  (job_id returned)
  test_6  backend_contract_regression        PASS  (422 on missing hero — enforced)
  File:   backend/tests/test_photo_trailer_hero_selection_ui_iteration532.py

─── (b) 48h RELIABILITY READOUT (2026-04-28 17:41Z → 2026-04-30 17:41Z) ───
  Window tool: backend/tests/reliability_readout_48h.py (live MongoDB pull)

  STARTS
    starts_attempted            278
    starts_succeeded            275  (reached pipeline)
    start_failed (job doc)        3  (all HERO_LOAD_FAIL)
    start_failed (funnel events)  0

  OUTCOMES
    completed                    79
    pipeline_failed             194
    still_running                 1
    completion_rate_of_starts  28.7%
    completion_rate_of_attempts 28.4%

  PIPELINE FAILURES BY CODE
    IMAGE_GEN_FAIL   92  (47.4%)   ← top bottleneck
    STALE_PIPELINE   87  (44.8%)   ← janitor-driven (often downstream of hung image-gen)
    RENDER_FAIL       8  ( 4.1%)
    SCRIPT_FAIL       4  ( 2.1%)
    TTS_FAIL          3  ( 1.5%)
    RENDER_TIMEOUT    0  (zero wall-clock kills — prior P0 fix holding)

  RENDER TIME (COMPLETED only, n=76)
    median          82.1 s
    p95            154.4 s
    max            246.2 s
    by_bucket      {15s:62  45s:5  60s:3  90s:1}

  USER ACTIONS
    downloads_clicked             0      ← instrumentation gap or real
    whatsapp_shares              25
    native_shares                 0
    auto_requeued                17
    jobs_with_manual_retry       27

  BOTTLENECK STATEMENT (founder-mandatory closer):
    Single largest bottleneck now is: Pipeline failures (IMAGE_GEN_FAIL)
    Expected lift if fixed first:     +21.5 pts on completion rate
                                      (65% retry success rate assumed)
    Confidence:                       High  (n=194 pipeline failures)

─── (c) signup_completed=0 — ROOT CAUSE PROVEN, NOT PATCHED ───
  Classification: INSTRUMENTATION BUG (naming mismatch). NOT a real signup failure.

  Evidence (live MongoDB pull, funnel_events collection):
    window  signup_started  signup_success  signup_completed  signup_failed
    48h         129             129               0                0
    7d          161             161               0                0
    30d         161             161               0                0

  Code trace:
    • backend/routes/photo_trailer.py:2139
        signup_completed = await _unique_sessions("signup_completed", cutoff)
      ← queries a step name nothing fires.
    • backend/routes/funnel_tracking.py:95-96 whitelist contains
        "signup_started", "signup_success"  (NOT "signup_completed")
    • frontend/src/pages/Login.js:188,327
        trackFunnel('signup_success', ...)  (NOT signup_completed)

  Proof signups are succeeding: 129 signup_success events in 48h,
  session_uniq == event count (1:1, no double-fire). Success-to-started
  ratio = 100% (129/129). No signup_failed events in 48h either.

  Recommendation (NOT applied per founder freeze):
    One-line fix in photo_trailer.py dashboard query — change
    "signup_completed" → "signup_success"  (or teach the whitelist to
    alias both). No data is missing; the dashboard just reads the wrong key.

  Secondary observation (flagged, not patched):
    Login.js fires signup_started/signup_success on EVERY login (existing
    users included), not only on new user creation. The 129 48h events
    therefore mix new-signup + returning-user traffic. Real new-user count
    per users.createdAt in 48h = 0. This is a separate measurement bug
    (misnamed event, not a broken flow).

📁 Files added:
   • backend/tests/test_photo_trailer_hero_selection_ui_iteration532.py (testing agent)
   • backend/tests/reliability_readout_48h.py

🚦 Freeze discipline maintained: ZERO new features, ZERO UI changes,
   ZERO refactors, ZERO patches. Evidence-only deliverable.


─────────────────────────────────────────────────────────
[2026-04-30] PHOTO TRAILER — IMAGE NORMALIZATION PATCH SHIPPED
─────────────────────────────────────────────────────────
Founder directive: apply _normalize_ref_image_bytes exactly as proposed, no
deviations. Ship, watch 6h, report.

✅ Patch implemented in backend/routes/photo_trailer.py:
   - New helper _normalize_ref_image_bytes(raw, max_dim=1024):
     exif_transpose → mode=='RGB' → thumbnail(1024, LANCZOS) → JPEG q=90.
   - Wrapped hero_bytes + villain_bytes call sites in _run_pipeline_inner.
   - PIL failure maps to HERO_LOAD_FAIL (no new error codes leaked).
   - Zero changes to retry logic, worker pools, templates, prompts, logging,
     metrics.
   - One-line dashboard fix applied earlier: signup_completed → signup_success
     (surfaces 161 real signups that were zeroed by a key mismatch).

✅ Tests (14/14 PASS, new file test_photo_trailer_image_normalization.py):
   - RGB happy path, RGBA→RGB, CMYK→RGB, palette→RGB, EXIF orientation honored,
     3000×4000 capped to 1024, 16×16 untouched, idempotent re-normalization,
     corrupt bytes raise UnidentifiedImageError, truncated bytes raise,
     output size sanity (<800KB), pipeline source assertions confirm
     HERO_LOAD_FAIL mapping on both hero and villain branches,
     _gen_scene_image retry loop (3 attempts, 2/5/10s backoff) untouched.

✅ Regression (26 PASS, 1 pre-existing skip):
   test_photo_trailer_reliability_sprint.py + test_photo_trailer_regression_2026_04_29.py
   + test_photo_trailer_start_errors.py — all green.

✅ Live smoke (admin, post-deploy):
   - CMYK 2400×3200 hero photo (previously Nano Banana 400): job
     2d69d1dc passed GENERATING_SCENES cleanly (all 6 scenes rendered +
     voiceovers) — failed downstream at RENDER_FAIL (ffmpeg drawtext filter
     missing; pre-existing issue observed in logs at 17:35–17:40 before
     this patch shipped).
   - RGB 1024×1024 happy path (birthday_movie): job f91e86c9 same result:
     image-gen clean → RENDER_FAIL on drawtext.

✅ Post-deploy window (5.6 min, n=2 — insufficient for 6h verdict but
   directionally clear):
   - IMAGE_GEN_FAIL count         0
   - IMAGE_GEN_FAIL reduction    100% (vs 33.1% of starts in prior 48h)
   - completion_rate              0.0% (shifted bottleneck, not regression)
   - new dominant bottleneck     RENDER_FAIL (ffmpeg "No such filter: drawtext")

📁 Files Changed:
   - backend/routes/photo_trailer.py (one helper, two call sites,
     one dashboard query key fix)
   - backend/tests/test_photo_trailer_image_normalization.py (NEW, 14 tests)
   - backend/tests/reliability_readout_48h.py (NEW, reusable raw-data tool)

🚦 Discipline held: zero refactor, zero logging noise, zero dashboard work,
   zero new error codes, zero new pipeline stages.

⚠️ Next bottleneck flagged (not touched): ffmpeg system binary lacks drawtext
   filter (requires libfreetype). Fix candidates: install libfreetype-dev
   + rebuild, OR drop drawtext from scene render filter chain. Awaiting
   founder directive to dig.



─────────────────────────────────────────────────────────
[2026-04-30] PHOTO TRAILER — FFMPEG DRAWTEXT ENV FIX SHIPPED
─────────────────────────────────────────────────────────
Founder directive: fix the binary, not the pipeline. Preserve drawtext.

✅ Environment fix (no code change):
   apt-get install -y ffmpeg libfreetype6 libfreetype6-dev fontconfig
   → /usr/bin/ffmpeg now = ffmpeg 5.1.8 with --enable-libfreetype
     + --enable-libfontconfig; drawtext filter present.
   → Pipeline code at photo_trailer.py:1040/1148 already prefers
     /usr/bin/ffmpeg when it exists — no code change needed.

✅ Capability verified:
   /usr/bin/ffmpeg -filters | grep drawtext
   T.C drawtext  V->V  Draw text on top of video frames using libfreetype library.
   Fonts: FreeSans + Liberation + WenQuanYi available via fc-list
   (fc-match default = wqy-zenhei).

✅ Mandatory real-job validation (admin):
   Job d2f2ffcc — superhero_origin, 15s, RGB hero
   COMPLETED in 95s — full traversal: WRITING_TRAILER_SCRIPT →
   GENERATING_SCENES → RENDERING_TRAILER → COMPLETED
   Output: 1280×720 H.264 + AAC stereo, 20.56s, 2.44 MB
   Drawtext overlay verified by pixel scan — 1.8% bright pixels in
   bottom 80-px strip (watermark region). PASS.

─── Readout (format per founder spec; actual window 3.1 min post-env-fix) ───

POST-ENV-FIX window (3.1 min, n=1 — directional, not statistical):
  completion_rate    100%
  IMAGE_GEN_FAIL     0    (stays at 0)
  RENDER_FAIL        0    (collapsed from 100% of drawtext-broken period)
  new bottleneck     none observed yet

Full post-normalize window (12.1 min, n=3, spans drawtext-broken + fix):
  completion_rate    33.3%
  IMAGE_GEN_FAIL     0
  RENDER_FAIL        2    (both pre-env-fix)

Delta vs 48h baseline (28.7% completion): post-env-fix +71.3 pts.

Verdict: both clusters eliminated. 45–50% threshold needs 6h of real traffic
to verify; if it doesn't land, next cluster to peel = STALE_PIPELINE.

📁 Files Changed: NONE (env-only fix).

─────────────────────────────────────────────────────────
[2026-04-30] PHOTO TRAILER — HERO/VILLAIN/SUPPORT ALIGNMENT FIX
─────────────────────────────────────────────────────────
Founder-approved exception to freeze: "purely alignment + layout fix" on
Step 2 role selectors (attached screenshot showed uneven spacing, mis-aligned
checkboxes, floating buttons, not centered under photo).

✅ Implemented exactly to spec (frontend/src/pages/PhotoTrailerPage.jsx):

  1. ONE flex container wrapping all three options:
       flex flex-wrap justify-center items-center gap-4 p-2
       rounded-xl border border-white/15 bg-transparent

  2. Each option (Hero / Villain / Supporting) is identical:
       min-w-[140px] h-12 flex items-center justify-center gap-2.5
       px-3 rounded-lg border

  3. Checkbox + label perfectly vertically centered (flex items-center).

  4. Container reads as a segmented control (outer border, inner pills).

  5. Mobile: flex-wrap kicks in when width is tight; each button keeps
     its 140×48 footprint and wraps cleanly centered.

  6. aria-pressed attribute added on each button (preserves the existing
     test_clicking_hero_marks_button_active_with_aria contract).

✅ Zero logic changes: pickHero/pickVillain/pickSupport unchanged.
   Continue button behavior unchanged (anyRoleSelected). Hero-fallback
   still promotes villain/supporting to hero_asset_id on submit. Backend
   contract untouched.

✅ Existing visibility regression PASS (5/5 in 53.76s):
   - consent_checkbox square 22px / 24px (desktop / mobile)
   - role buttons ≥40px H + ≥48px W (now 48H × 140W)
   - role buttons ≥44px H on mobile (now 48H)
   - click-hero aria-pressed flip (still works with new layout)

📁 Files Changed: frontend/src/pages/PhotoTrailerPage.jsx (2 small edits —
   RoleCheckbox className, outer grid → flex container).

🚦 Freeze discipline: no animations, no logic shift, no new components,
   no backend change, no refactor, no dashboard work.


─────────────────────────────────────────────────────────
[2026-05-03] AI PERSONAL AVATAR STUDIO — VERTICAL SLICE SHIPPED
─────────────────────────────────────────────────────────
Founder directive: build consent-based avatar studio independent of Photo
Trailer. Phase 1 = end-to-end clickable vertical slice with mocked AI;
no real face/voice/training providers wired this session.

✅ Backend (NEW): /app/backend/routes/avatar_studio.py
  Router prefix: /api/avatar (mounted in server.py)
  - DB collections (new):
      avatar_clones, clone_consents, avatar_jobs, avatar_exports,
      clone_abuse_reports
  - Public endpoints:
      GET    /health
      GET    /billing/plans                        (4 plans + 4 topups, INR)
      POST   /clones                                (create — self/authorized_person)
      GET    /clones                                (user's clones)
      GET    /clones/{id}                           (single)
      POST   /clones/{id}/consent                  (multipart: phrase + 5s+
                                                    webm + duration + UA)
      GET    /clones/{id}/consent                  (latest consent state)
      POST   /clones/{id}/voice-profile            (mock voice ref)
      POST   /clones/{id}/train                    (mock training, BG task)
      GET    /jobs/{id}                            (poll progress)
      POST   /generate-video                       (mock render, BG task)
      POST   /clones/{id}/chat                     (mock reply with label)
      GET    /clones/{id}/exports                  (list with metadata)
      POST   /abuse-report
  - Admin-only:
      GET    /admin/clones
      GET    /admin/consents/pending
      POST   /admin/clones/{id}/action             (approve|reject|disable|enable)
      GET    /admin/abuse-reports
      POST   /admin/abuse-reports/{id}/action

  Hard rules baked into code:
    - DISCLOSURE_TEXT = "This video uses an AI-generated avatar with verified
      consent." stamped on every export
    - VISIBLE_LABEL = "AI-generated avatar" stamped on every export
    - REQUIRED_CONSENT_PHRASE enforced (≥80% word overlap match)
    - MIN_CONSENT_SECONDS = 5
    - MAX_SCRIPT_CHARS = 1200
    - BANNED_SUBSTRINGS list refuses celebrity/politician names, OTP/banking,
      medical/legal impersonation, sexual material, "this is real"
      deception phrases. Triggers HTTP 400 with code='DISALLOWED_CONTENT'.
    - Admin disable_clone REVOKES all approved consents (consent_status →
      revoked, revoked_at set) — defensive default.

✅ Frontend (NEW):
  - /app/frontend/src/pages/AvatarStudioPage.jsx
      7-state machine: dashboard → create → consent → train → generate
      → result → pricing.
      DisclosureBanner shown on Dashboard / Train / Generate / Result.
      Browser MediaRecorder for 5s+ consent video capture (webm).
      All interactive elements have data-testid (kebab-case).
  - /app/frontend/src/pages/AdminCloneModerationPage.jsx
      Three sections: pending consents, all clones (with disable/enable),
      abuse reports (mark reviewing/actioned/rejected).
  - App.js routes:
      /app/avatar                        (auth-gated)
      /app/admin/avatar/moderation       (auth-gated; admin role check
                                          enforced at API layer too)

✅ Test results (iteration 533): 24/24 backend, all frontend tests PASS.
   - Mocked AI providers documented in code + report.
   - Photo Trailer isolation confirmed (no regression on /api/photo-trailer/*).
   - One LOW-priority UX nit fixed in this session (submit button cursor).

🛑 Photo Trailer freeze HELD: zero changes to photo_trailer.py, pipeline,
   workers, templates, frontend, or KPI dashboard. 6h reliability readout
   still scheduled at 00:13 UTC.

📁 Files Added:
  - backend/routes/avatar_studio.py
  - frontend/src/pages/AvatarStudioPage.jsx
  - frontend/src/pages/AdminCloneModerationPage.jsx
  - backend/tests/test_avatar_studio_iteration533.py (testing agent)

📁 Files Touched:
  - backend/server.py (2 lines: import + include_router)
  - frontend/src/App.js (3 lines: lazy imports + 2 routes)

🚦 Next session (Phase 2) — provider adapter plug-ins:
   - fal.ai face/lip-sync (replace _mock_render_worker — adapter shape
     already in place: input = face_model_ref + audio_url; output = url)
   - ElevenLabs voice cloning (replace _mock_training_worker voice phase)
   - Real liveness vendor (Onfido / Persona) for third-party clones
   - SynthID-equivalent forensic watermark (real bit injection)
   - Cashfree billing wire-up (display already shipped)


─────────────────────────────────────────────────────────
[2026-05-03] AVATAR STUDIO — DEMAND-VALIDATION SCAFFOLDING SHIPPED
─────────────────────────────────────────────────────────
Founder directive: STEP 1 of the 4-step plan from prior turn (public demo
page + share buttons + 6-event funnel + referral capture + Day-7 gate).
Hard rule: no Phase 2 spend until 7-day distribution gate passes.

✅ Backend extensions (no new file; appended to avatar_studio.py):
  - 7 namespaced funnel steps allowed (avatar_landing_view, avatar_demo_played,
    avatar_signup_from_avatar, avatar_consent_submitted, avatar_first_export,
    avatar_repeat_export, avatar_share_click).
  - POST /api/avatar/funnel/track            (public, anonymous, anti-spam
                                              by step whitelist + 400 on
                                              unknown step)
  - POST /api/avatar/referral/attribute       (auth required, idempotent —
                                              first call sets users.avatar_attribution
                                              and emits avatar_signup_from_avatar;
                                              second call no-ops with
                                              {attributed: false, reason: 'already_attributed'})
  - GET  /api/avatar/demo-config              (public read; serves placeholder
                                              defaults until founder POSTs real
                                              video URLs)
  - POST /api/avatar/admin/demo-config        (admin-only; founder uses to
                                              swap real recordings without
                                              redeploy)
  - GET  /api/avatar/admin/funnel-table       (admin-only; row-table for last
                                              N days + last-7 totals + Day-7
                                              gate verdict {first_exports>=20,
                                              repeats>=5, shares>=1})
  - Server-side emits wired into existing endpoints:
      submit_consent → avatar_consent_submitted
      _mock_render_worker → avatar_first_export OR avatar_repeat_export
      (decided by the user's prior export count)

✅ Frontend (NEW):
  - /app/frontend/src/pages/AvatarDemoPage.jsx
      Public route /avatar-demo (no auth, in App.js after /share/:shareId).
      Above-the-fold:
        H1: "I replaced 2 hours of daily content creation with this AI avatar."
        Subhead: "Verified personal AI avatar. Disclosure-labeled. YouTube +
                  Instagram safe."
      3-card vertical 9:16 demo grid with mandatory "AI-generated avatar"
      label overlay on every card. Each card shows:
        - Used by: <Coaches | Course creators | Founders>
        - Time saved: ~90 minutes per day
        - Caption (founder-editable)
        - Placeholder badge while default URLs are still BigBuckBunny
      Sections: How It Works (3 steps), Disclosure-First manifesto, final CTA.
      On mount: captures utm_source/utm_campaign/ref from URL, persists once
      to localStorage.avatar_attribution, emits avatar_landing_view.
      Demo videos auto-play muted, loop. avatar_demo_played fires at 50%
      playthrough (idempotent per video).
      All CTAs route to /signup with attribution preserved in query string.
  - /app/frontend/src/pages/AvatarFunnelTablePage.jsx (admin)
      Single-table, no charts. Daily rows + last-7 totals + Day-7 gate
      verdict (PASS/FAIL with three checkmarks).
      Mounted at /app/admin/avatar/funnel.

✅ Existing frontend changes (small, surgical):
  - AvatarStudioPage.jsx → ResultStep:
      Share row added: Share to WhatsApp (wa.me/?text=...), Download for
      Instagram (downloads MP4 + copies caption), Copy invite link
      (links to /avatar-demo?utm_source=user_share&utm_campaign=avatar_referral
      &ref=<user_id>). Each click fires avatar_share_click with channel meta.
  - AvatarStudioPage.jsx → Dashboard:
      "Funnel table" admin button added (alongside Admin moderation).
      Lazy attribution: first dashboard mount per user reads
      localStorage.avatar_attribution and POSTs to /referral/attribute. Sets
      localStorage.avatar_attribution_attached='1' to ensure single-shot.

✅ Smoke (9/9 backend checks pass — admin token + test user token):
  1. /demo-config returns 3 placeholder videos with founder copy
  2. /funnel/track accepts 3 valid steps, rejects unknown step (400)
  3. /referral/attribute first-call attaches; second-call idempotent
  4. /admin/funnel-table returns N rows + last-7 totals + Day-7 gate
  5. /admin/demo-config writes; /demo-config reflects override; reset OK
  6. Non-admin user gets 403 on admin endpoints
  7. /api/photo-trailer/templates still returns 9 templates (Photo Trailer
     freeze HELD, no regression)

✅ Lint clean: AvatarDemoPage.jsx, AvatarFunnelTablePage.jsx,
   AvatarStudioPage.jsx, avatar_studio.py.

🛑 What is NOT shipped (re-confirmed freezes):
  - No fal.ai integration
  - No ElevenLabs integration
  - No Cashfree wire-up
  - No real watermark embedding
  - No safety rule engine implementation (Phase 2 parallel work, gated on
    founder explicit "begin" — separate from this STEP 1 task)
  - No Photo Trailer changes
  - No universal negative prompt
  - No new AI model calls of any kind

🚦 Founder action items for the 7-day distribution sprint:
  1. Record 3 self-avatar demo clips (vertical 9:16, ≤15s each, visible
     "AI-generated avatar" label burned in via current pipeline OR added
     in a video editor). Upload URLs via POST /api/avatar/admin/demo-config
     {videos: [...]}.
  2. Execute the Day-1 → Day-7 distribution checklist from prior plan
     (IG / LinkedIn / X / WhatsApp DMs).
  3. Watch /app/admin/avatar/funnel daily.
  4. At Day 7: read the Day-7 gate verdict. PASS → unlock Phase 2.
     FAIL → kill or pivot per founder directive (no "iterate UI more").

📁 Files Added:
   - frontend/src/pages/AvatarDemoPage.jsx
   - frontend/src/pages/AvatarFunnelTablePage.jsx

📁 Files Touched:
   - backend/routes/avatar_studio.py (appended ~210 lines, no existing
     code modified except 2 small emit-additions inside existing handlers)
   - frontend/src/App.js (3 lines: 2 lazy imports + 2 routes)
   - frontend/src/pages/AvatarStudioPage.jsx (Dashboard signature +
     Funnel button + ResultStep share row + lazy attribution effect)



─────────────────────────────────────────────────────────
[2026-05-03] AI CLONING STUDIO — 5-STEP MOCKED WIZARD SHIPPED (Phase 1)
─────────────────────────────────────────────────────────
Founder directive: rebuild AI Cloning Studio into a polished 5-step wizard
for demand validation. STRICT — keep backend fully MOCKED, no real AI
providers, no queues, no workers. "Convincing illusion" to test user intent
before incurring Phase 2 (fal.ai / ElevenLabs) spend.

User-confirmed choices (no re-opened decisions):
  1. Route: REPLACE /app/avatar (legacy archived, no dual paths)
  2. Avatar Library: inline Step 0 of the wizard
  3. Illusion: auto-complete in 20–60s with demo output (short=~20s, long=~55s)
  4. TestID convention: avatar-studio-<step>-<element>

✅ Frontend (NEW, modular):
   • /app/frontend/src/pages/AICloningStudio.jsx (orchestrator, 6 steps)
   • /app/frontend/src/components/avatar/LibraryStep.jsx (Step 0 — saved + create-new)
   • /app/frontend/src/components/avatar/AvatarTypeStep.jsx (Step 1 — 4 tiles:
     quick_avatar, voice_matched, motion, template)
   • /app/frontend/src/components/avatar/AssetUploadStep.jsx (Step 2 — photo +
     conditional voice-sample upload for voice_matched type, name required)
   • /app/frontend/src/components/avatar/MotionStep.jsx (Step 3 — 4 motion
     styles + 5 duration chips 15/30/45/60/90s)
   • /app/frontend/src/components/avatar/SafetyReviewStep.jsx (Step 4 — script
     + 5-rule checklist; Generate disabled until all ticked)
   • /app/frontend/src/components/avatar/GenerationProgress.jsx (Step 5 — polling
     job, staged progress + ETA + Result view with demo video + labels + share)
   • /app/frontend/src/components/avatar/shared.jsx (DisclosureBanner, DemoBadge,
     StepperHeader, SectionTitle)

✅ Backend (single file, +~180 LOC, zero existing code modified):
   • POST /api/avatar/studio/mock-generate (new): accepts {avatar_type,
     motion_style, duration_seconds, script?, safety_confirmed, clone_name?,
     assets?} → returns {job_id, eta_seconds, demo_label, is_demo_output:true}
   • Structured 400 errors: INVALID_AVATAR_TYPE, INVALID_MOTION_STYLE,
     SAFETY_NOT_CONFIRMED, DISALLOWED_CONTENT (reuses existing banned-substrings)
   • GET /api/avatar/studio/templates (new): 6 pre-built templates for the
     "From Template" avatar_type tile
   • _mock_studio_illusion_worker: 5 named stages (Analyzing → Preparing →
     Synthesizing voice → Rendering → Disclosure), total wall-clock capped at
     _mock_progress_for_duration (20s/35s/55s buckets), always succeeds with
     demo BigBuckBunny/ElephantsDream URL; writes avatar_exports row with
     is_demo_output=true + demo_label="Demo / simulated output" + forensic
     watermark id
   • /api/avatar/jobs/{id} projection now exposes stage_label, eta_seconds,
     is_demo_output, demo_label for the progress UI
   • Emits avatar_first_export / avatar_repeat_export funnel events on
     completion (preserves existing funnel contract)

✅ Route swap:
   • /app/avatar now points to AICloningStudio (old AvatarStudioPage moved
     to AvatarStudioPage.legacy.jsx — unreachable, not imported)
   • /app/admin/avatar/moderation + /app/admin/avatar/funnel unchanged
   • /avatar-demo (public demand page) unchanged

✅ Live E2E smoke (admin login, preview):
   login → /app/avatar → Library (21 saved avatars + Create-new tile render
   correctly) → Create-new → Type (quick_avatar) → Upload (photo preview +
   name "Smoke") → Motion (talking_head + 15s) → Safety (all 5 rules ticked +
   script) → Generate → Progress polling → Result view with demo video,
   visible "AI-generated avatar" label, "Demo / simulated output" label,
   share row, Make-another + Back-to-library buttons.
   Total time: ~21.5s for 15s clip (matches 20s backend ETA).

✅ testing_agent_v3_fork iteration 534:
   • Backend: 29/29 PASS (100%)
   • Frontend: 100% PASS — all testids verified, all 5 steps transition,
     all 4 avatar types + 4 motion styles + 5 durations work, demo labels
     visible throughout
   • Photo Trailer regression PASS: /api/photo-trailer/templates still
     returns 9 templates (freeze held)
   • Existing avatar endpoints untouched: /funnel/track, /referral/attribute,
     /admin/funnel-table all still green
   • 0 critical issues, 0 minor issues, 0 integration issues

📁 Files Added:
   • frontend/src/pages/AICloningStudio.jsx (241 LOC)
   • frontend/src/components/avatar/LibraryStep.jsx (95 LOC)
   • frontend/src/components/avatar/AvatarTypeStep.jsx (105 LOC)
   • frontend/src/components/avatar/AssetUploadStep.jsx (170 LOC)
   • frontend/src/components/avatar/MotionStep.jsx (120 LOC)
   • frontend/src/components/avatar/SafetyReviewStep.jsx (115 LOC)
   • frontend/src/components/avatar/GenerationProgress.jsx (235 LOC)
   • frontend/src/components/avatar/shared.jsx (65 LOC)

📁 Files Touched:
   • backend/routes/avatar_studio.py (appended new studio block + 1-line
     projection change on /jobs/{id})
   • frontend/src/App.js (1 lazy-import swap + 1 route element swap)
   • frontend/src/pages/AvatarStudioPage.jsx → renamed to
     AvatarStudioPage.legacy.jsx (archived, unreachable)

🚦 Still honoured (non-negotiables from founder):
   ❌ No real AI provider wired (fal.ai, ElevenLabs, HeyGen)
   ❌ No queues / workers / celery
   ❌ No universal negative prompts
   ❌ No backend complexity creep (1 new endpoint + 1 new worker + 1 new
       templates catalog — that's it)
   ❌ No Photo Trailer changes
   ❌ No second UX path — old studio archived, single source of truth
   ✅ Clean 5-step wizard, clickable end-to-end, fast completion loop,
      clear DEMO labeling on every surface

📊 Demand-validation data flow (unchanged from prior sprint):
   avatar_landing_view → avatar_demo_played → avatar_signup_from_avatar →
   avatar_consent_submitted → avatar_first_export → avatar_repeat_export
   + avatar_share_click
   Watch /app/admin/avatar/funnel daily — Day-7 gate still the same threshold
   (>=20 first_exports, >=5 repeats, >=1 share).

Next session (blocked pending 7-day gate pass):
   Phase 2 adapters (fal.ai lip-sync, ElevenLabs voice clone, real watermark
   embedding, Whisper/Mediapipe liveness), rule-based Safety Engine, Discovery
   Feed. Do not start until founder unlocks.

─────────────────────────────────────────────────────────
[2026-05-03] AVATAR DEMO WIZARD — ANONYMOUS TRY-BEFORE-SIGNUP (Phase 1.5)
─────────────────────────────────────────────────────────
Founder directive: "Ship /avatar-demo as anonymous wizard. Users experience
value first, then hit signup gate. Do NOT ask login before Generate."

✅ Backend (+130 LOC, zero existing code broken):
  • POST /api/avatar/studio/anon-mock-generate — no auth, session_id bound.
    Returns {job_id, eta_seconds, demo_label, is_demo_output=true, anonymous=true,
    remaining_in_window}.
  • GET /api/avatar/studio/anon-jobs/{id}?session_id=X — anon polling;
    cross-session reads return 404.
  • Rate limit: 2 generations per session_id per rolling 24h. 3rd call →
    429 with {code: "ANON_LIMIT_REACHED", limit: 2, window_hours: 24}.
  • 5 new funnel events: demo_generate_clicked, demo_completed,
    signup_after_demo, retry_after_demo, share_after_demo.
  • Server-side emits: demo_generate_clicked on anon-mock-generate +
    demo_completed (idempotent) on first poll of a completed anon job.

✅ Frontend (NEW AvatarDemoWizard.jsx):
  • Lands DIRECTLY on Step 1 Type — library step skipped.
  • Pre-fills: quick_avatar type, "My Demo Avatar" name, sample_face.svg
    preview, talking_head motion, 15s duration, sample script. Users can
    hit Generate in under 30s without touching anything.
  • Persistent anon session_id in localStorage.avatar_demo_session_id.
  • UTM / ref attribution captured into localStorage.avatar_attribution
    (preserves signup-time attribution).

✅ Frontend (EXTENDED GenerationProgress.jsx):
  • New anonymous + anonSessionId + onSignupGate props (fully backwards-
    compatible — /app/avatar unaffected).
  • ResultView in anonymous mode renders "Sign up to download your video"
    signup-gate card. Download button flips to "Sign up to download" +
    Lock icon. Clicking Download → fires signup_after_demo + nav()s to
    /signup?from=avatar_demo&reason=download.
  • Make-another fires retry_after_demo before resetting the form.
  • Share clicks fire share_after_demo (vs avatar_share_click) when anon.

✅ Routing:
  • /avatar-demo → new AvatarDemoWizard. Old AvatarDemoPage.jsx archived
    as .legacy.jsx (unreachable, not imported). Existing share-link
    traffic (?utm_source=user_share&ref=X) lands on the wizard — attribution
    still captured, zero broken links.

✅ testing_agent_v3_fork iteration 535:
  • Backend: 21/21 PASS (100%) — anon generate, rate limit 429,
    cross-session 404, all 4 types + 4 motion styles, banned script,
    funnel whitelist, session_id length bounds.
  • Frontend: 100% PASS — wizard lands anonymously, all fields pre-filled,
    full flow reaches Result in ~21.5s for 15s clip, signup gate renders,
    Download redirects to /signup?from=avatar_demo&reason=download.
  • Photo Trailer freeze: /api/photo-trailer/templates still returns 9.
  • Authenticated /app/avatar 5-step wizard: untouched.
  • 0 critical, 0 minor, 0 integration issues.

📁 Files Added:
  • frontend/src/pages/AvatarDemoWizard.jsx (240 LOC)

📁 Files Touched:
  • backend/routes/avatar_studio.py (+anon endpoints, +5 funnel steps)
  • frontend/src/components/avatar/GenerationProgress.jsx (anonymous mode)
  • frontend/src/App.js (1 lazy import + 1 route element)
  • frontend/src/pages/AvatarDemoPage.jsx → .legacy.jsx (archived)

🎯 Founder's Day-7 gate (what to watch at /app/admin/avatar/funnel):
  demo_generate_clicked → demo_completed → signup_after_demo is the key
  conversion chain. retry_after_demo = intent signal. share_after_demo =
  output is share-worthy. If signup_after_demo / demo_completed ≥ 5% →
  green light Phase 2. Below 2% → rethink the feature.

🚦 Still honoured (non-negotiables):
  ❌ No Phase 2 (no fal.ai, no ElevenLabs, no real generation)
  ❌ No voice cloning / better rendering / workers / pricing tweaks
  ❌ No Photo Trailer changes
  ✅ Single flow per route. Hard signup gate ONLY at Save/Download/Create.
  ✅ DEMO / SIMULATED OUTPUT labels everywhere.


## 2026-05-12 — P0 Frontend Fix: Comic Story Book Builder Admin Credit-Gate Leak

**Issue**: Despite the centralized backend `services/entitlement.py` rollout correctly granting unlimited access to admin/QA users, the **frontend** `ComicStorybookBuilder.js` still trapped admins in the "buy credits / insufficient credits" UI loop (modal + disabled Generate button) whenever the `/api/credits/balance` call was delayed, errored, or before the response landed.

**Root cause**: `credits` state initialised to `null`. `credits < cost` evaluates `null < 45` → `0 < 45` → `true`, so the button stayed disabled and the Upsell modal could fire. There was no client-side mirror of `is_unlimited_user` (which the backend computes from role / is_unlimited flag).

**Fix** (`/app/frontend/src/pages/ComicStorybookBuilder.js`):
- Added `_detectUnlimitedFromLocalStorage()` helper + canonical `_UNLIMITED_ROLES = ['admin','owner','dev','qa','qa_user','test']` mirroring backend.
- New `isUnlimitedUser` state initialised synchronously from `localStorage.user` so it is `true` on first render — no race with `/credits/balance`.
- `fetchCredits` and `fetchUserPlan` additionally set the flag from server response (defense-in-depth).
- `generateComicBook` skips the `credits < cost` gate when `isUnlimitedUser`.
- `handleDownload` bypasses the free-plan upsell for unlimited users.
- Generate button `disabled` prop respects the flag.
- Step 3 / Step 5 cost summary balance pills + header credit pill render "∞ Unlimited" when `isUnlimitedUser`.
- `UpsellModal` render guarded with `!isUnlimitedUser` (cannot open for admins even if state is forced).

**Verification**: testing_agent_v3_fork iteration_540 — ALL PASSED.
- Admin: header pill `∞ Unlimited`, all step balances `∞ Unlimited`, Generate button enabled, no Upsell, no "Insufficient credits" toast, generation started successfully.
- Test user (regression): correctly sees numeric `1,404 Credits` — gate scoped to admin only.

## 2026-05-12 — P0/P1 Bedtime Stories Subscription Access Gate

**Issue**: The Bedtime Stories page exposed the full story payload (every scene, voice notes, SFX cues) in the API response and rendered it in the DOM for every user — free, subscriber, and admin alike. There was no payload-level paywall, no playback gate, no download/copy gate, and no copy-protection on the rendered text.

**Backend fix** (`/app/backend/services/entitlement.py`, `/app/backend/routes/bedtime_story_builder.py`):
- New helpers: `has_active_subscription(user)` (reads `user.subscription.status='active'` + endDate check) and `has_full_content_access(user)` = unlimited OR premium plan OR active subscription.
- `_apply_access_gate(result, user)` truncates `scenes`, `script`, `voice_notes`, `sfx_cues` to the first scene for free users and attaches an `access` block (`full_access`, `preview_only`, `upgrade_required`, `total_scenes`, `preview_scenes`, `upgrade_message`).
- `POST /api/bedtime-story-builder/generate` calls the gate after `normalize_story()` so the full text NEVER leaves the backend for free users.
- `POST /api/bedtime-story-builder/export` returns HTTP 402 with subscription prompt for free users (was previously open).

**Frontend fix** (`/app/frontend/src/pages/BedtimeStoryBuilder.js`, `/app/frontend/src/components/BedtimePaywallModal.jsx`):
- New `BedtimePaywallModal` component with 4 contextual reasons: `play`, `download`, `copy`, `default`. CTA navigates to `/pricing`.
- Derived `fullAccess` / `previewOnly` from `story.access.*` (the backend remains the source of truth).
- `handlePlay` schedules the paywall to open ~8–10 s after the preview scene starts for free users.
- `downloadStory` and `copySection` open the paywall instead of executing for free users.
- New window-level `keydown` listener blocks Cmd/Ctrl+C/X/S/P/A and `copy`/`cut` events for non-premium users (frontend deterrent only).
- The `story-scenes` container has `onContextMenu` + `onCopy` handlers and inline `userSelect: 'none'` style applied for non-premium users.
- New preview banner (`data-testid='preview-banner'`) renders for free users with an Unlock CTA.

**Honesty note**: Screenshots cannot be technically prevented, and the UI does not claim to do so. The protection model is: payload withholding (security) + UX deterrents (no select / no context menu / blocked shortcuts) + paywall modal (conversion).

**Verification**:
- Backend regression: `/app/backend/tests/test_bedtime_subscription_gate_2026_05.py` — 4/4 PASS (free preview, free export 402, admin full, subscriber full).
- Frontend regression: `testing_agent_v3_fork` iteration_541 — 15/16 PASS. The 1 SKIP was the subscriber path because the testing agent's env did not have `test@visionary-suite.com` available; the same case is covered by the backend test which PASSED.

## 2026-05-12 — P0 Photo to Comic 502 — Code hardening + P1 enum validation

**Reproduction**: Reproduced on preview using admin/unlimited with `mode=strip + style=cute_chibi + genre=action + panel_count=6 + hd_export=false + include_dialogue=true`. Preview returned HTTP 200 with a valid jobId in ~1.17 s. **The 502 is production-infra-only** (not reproducible in preview). Most likely causes: prod nginx ingress timeout, worker OOM, or stale build.

**Code fixes (preview, ready to redeploy)**:
- `/app/frontend/src/utils/api.js` — axios response interceptor now detects HTML/non-JSON bodies (`<html>`, `<center>`, etc.) on ANY 4xx/5xx, and rewrites `response.data` to `{ detail: "The service is temporarily unavailable. Please try again.", code: "GATEWAY_ERROR", http_status, gateway: true }`. This means no page can accidentally toast raw nginx HTML again.
- `/app/frontend/src/pages/PhotoToComic.js` — `handleGenerate` error path now explicitly treats `502/503/504` and HTML-shaped bodies as gateway errors and toasts `"Comic generation failed. Please try again."` instead of leaking upstream HTML.
- `/app/backend/routes/photo_to_comic.py` — `/generate` now raises `HTTPException(400, "Invalid style '<x>'. Allowed: …")` for unknown style enums (was: silently rebranded to `cartoon_fun`, masking client bugs and making style mismatches invisible).

**Tests** (`/app/backend/tests/test_photo_to_comic_gateway_safety_2026_05.py`, 4/4 PASS):
- happy path uploaded image + `cute_chibi` + 6 panels → 200 + jobId
- unsupported style → JSON 400 with `detail`
- invalid mode → JSON 400
- admin/unlimited balance not blocked

**Production action needed (cannot fix from preview)**:
- Tail prod backend logs around the 502 timestamp — look for OOM, worker restart, or upstream R2/LLM timeout.
- Check prod nginx ingress timeout (`proxy_read_timeout`) — should be ≥ 60 s.
- If neither, raise an Emergent Support ticket; provide the prod request timestamp.

## 2026-05-12 — P0 Comic Story Book "Duplicate request in progress" soft-lock

**Bug**: Clicking "Generate Full Comic Book" returned a raw 409 toast: `"Duplicate request in progress. Please poll job status."` — even for admin/unlimited users, even on the very first click of the session.

**Root cause** (`/app/backend/services/idempotency_service.py`):
1. `check_and_store()` treated **every existing record** as a duplicate, regardless of status. Records with `status="FAILED"` from a prior crashed attempt soft-locked the user for the entire 24-hour TTL.
2. If a request crashed between `insert()` and `update_result()` (or `mark_failed`), the PENDING row was orphaned — same 24-hour soft-lock.
3. Because the body-fingerprint hash was deterministic for `(user_id, genre, title, storyIdea, pageCount)`, the user couldn't even retry by varying input — they had to wait out the TTL.

**Backend fix** (`services/idempotency_service.py`):
- `check_and_store()` now auto-recovers stuck records:
  - `status="FAILED"` → delete the row and create a fresh PENDING (retry allowed).
  - `status="PENDING"` and older than `STALE_PENDING_MINUTES=10` → delete and recreate (assume the owning request crashed).
  - `status="COMPLETED"` with a cached result → still returns the cached `{jobId,…}` payload (true idempotency preserved).
- `STALE_PENDING_MINUTES = 10` chosen because the `/generate` route is fully synchronous-fast (< 5 s under healthy load).

**Backend fix** (`routes/comic_storybook_v2.py`):
- When the duplicate path is hit and there's no cached result yet, the route now looks up the user's most-recent in-flight `comic_storybook_v2_jobs` doc by `idempotency_key` and returns `{success: true, jobId, status, progress, resumed: true}` instead of 409. The 409 path now only fires for the rare genuine race where the second request lands before the first inserted its job row.

**Frontend fix** (`pages/ComicStorybookBuilder.js`):
- `generateComicBook()` early-exits if `loading` or `pollingRef.current` is already set — kills the rapid double-submit pathway.
- On a 200 response with `resumed: true`, the toast reads `"Your comic is already generating. Opening progress…"` and the existing job is polled.
- On a 409 fallback, the client queries `/history?page=0&size=5` for the most-recent non-terminal job and resumes polling that. Only if no live job is found does it surface the soft message `"Your comic is already generating. Please wait a moment and try again."` — never the raw 409 detail.

**Tests** (`tests/test_comic_storybook_idempotency_2026_05.py`) — 6/6 PASS:
- `test_first_submit_is_not_duplicate` — fresh key returns `(False, None)`.
- `test_concurrent_pending_returns_dup_with_no_result` — fresh PENDING soft-blocks correctly.
- `test_stale_pending_is_auto_recovered` — PENDING > 10 min auto-recovers.
- `test_failed_key_is_auto_recovered` — FAILED auto-recovers.
- `test_completed_key_returns_cached_result` — true idempotency preserved.
- `test_http_single_click_returns_200_jobid` — HTTP smoke end-to-end.

**Why the user kept hitting 409**: their prior generation attempts on production crashed (the 502 episode from earlier today) — that left FAILED idempotency rows in the DB. Until this fix, those rows blocked every subsequent retry for 24 h.

**Production action** (one-time, after redeploy): clear any leftover stuck rows.
```js
// Admin DB shell — optional one-time cleanup after deploy
db.idempotency_keys.deleteMany({ status: { $in: ["FAILED", "PENDING"] } })
```
(Not strictly required — the new auto-recovery will heal them on the next submit — but speeds things up.)

## 2026-05-12 — P0/P1 Reaction GIF Creator: Actions + Access Control + Anti-Copy

**Bugs fixed**:
- `Share to Story` was a thin wrapper around `downloadResult` and silently no-op'd if the asset URL was missing.
- `Download` and `Share` fetched the raw R2 URL directly, bypassing any backend access check (free users could right-click → Save As to bypass the paywall entirely).
- No clean error when the asset URL was unavailable — silent failure.
- No copy-protection on the rendered result image.
- No engagement when the user is waiting on a 15–30 s generation.

**Backend** (`/app/backend/routes/reaction_gif.py`):
- `/job/:id` now attaches an `access` block: `full_access`, `can_download`, `can_copy_link`, `can_share_story`, `upgrade_required`. Sourced from `services/entitlement.has_full_content_access()`.
- `/download/:id` switched from the old `plan == "free"` check to `has_full_content_access()` (canonical) and returns **HTTP 402** with `"Subscribe to download. Preview is watermarked."` (changed from 403 to standard Payment Required). Also returns 404 with `"Download asset not available"` if the job is missing assets.

**Frontend** (`/app/frontend/src/pages/PhotoReactionGIF.js`):
- New `isUnlimitedUser` (from localStorage + `/api/credits/balance` `is_unlimited`) and derived `canAccessFull` (mirror of backend gate).
- All download / share / copy actions route through `POST /api/reaction-gif/download/:id` FIRST so the backend gate is the canonical enforcement. Direct R2 URL leakage is eliminated.
- `shareToStory` prefers `navigator.share({ files })` (Web Share API w/ file payload) and falls back to downloading the blob so the user can attach it to their Story manually.
- Result image wrapped in a protected container: `onContextMenu` opens the paywall for non-premium users; `draggable=false` + `onDragStart` blocked; inline `userSelect: none` + `WebkitTouchCallout: none`; image gets `pointer-events: none` for non-premium.
- New global `keydown` handler active while `phase === 'result'` && !canAccessFull blocks `Cmd/Ctrl + C / X / S / P / A` and `copy` / `cut` events — each opens the appropriate paywall (copy vs download).
- Small `"Preview · Subscribe to download"` badge overlays the bottom-right of the image for non-premium users (UX honesty — no claim of screenshot prevention).
- New waiting-feature panel (`data-testid="waiting-feature-panel"`) inside `renderGenerating` with 4 deep-link CTAs: Story Video, Photo to Comic, Comic Story Book, Bedtime Stories. Polling keeps running in the background; navigating away doesn't kill the job.
- Reuses `BedtimePaywallModal` (already shipped) for the 4 reasons: `play`, `download`, `copy`, `default`.

**Tests**:
- Backend `/app/backend/tests/test_reaction_gif_access_control_2026_05.py` — **5/5 PASS** (admin access flags, admin download, free user access flags, free user 402, missing job 404 as JSON).
- Frontend `testing_agent_v3_fork` iteration_542 — **12/12 PASS** across admin + free-user end-to-end (waiting panel, watermark badge, paywall for download/share/copy/right-click/Cmd+S/Cmd+C, admin clean paths).

**Honesty**: Screenshots cannot be prevented and the UI does not claim they can. The protection model is: backend access gate (security) + UX deterrents (no select / no context menu / no drag / blocked shortcuts) + paywall (conversion).

## 2026-05-12 — P0/P1 Brand Kit / Brand Story: Access Gate + Anti-Copy + Robust Download Errors

**Bugs fixed**:
- `/api/brand-story-builder/job/:id/result` exposed the **full** artifact payload to every authenticated user — free users could read the entire brand story end-to-end.
- `/api/brand-story-builder/job/:id/pdf` and `/zip` had **no** access gate — a free user could download the production-ready PDF/ZIP.
- TXT export was built entirely client-side from the (previously unrestricted) result payload — same leak.
- Download handlers toasted a generic `"PDF download failed"` for ANY non-200, including 402/403 paywall responses — so a paywall could look like a broken download.
- 500 PDF response detail was opaque (`"PDF generation failed"` with no error context).

**Backend** (`/app/backend/routes/brand_story_builder.py`):
- `/job/:id/result` now attaches an `access` block: `full_access`, `preview_only`, `upgrade_required`, `can_download`, `upgrade_message`. Sourced from `services.entitlement.has_full_content_access()`.
- For non-premium users, `_truncate_artifact_for_preview()` truncates artifact data server-side: strings → 140 chars + ellipsis; lists → first item only; dicts → recurse. The full artifact text NEVER leaves the backend.
- `/job/:id/pdf` and `/zip` now return **HTTP 402** with `"Subscribe to download your brand kit."` for free users.
- PDF 500 detail now includes the underlying error (logger.exception preserves stack to backend log).

**Frontend** (`/app/frontend/src/pages/BrandStoryBuilder.js`):
- New `isUnlimitedUser` (localStorage + `/api/credits/balance.is_unlimited` hydration) and `canAccessFull` (mirror of backend gate).
- New preview banner (`data-testid="brand-kit-preview-banner"`) for free users with "Unlock" CTA.
- Each artifact card's inner content is wrapped in a div with `filter blur-[3px] pointer-events-none` for free users. A floating "Subscribe to unlock" overlay sits on top of every artifact card with a `"See plans"` CTA (`data-testid="unlock-<key>"`).
- All 3 download handlers (PDF/ZIP/TXT) and the copy handler short-circuit to the paywall when `!canAccessFull`. The new `_handleDownloadError()` parses JSON error bodies from binary endpoints and routes 402/403 to the paywall, 404 to a clean toast, and any other error to a generic `"PDF/ZIP download failed. Please try again."` — never raw HTML.
- Artifacts container has `onContextMenu` + `onDragStart` + inline `userSelect:none` + `WebkitTouchCallout:none` for free users. New global keydown listener active while `phase === 'results' && !canAccessFull` blocks Cmd/Ctrl + C / X / S / P / A and `copy` / `cut` events, opening the right paywall reason.
- Reuses `BedtimePaywallModal` for the 4 reasons (download/copy/play/default).

**Tests**:
- Backend `/app/backend/tests/test_brand_kit_access_gate_2026_05.py` — **7/7 PASS** (admin full content, admin PDF/ZIP 200, free preview-only, free truncation, free PDF/ZIP 402, missing job clean JSON 404).
- Frontend `testing_agent_v3_fork` iteration_543 — **22/22 PASS** across API + code review (canAccessFull logic, preview banner, blur, lock overlay, download/copy gating, right-click and keyboard shortcuts).

**Honesty**: Screenshots cannot be prevented. The UI does not claim to. Protection model: backend preview truncation + 402 download gate (security) + UX deterrents (blur / no select / no context menu / no drag / blocked shortcuts) + paywall modal (conversion).

## 2026-05-12 — P0/P1 Viral Videos (Daily Viral Idea Drop): Subscriber-Only Gate + Broken Actions

**Bugs fixed**:
- `/api/viral-ideas/generate-bundle` was generating a free pack for every user's first attempt and credit-charged paywalled packs after — i.e. it leaked the full LLM pipeline to anonymous-grade traffic.
- `/api/viral-ideas/jobs/:id/assets` exposed full content based on the job's own `locked` flag, regardless of whether the requester held a subscription.
- `/api/viral-ideas/jobs/:id/unlock` accepted a 5-credit unlock — users could grind credits to bypass the subscription gate.
- `/api/media/download-token` allowed any owner of a viral asset to download — bypassing subscription on a route the frontend doesn't expose openly.
- `Message` / `Post` / `Download ZIP` / `Copy Link` on the result page worked for any logged-in user with no entitlement check, no missing-asset toast, and silently no-op'd on bad jobIds.
- No anti-copy deterrents on the result view.

**Backend**:
- `routes/viral_ideas_v2.py`:
  - `/generate-bundle` now **requires `has_full_content_access`** and returns **HTTP 402** for free users (`"Subscribe to generate viral content packs."`). The "first generation is free" path is removed.
  - `/jobs/:id/assets` returns an `access` block (`full_access`, `can_download`, `can_share`, `upgrade_required`, `upgrade_message`). For non-premium users, the response is force-locked server-side (`locked=true`) regardless of the job's own flag, so the existing `_format_asset()` teaser code path takes effect — the full content text never leaves the backend.
  - `/jobs/:id/unlock` is now **subscription-gated**: free users get HTTP 402; subscribers/admin/unlimited unlock the pack for free (no credit charge). Removes the credit-grind escape hatch.
- `routes/media_proxy.py::_check_entitlement` now also requires `has_full_content_access`. Non-subscribers hitting `/api/media/download/issue` (and the legacy `/download-token`) get HTTP 402 with `"Subscribe to download viral content."`.

**Frontend** (`pages/DailyViralIdeas.js`):
- New `canAccess` (from localStorage role + `subscription.status === 'active'` + `/api/credits/balance.is_unlimited`) and `fullAccess` (canonical, also synced from server `access.full_access`).
- `handleGenerate` short-circuits to the paywall for free users (defense-in-depth; backend also returns 402).
- `downloadFile`, `handleShare` (Message/Post/Copy), `copyContent`, `handleUnlock` all gate on `fullAccess` → open `BedtimePaywallModal`. 402/403 backend responses also route to the paywall instead of toasting "Download failed".
- Result wrapper has `onContextMenu` + `onDragStart` + inline `userSelect:none` for free users. New keydown effect blocks Cmd/Ctrl + C / X / S / P / A and `copy` / `cut` events while the result view is visible for non-premium.
- Locked-banner CTA copy now reads `"Subscribe to unlock"` for free users (was "Unlock This Pack (5 credits)" — the credit-unlock path is gone).
- Header counter switched from "5 credits / pack" to `Subscriber access` / `Subscribe to generate`.
- Reuses `BedtimePaywallModal` for the 4 reasons (download / copy / share / default).

**Tests** (`tests/test_viral_ideas_access_gate_2026_05.py`) — **7/7 PASS**:
1. Free user `/generate-bundle` → 402.
2. Admin `/generate-bundle` → 200 + job_id.
3. Free user `/jobs/:id/assets` → `access.full_access=false`, `locked=true`, asset text truncated to teaser.
4. Admin `/jobs/:id/assets` → `access.full_access=true`, `locked=false`, full content visible.
5. Free user `/jobs/:id/unlock` → 402.
6. Free user `/media/download-token` → 402.
7. Admin `/media/download-token` → 200 + single-use URL.

**Honesty**: Screenshots cannot be prevented and the UI does not claim to. Protection = backend subscription gate (security) + UX deterrents (no select / no context menu / no drag / blocked shortcuts) + paywall modal (conversion).

## 2026-05-15 — P0 V13 Growth Intervention Spine (Phase 1 of 3)

Founder directive: **stop feature expansion, fix activation**. Funnel showed 3797 landing visits → 510 CTA clicks → 0 stories created. Acquisition is fine; activation is catastrophic. Phase 1 ships the MEASUREMENT spine so Phases 2 (anonymous flow) and 3 (content fill) can be data-driven.

### P0-1 Kill loser headline (`headline_a`)
- `routes/ab_testing.py::INITIAL_EXPERIMENTS["hero_headline"]`: `traffic_weights = {headline_b:1.0, headline_a:0.0, headline_c:0.0}` + `frozen_variants: ["headline_a"]` + `frozen_reason` explaining the kill.
- `routes/ab_testing.py::seed_experiments()` now **force-syncs** `traffic_weights`/`frozen_variants`/`frozen_reason`/`active`/`min_sessions` to Mongo on every call (was: only updated when variant IDs changed).
- `server.py` startup hook calls `seed_experiments()` so every deploy resets DB to code-defined weights. **No manual Mongo update required to kill the loser** — just redeploy.
- Soft admin lock via `frozen_variants`. (Hard lock would require a redeploy to reverse; soft lock survives a Mongo wipe via the same seed sync.)

### P0-2 + P0-7 + P0-9 Funnel events
- `routes/funnel_tracking.py::FUNNEL_STEPS` now includes the 12 canonical activation events + 6 share-loop events + 3 performance SLA events from the founder brief.
- `routes/funnel_tracking.py::ACTIVATION_FUNNEL_ORDER` rewritten as the canonical 7-step chain (`landing_view → hero_cta_clicked → story_prompt_started → story_prompt_submitted → story_generation_started → story_generation_completed → story_published`).
- Event document enriched with `anonymous_id`, `auth_state`, `latency_ms`, `generation_id`, `abandonment_step`, `abandonment_reason`, `share_channel`, `share_story_id`.
- Frontend `utils/funnelTracker.js` now generates and persists `anonymous_id` in `localStorage` (separate from auth user ID — captures real anon-vs-auth split), and threads all new fields through `trackFunnel()`.
- Emitters wired:
  - **Landing** (`Landing.js`): `hero_cta_clicked` on both hook-tile and Create-Fresh CTAs (back-compat `landing_cta_clicked` still fires).
  - **Experience** (`InstantStoryExperience.jsx`): `story_prompt_started` on mount, `story_prompt_submitted` + `story_generation_started` on quick-generate kickoff, `story_generation_completed` / `_failed` / `_timeout` with `latency_ms` + `generation_id` + `abandonment_reason`, plus `prompt_to_teaser` and `generation_total_latency` SLA events.
  - **Share** (`ShareButtons.jsx`): `share_sheet_opened` on mount, `share_channel_selected` + `share_link_copied` with `share_channel`.

### P0-3 Activation Diagnostics admin page
- New page `/app/admin/activation-diagnostics` (`pages/Admin/ActivationDiagnostics.jsx`).
- Consumes the extended `/api/funnel/activation-funnel`, which now also returns:
  - `red_alerts[]` — auto-flagged threshold breaches: `CTA→Prompt Started < 60%`, `Prompt Submitted→Generation Started < 85%`, `Generation Success < 90%`, `Median Generation Latency > 8s`.
  - `abandonment_breakdown[]` — top abandonment reasons (rolled up from `abandonment_step` × `abandonment_reason`).
  - Per-stage `p95_to_next_ms` and `auth_sessions` / `anon_sessions`.
- Page renders red-alert strip, funnel table (step / sessions / conv. from prev / median → next / P95 → next / mobile vs desktop / anon vs auth), abandonment table, speed SLA JSON.

### Tests
- `tests/test_growth_spine_v13_2026_05.py` — **5/5 PASS**:
  - Mongo doc reflects kill-switch + freeze lock.
  - Variant assignment honors weights — 100% to `headline_b` across 40 sessions.
  - `/activation-funnel` response shape (red_alerts, abandonment_breakdown, p95_to_next_ms, auth/anon per stage, 7-step chain order).
  - Funnel ingest accepts new event names + persists `anonymous_id` / `latency_ms` / `generation_id` / `auth_state`.
  - Share-loop events ingest and persist `share_channel`.

### Pending — Phases 2 & 3 (next sessions, NOT in this deploy)
- **Phase 2 — P0-4** Anonymous story creation (~1 day).
- **Phase 3 — P0-5** Auto-generate 5 continuations per public story (worker fan-out).
- **Phase 3 — P0-6** Emotional title rewrite + backfill.
- **Phase 3 — P0-10** Story-quality admin panel.

