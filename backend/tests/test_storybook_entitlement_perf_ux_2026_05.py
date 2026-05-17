"""
P0 2026-05-19 — Comic Story Book entitlement + performance + UX fixes.
=====================================================================
Three production bugs surfaced together:

1. ENTITLEMENT — Paid user with sufficient credits saw "Upgrade to
   Download" on their completed comic. Root cause: the global
   `resolve_entitlements()` only honored role=ADMIN/SUPERADMIN and
   plans {starter, pro, premium}. It disagreed with the canonical
   `is_unlimited_user()` helper and the `_PREMIUM_PLANS` set, which
   include {creator, studio} and the is_unlimited flag. Also: the
   Comic Story Book PDF download used the GENERIC media entitlement
   gate (streaming-subscription model) when the asset is per-job
   credit-paid — wrong gate.

2. SLOW GENERATION — 30-page comic took 9m 19s. Root cause:
   `stage_image_generation` ran strictly serial (`for panel in
   panel_prompts:`) — 30 sequential Gemini calls at ~15-25s each.
   R2 page uploads were also strictly serial.

3. BLANK PAGE — Brief blank/static UI between Generate click and the
   moment the backend POST returned. Root cause: progress UI swap
   was gated on `setJob(...)` which only fired AFTER the POST
   resolved.

LOCKED-IN CONTRACT
------------------
1a. `resolve_entitlements()` honors `is_unlimited_user()` AND the
    canonical `_PREMIUM_PLANS` set (creator/studio included).
1b. `/api/comic-storybook-v2/job/{id}` returns a structured
    `entitlement` block with: can_download, upgrade_required, reason,
    subscription_status, credits_available, required_credits,
    is_unlimited, request_id.
1c. Comic Story Book PDF download button renders from per-job
    entitlement, NOT the generic <DownloadWithExpiry>.

2a. `stage_image_generation` uses bounded-concurrency parallel
    generation via `asyncio.Semaphore` + `asyncio.gather`.
2b. Concurrency cap is tier-aware (3/4/6 for free/starter-creator/
    pro-studio-premium-unlimited).
2c. R2 page-image uploads run in parallel under a bounded semaphore.
2d. Page-URL order in the persisted job document is stable (sorted).

3a. Frontend immediately sets an optimistic `job` placeholder
    (id='pending', status='QUEUED', _optimistic=true) so the
    progress card renders within one frame of the click.
3b. Every error path in generateComicBook clears the optimistic
    placeholder so the user is not stranded staring at fake progress.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, "/app/backend")

from services.entitlement import (  # noqa: E402
    resolve_entitlements,
    can_download_asset,
    is_unlimited_user,
    _PREMIUM_PLANS,
)


COMIC_PY = Path("/app/backend/routes/comic_storybook_v2.py")
COMIC_JS = Path("/app/frontend/src/pages/ComicStorybookBuilder.js")
ENTITLEMENT_PY = Path("/app/backend/services/entitlement.py")


# ════════════════════════════════════════════════════════════════════════
# 1. Entitlement resolver — unified with universal helpers
# ════════════════════════════════════════════════════════════════════════
def test_admin_role_can_download():
    """Existing admin bypass must still work."""
    assert can_download_asset({"role": "admin", "plan_type": "free"})
    assert can_download_asset({"role": "ADMIN", "plan_type": "free"})


def test_owner_dev_qa_test_roles_can_download():
    """Production trap: admin/QA/owner users saw 'Upgrade to Download'
    on their own deliverables because the resolver only checked
    ADMIN/SUPERADMIN. is_unlimited_user() expands the bypass set."""
    for role in ("owner", "dev", "qa", "test"):
        assert can_download_asset({"role": role, "plan_type": "free"}), (
            f"role={role!r} must bypass via is_unlimited_user()"
        )


def test_is_unlimited_flag_can_download():
    """The `is_unlimited=True` user flag must also bypass the gate."""
    assert can_download_asset({"is_unlimited": True, "plan_type": "free"})


def test_creator_and_studio_plans_can_download_when_active():
    """Production trap: paying `creator` and `studio` subscribers were
    treated as free because the resolver's eligible-plan set only had
    {starter, pro, premium}. Now aligned with the canonical
    `_PREMIUM_PLANS` set."""
    assert "creator" in _PREMIUM_PLANS
    assert "studio" in _PREMIUM_PLANS
    for plan in ("creator", "studio"):
        ent = resolve_entitlements({
            "plan_type": plan,
            "subscription_status": "active",
        })
        assert ent["can_download"], (
            f"active {plan} subscriber must have can_download=True; "
            f"got {ent}"
        )
        assert not ent["upgrade_required"]


def test_starter_pro_premium_plans_still_eligible():
    """Existing eligible plans must not regress."""
    for plan in ("starter", "pro", "premium"):
        ent = resolve_entitlements({
            "plan_type": plan,
            "subscription_status": "active",
        })
        assert ent["can_download"]


def test_free_user_cannot_download():
    """Free plan + no unlimited flag must NOT download generic media."""
    ent = resolve_entitlements({"plan_type": "free", "subscription_status": "inactive"})
    assert ent["can_download"] is False
    assert ent["upgrade_required"] is True
    assert ent["watermark_required"] is True


def test_top_up_alone_without_subscription_does_not_unlock_generic_download():
    """Documented product rule: top-up credits ALONE don't unlock
    Story Engine downloads (they DO unlock per-job credit-paid
    deliverables — separate gate on the job route)."""
    ent = resolve_entitlements({
        "plan_type": "free",
        "subscription_status": "inactive",
        "credits": 999,
    })
    assert ent["can_download"] is False


# ════════════════════════════════════════════════════════════════════════
# 2. Comic Story Book per-job entitlement block
# ════════════════════════════════════════════════════════════════════════
def test_job_status_endpoint_takes_request_for_request_id():
    """Per-job entitlement block must carry request_id for ops
    correlation — same contract as every other P0 surface."""
    src = COMIC_PY.read_text()
    job_route = src.split("@router.get(\"/job/{job_id}\")", 1)[1].split(
        "\n\n@router.", 1
    )[0]
    assert "http_request: Request" in job_route, (
        "Job status route must accept Request so request_id can be plumbed"
    )
    assert "get_request_id(http_request)" in job_route


def test_job_status_endpoint_emits_structured_entitlement_block():
    """Per-job entitlement block contract: founder-mandated fields."""
    src = COMIC_PY.read_text()
    job_route = src.split("@router.get(\"/job/{job_id}\")", 1)[1].split(
        "\n\n@router.", 1
    )[0]
    assert 'job["entitlement"]' in job_route, (
        "Per-job entitlement block must be stamped on /job/{id} response"
    )
    # Required keys per founder spec.
    for key in (
        "can_download",
        "upgrade_required",
        "reason",
        "subscription_status",
        "credits_available",
        "required_credits",
        "request_id",
    ):
        assert f'"{key}"' in job_route, (
            f"Per-job entitlement block missing field: {key}"
        )


def test_job_status_404_uses_structured_envelope():
    """404 must be a structured envelope, not bare string."""
    src = COMIC_PY.read_text()
    job_route = src.split("@router.get(\"/job/{job_id}\")", 1)[1].split(
        "\n\n@router.", 1
    )[0]
    assert '"code": "JOB_NOT_FOUND"' in job_route
    assert 'detail="Job not found"' not in job_route, (
        "Bare-string detail must be replaced with structured envelope"
    )


# ════════════════════════════════════════════════════════════════════════
# 3. Performance — bounded-concurrency parallel generation
# ════════════════════════════════════════════════════════════════════════
def test_image_generation_is_parallelized_with_semaphore():
    """The strict serial `for panel in panel_prompts:` loop was the
    primary 9-minute bottleneck. Must be replaced with bounded
    concurrency via asyncio.Semaphore + asyncio.gather."""
    src = COMIC_PY.read_text()
    fn = src.split("async def stage_image_generation", 1)[1].split(
        "\nasync def ", 1
    )[0]
    assert "asyncio.Semaphore" in fn, (
        "stage_image_generation must use asyncio.Semaphore for bounded "
        "concurrency"
    )
    assert "asyncio.gather" in fn, (
        "Per-page tasks must be gathered, not sequenced in a for-loop"
    )
    # Tier-aware cap.
    assert "max_concurrent = 6" in fn
    assert "max_concurrent = 4" in fn
    assert "max_concurrent = 3" in fn


def test_image_generation_preserves_retry_budget():
    """Parallelization must NOT cut per-page retry budget."""
    src = COMIC_PY.read_text()
    fn = src.split("async def stage_image_generation", 1)[1].split(
        "\nasync def ", 1
    )[0]
    assert "for attempt in range(max_retries)" in fn, (
        "Per-page retry loop must remain inside the parallel task"
    )


def test_page_uploads_are_parallelized():
    """Page-image R2 uploads must also run in parallel."""
    src = COMIC_PY.read_text()
    fn = src.split("async def stage_storage_upload", 1)[1].split(
        "\nasync def ", 1
    )[0]
    assert "asyncio.gather" in fn, (
        "Page-image uploads in stage_storage_upload must use gather"
    )
    assert "asyncio.Semaphore(6)" in fn, (
        "Page-upload concurrency must be bounded (≤6) to avoid hammering R2"
    )
    # Page order must be stable in the persisted document.
    assert ".sort(key=lambda" in fn, (
        "page_urls must be sorted after parallel uploads complete"
    )


# ════════════════════════════════════════════════════════════════════════
# 4. Frontend — optimistic progress + per-job download gate
# ════════════════════════════════════════════════════════════════════════
def test_generate_handler_sets_optimistic_progress_immediately():
    """The progress card must render within a frame of the click —
    never a blank page between click and POST response."""
    src = COMIC_JS.read_text()
    handler = src.split("const generateComicBook = async () => {", 1)[1].split(
        "// Download handler", 1
    )[0]
    # Optimistic setJob BEFORE the await api.post(...).
    before_post = handler.split("await api.post(", 1)[0]
    assert "_optimistic: true" in before_post, (
        "Optimistic job placeholder must be set BEFORE the POST so the "
        "progress UI swaps in within one frame of the click"
    )
    assert "Starting your comic book…" in before_post or \
           "Starting your comic book" in before_post, (
        "Optimistic placeholder must show a 'Starting…' message"
    )


def test_generate_handler_clears_optimistic_on_every_error_path():
    """When the POST fails, the optimistic progress card must be
    cleared so the user isn't stranded staring at fake progress."""
    src = COMIC_JS.read_text()
    handler = src.split("const generateComicBook = async () => {", 1)[1].split(
        "// Download handler", 1
    )[0]
    catch_block = handler.split("} catch (e) {", 1)[1].split("} finally {", 1)[0]
    # Every early-return after toast.error must call clearOptimistic().
    assert "clearOptimistic" in catch_block, (
        "Error paths must clear the optimistic progress placeholder"
    )
    # At least 4 calls (409, structured, network, catch-all).
    assert catch_block.count("clearOptimistic()") >= 4, (
        f"Expected ≥4 clearOptimistic() calls in catch block; "
        f"found {catch_block.count('clearOptimistic()')}"
    )


