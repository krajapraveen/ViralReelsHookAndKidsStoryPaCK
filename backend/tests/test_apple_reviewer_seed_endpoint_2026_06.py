"""P0 2026-06 — Apple App Store reviewer seed-or-refresh endpoint.

Apple App Review requires a working demo credential at submission
time. The reviewer account must:
  • always exist with the agreed email + password,
  • have at least 300 credits, and
  • never be in a locked-out state when Apple's reviewers attempt
    to sign in.

The endpoint `POST /api/auth/admin/seed-apple-reviewer` guarantees
those three invariants on whichever environment it is called against
(preview or production). It is master-key-protected and idempotent.

This test pins the endpoint's contract — any future PR that drops
the credit floor, removes the lockout-clearing logic, or weakens
the master-key guard will fail the audit.

Registered under `make audit-boundaries`.
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO = Path("/app")
AUTH_PY = REPO / "backend/routes/auth.py"


@pytest.fixture(scope="module")
def auth_src() -> str:
    assert AUTH_PY.exists(), f"missing {AUTH_PY}"
    return AUTH_PY.read_text()


# ── 1. Endpoint is registered with the right path + verb ─────────────────────


def test_seed_apple_reviewer_endpoint_registered(auth_src: str) -> None:
    assert '@router.post("/admin/seed-apple-reviewer")' in auth_src, (
        "POST /api/auth/admin/seed-apple-reviewer must exist so Apple App "
        "Review credentials can be re-seeded on production without shell "
        "access to the DB."
    )
    assert "async def seed_apple_reviewer(" in auth_src, (
        "Handler must be named seed_apple_reviewer."
    )


# ── 2. Master-key guard is the FIRST check ───────────────────────────────────


def test_seed_apple_reviewer_guarded_by_master_key(auth_src: str) -> None:
    handler_start = auth_src.index("async def seed_apple_reviewer(")
    handler = auth_src[handler_start : handler_start + 4000]
    assert "data.master_key != MASTER_UNLOCK_KEY" in handler, (
        "Endpoint must reject any call whose master_key does not match "
        "MASTER_UNLOCK_KEY. Without this guard anyone could reset the "
        "reviewer password remotely."
    )
    assert 'status_code=403' in handler, (
        "Bad master key must return HTTP 403."
    )


# ── 3. Constants match the value committed to the App Review submission ─────


def test_apple_reviewer_constants_pinned(auth_src: str) -> None:
    assert 'APPLE_REVIEWER_EMAIL = "apple-reviewer@visionary-suite.com"' in auth_src
    assert 'APPLE_REVIEWER_PASSWORD = "Reviewer@VS2026"' in auth_src
    assert "APPLE_REVIEWER_CREDIT_FLOOR = 300" in auth_src, (
        "Credit floor must stay at 300 — the value Apple's reviewers "
        "are told to expect."
    )


# ── 4. Idempotent credit top-up (never doubles) ──────────────────────────────


def test_seed_apple_reviewer_uses_max_floor_top_up(auth_src: str) -> None:
    """Top-up must use max(current, FLOOR) so re-running the endpoint
    never grants credits beyond the floor."""
    assert "max(current_credits, APPLE_REVIEWER_CREDIT_FLOOR)" in auth_src, (
        "Update path must use max(current, FLOOR) to stay idempotent."
    )
    assert "topup = max(0, APPLE_REVIEWER_CREDIT_FLOOR - current_credits)" in auth_src, (
        "Top-up delta must be max(0, FLOOR - current)."
    )


# ── 5. Lockout-clearing is mandatory ─────────────────────────────────────────


def test_seed_apple_reviewer_clears_lockouts(auth_src: str) -> None:
    handler_start = auth_src.index("async def seed_apple_reviewer(")
    handler = auth_src[handler_start : handler_start + 5000]
    assert 'db.account_lockouts.delete_many({"email": email})' in handler, (
        "Endpoint must clear the account_lockouts collection for the "
        "reviewer email — App Review repeatedly fails first attempts."
    )
    assert "login_activity.delete_many" in handler, (
        "Endpoint must also clear FAILED login_activity records so the "
        "failed-attempt counter resets to zero."
    )
    # User-level lock flags must also reset.
    for flag in ('"locked": False', '"accountLocked": False',
                 '"failedLoginAttempts": 0', '"lockUntil": None'):
        assert flag in handler, (
            f"Endpoint must reset user-level lock flag `{flag}`."
        )


# ── 6. Audit ledger entry on credit top-up ───────────────────────────────────


def test_seed_apple_reviewer_writes_credit_ledger(auth_src: str) -> None:
    handler_start = auth_src.index("async def seed_apple_reviewer(")
    handler = auth_src[handler_start : handler_start + 5000]
    assert "db.credit_ledger.insert_one" in handler, (
        "Every credit grant must write a credit_ledger entry for audit."
    )
    assert '"type": "ADMIN_GRANT"' in handler, (
        "Credit ledger entry must use type=ADMIN_GRANT so it is "
        "distinguishable from purchase / signup / refund credits."
    )


# ── 7. Account is created with emailVerified=true so login is not blocked ───


def test_seed_apple_reviewer_creates_verified_account(auth_src: str) -> None:
    handler_start = auth_src.index("async def seed_apple_reviewer(")
    handler = auth_src[handler_start : handler_start + 5000]
    assert '"emailVerified": True' in handler, (
        "Reviewer account must be created with emailVerified=true so "
        "Apple's reviewers do not need access to the mailbox."
    )
    assert '"role": "user"' in handler, (
        "Reviewer must have role=user (not admin) — App Review tests "
        "the consumer flow."
    )
