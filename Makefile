# CreatorStudio Engineering Makefile
#
# All targets are CI-safe (no interactive prompts, deterministic exits).
# The boundary audit gate is `make audit-boundaries` — see the
# Engineering Doctrine at /app/memory/ENGINEERING_DOCTRINE.md.

SHELL := /bin/bash

# ─── Audit suite registry ────────────────────────────────────────────
# When you add a new audit, append its file path here. Every PR runs
# the full registry; no human memory dependency.
BOUNDARY_AUDIT_SUITES := \
	backend/tests/test_event_trap_audit_2026_05.py \
	backend/tests/test_payload_boundary_audit_2026_05.py \
	backend/tests/test_url_boundary_audit_2026_05.py \
	backend/tests/test_backend_payload_acceptance_2026_05.py \
	backend/tests/test_payment_auth_batch_a_2026_05.py \
	backend/tests/test_completion_invariant_audit_2026_05.py \
	backend/tests/test_diagnostics_beacon_2026_05.py \
	backend/tests/test_doctrine_and_ci_gate_2026_05.py \
	backend/tests/test_bug_class_elimination_mandate_2026_05.py \
	backend/tests/test_reaction_gif_connection_loss_2026_05.py \
	backend/tests/test_reaction_gif_false_success_2026_05.py \
	backend/tests/test_reaction_gif_honest_progress_2026_05.py \
	backend/tests/test_reaction_gif_stuck_job_2026_05.py \
	backend/tests/test_google_ads_conversion_audit_2026_05.py \
	backend/tests/test_story_async_contract_2026_05.py \
	backend/tests/test_my_space_preview_cta_2026_05.py \
	backend/tests/test_p2c_event_trap_2026_05.py \
	backend/tests/test_p2c_style_validation_safety_net_2026_05.py \
	backend/tests/test_p2c_object_state_hotfix_2026_05.py \
	backend/tests/test_p2c_cache_bust_2026_05.py \
	backend/tests/test_strip_completion_invariant_2026_05.py \
	backend/tests/test_storybook_next_action_hooks_2026_05.py \
	backend/tests/test_silent_render_prevention_2026_05.py \
	backend/tests/test_empty_myspace_after_create_2026_05.py \
	backend/tests/test_story_video_locating_surface_2026_05.py \
	backend/tests/test_draft_already_active_recovery_2026_05.py \
	backend/tests/test_retry_visibility_contract_2026_05.py \
	backend/tests/test_audio_video_duration_parity_2026_05.py \
	backend/tests/test_pricing_canonical_source_2026_05.py \
	backend/tests/test_billing_decoupled_fetch_and_session_2026_05.py \
	backend/tests/test_protected_route_next_redirect_2026_06.py \
	backend/tests/test_safe_redirect_open_redirect_guard_2026_06.py \
	backend/tests/test_navigation_sink_audit_2026_06.py \
	backend/tests/test_backend_redirect_sink_audit_2026_06.py \
	backend/tests/test_premium_subscription_clarity_2026_06.py \
	backend/tests/test_entitlement_sync_after_webhook_2026_06.py \
	backend/tests/test_entitlement_consolidation_2026_06.py \
	backend/tests/test_photo_trailer_credit_integrity_2026_06.py \
	backend/tests/test_photo_trailer_kill_switch_2026_06.py

PYTEST := python -m pytest


# ─── Primary CI gate ─────────────────────────────────────────────────

.PHONY: audit-boundaries
audit-boundaries:  ## Run every boundary audit. Merge gate.
	@echo "════════════════════════════════════════════════════════════"
	@echo "  CreatorStudio boundary audit"
	@echo "  Doctrine: 'Never allow unvalidated input, ambiguous"
	@echo "  state, or silent failure to cross a system boundary.'"
	@echo "════════════════════════════════════════════════════════════"
	@$(PYTEST) $(BOUNDARY_AUDIT_SUITES) -v --tb=short

.PHONY: audit-boundaries-quick
audit-boundaries-quick:  ## Same suite but quiet — for pre-push hooks.
	@$(PYTEST) $(BOUNDARY_AUDIT_SUITES) -q --tb=line

.PHONY: audit-boundaries-report
audit-boundaries-report:  ## JUnit XML report — for CI artifact upload.
	@mkdir -p /app/test_reports
	@$(PYTEST) $(BOUNDARY_AUDIT_SUITES) -q --tb=short \
		--junitxml=/app/test_reports/audit_boundaries.xml

.PHONY: audit-boundaries-coverage
audit-boundaries-coverage:  ## Print registered pipelines + migration backlog.
	@cd /app && python3 backend/scripts/audit_boundaries_coverage.py


# ─── Lint ────────────────────────────────────────────────────────────

.PHONY: lint
lint:  ## Lint backend + frontend.
	@cd /app/backend && python -m ruff check .
	@cd /app/frontend && yarn -s lint || true


# ─── Convenience composites ──────────────────────────────────────────

.PHONY: pre-merge
pre-merge: lint audit-boundaries  ## Run before opening / merging a PR.


# ─── Self-documenting help ───────────────────────────────────────────

.PHONY: help
help:  ## Print every target with its docstring.
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(firstword $(MAKEFILE_LIST)) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-30s\033[0m %s\n", $$1, $$2}'

.DEFAULT_GOAL := help