def test_pdf_download_button_uses_per_job_entitlement_not_generic_gate():
    """Comic Story Book PDF download must NOT use <DownloadWithExpiry>
    (generic streaming-subscription gate). Must consult per-job
    entitlement signals."""
    src = COMIC_JS.read_text()
    # Strip JS line + block comments so historical references in
    # docstrings don't trip the legacy-class assertion.
    code_only = re.sub(r"//.*$", "", src, flags=re.M)
    code_only = re.sub(r"/\*.*?\*/", "", code_only, flags=re.S)
    # Locate the PDF download block by its canonical testid and
    # examine a 1.5 KB window around it.
    idx = code_only.find('data-testid="comic-pdf-download-btn"')
    assert idx != -1, (
        "Per-job-aware comic PDF download button must keep the canonical "
        "testid for downstream Playwright suites"
    )
    window = code_only[max(0, idx - 1200):idx + 600]
    # Legacy generic wrapper must NOT be the gate used for THIS asset.
    assert "<DownloadWithExpiry" not in window, (
        "Legacy <DownloadWithExpiry> wrapper for Comic Story Book PDF "
        "was the source of the 'Upgrade to Download' trap. Must use "
        "per-job entitlement gate."
    )
    # Per-job entitlement signal consulted.
    assert "job.entitlement?.can_download" in window, (
        "Button must read from the per-job entitlement block returned "
        "by /job/{id}"
    )
    # Per-job ownership fallback (handles legacy / pre-entitlement-block
    # response shape).
    assert ("job.purchased" in window) or ("isUnlimitedUser" in window), (
        "Fallback per-job ownership signal must be present"
    )


def test_generate_button_remains_disabled_during_loading():
    """Smoke: don't regress the double-submit guard."""
    src = COMIC_JS.read_text()
    near = src.split("Generate Full Comic Book", 1)[0][-800:]
    assert "disabled={loading" in near
    assert 'data-testid="generate-btn"' in near
