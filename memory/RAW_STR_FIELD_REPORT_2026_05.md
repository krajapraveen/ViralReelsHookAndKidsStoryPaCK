# Raw-`str` Payload-Field Prioritized Hit List (Read-Only Report)

**Date:** 2026-05-19
**Scope:** Backend request models + Form/Query/Path params across `/app/backend/{routes,models}/*.py`
**Status:** REPORT ONLY. **No code changed. No fields tightened. No tests written.**
**Freeze invariants still respected:** ✗ Phase 3c, ✗ Phase 4, ✗ canonical migration, ✗ admin panel, ✗ new features, ✗ UI redesign.

---

## 1. Inventory totals

| Metric | Count |
|---|---|
| Total raw `str` / `Optional[str]` request-side field declarations | **615** |
| Files with `BaseModel` containing such fields | 102 |
| Fields named like target keys (style/id/job/order/etc.) | 127 |
| Fields named like enum-shaped slots (severity/status/tier/role/visibility/sort/format/etc.) | 95 |
| Fields named like opaque IDs (id/user_id/session_id/project_id/etc.) | 111 |
| Fields named like free-text user content (title/prompt/message/comment/description/etc.) | 137 |
| Money / credit / payment fields (int already, NOT raw str) | 11 |

These overlap (e.g., `job_id: str` is both a target key and an opaque ID). The classification table below resolves the overlaps deterministically.

---

## 2. P0 — Money / credit / payment / security / token / public-share

**Posture:** These already-tight fields (`amount: int`, `credits: int = Field(ge=0, le=...)`) prove the pattern works. The P0 risk here is mostly **string-shaped IDs that gate money flows** and **auth tokens that gate access**.

| File | Route/Model | Field | Current | Recommended | Reason | Behavior risk |
|---|---|---|---|---|---|---|
| `routes/cashfree_payments.py` | `CashfreeVerifyRequest`, `RefundStatus`, `get_order_status`, `get_refund_status`, `retry_credit_delivery`, `process_refund` | `order_id: str` | `str` | `OrderIdStr` (regex `^[A-Za-z0-9_-]{6,128}$`) | Money-gating path/body keys. Object/array shapes today reach DB queries unfiltered. | Very low — Cashfree order IDs already match. New shape rejects malformed IDs with `VALIDATION_ERROR` envelope instead of a 404. |
| `routes/cashfree_payments.py` | `CashfreeOrderRequest` | `productId: str`, `currency: str = "INR"` | `str` | `currency: Literal["INR"]`; `productId: SlugStr` | Currency is finite-choice (we only ship INR). productId is a slug. | None for `currency`. Low for `productId` if product registry uses slugs. |
| `routes/recovery_ui.py:305` | `recover_download` | `order_id: str` (path) | `str` | `OrderIdStr` | Public-share-adjacent: order ID controls credit re-grant. | None — same shape today. |
| `routes/admin_payments.py:135,477` | Admin payment search | `order_id: Optional[str]` (Query) | `Optional[str]` | `Optional[OrderIdStr]` | Admin search. Filters that should reject objects. | None. |
| `routes/auth.py:90,101` | `ResetPasswordRequest`, `VerifyEmailRequest` | `token: str` | `str` | `TokenStr` (recommend new: `^[A-Za-z0-9_\-\.]{16,512}$`) | Public-share token. JWT-shaped today; current handler does its own validation, but a typed boundary kills entire bug class. | Very low — JWT alphabets fit. |
| `routes/websocket_progress.py:164` | WS job progress | `token: str = Query(...)` | `str` | `TokenStr` | Public WS upgrade token. | Very low. |
| `routes/content_protection_routes.py:35,176,210` | Stream auth | `token: str` (body + Query) | `str` | `TokenStr` | Public stream tokens. | Very low. |
| `routes/security_management.py:42,46` | Sensitive ops | `password: str = Field(..., description=...)`; `otp: str = Field(..., min_length=6, max_length=6)` | mostly OK | `password`: add `min_length=8, max_length=128`; `otp` already tight | Money/security adjacent. Password field has no length cap → DoS-shaped risk. | Low — current users have ≤128-char passwords. |
| `routes/admin.py:38` | `RegisterRequest` (admin create) | `password: str = Field(min_length=8)` | mostly OK | Add `max_length=128` | Same DoS-shaped argument. | None. |
| `routes/anti_abuse_routes.py:37` | OTP submit | `otp: str` | `str` | `Annotated[str, StringConstraints(min_length=6, max_length=8, pattern=r"^\d{6,8}$")]` | OTPs are numeric. Today accepts arbitrary strings. | Very low — should already match. |
| `routes/comix_ai.py:933` | BYO_USER_KEY | `api_key: str = Form(...)` | `str` | `Annotated[str, StringConstraints(min_length=10, max_length=512)]` | Trusted-but-untyped credential field. Length cap = DoS guard. | None. |
| `routes/wallet.py:93-98` | `LedgerEntry` (response shape, but still a Pydantic model) | `entryType: str`, `refType: str`, `status: str` | `str` | `Literal["HOLD","CAPTURE","RELEASE","TOPUP","ADJUST"]`, `Literal["JOB","SUBSCRIPTION","ADMIN","REFUND"]`, `Literal["ACTIVE","REVERSED"]` | Money-ledger enums. Comments already document the allowed values. | None — values are already canonical strings emitted by our code. |
| `models/schemas.py:160` | `OpsEvent.severity` | `severity: str = "ERROR"` | `str` | `Literal["DEBUG","INFO","WARNING","ERROR","CRITICAL"]` | Ops/payment audit log severity. | None — comment confirms canonical set. |
| `models/schemas.py:165-177` | `PaymentLog` model | `status: str`, `currency: str` | `str` | `status: Literal["SUCCESS","FAILED","PENDING","REFUNDED"]`; `currency: Literal["INR","USD"]` | Money ledger response. Comments document the set. | None. |

**P0 count: 14 distinct field shapes.** Most are 1-line fixes via the existing `models/payload_validators.IdStr` / `SlugStr` / `OrderIdStr` types or a new `TokenStr`.

---

## 3. P1 — Enum / finite-choice risk

**Posture:** These fields document their canonical values in a comment (`# SUCCESS, FAILED, PENDING`) but are typed as raw `str`. The `Literal[...]` lock-down pattern we shipped for `mode` / `style` / `voice_id` in the prior pass is the proven recipe.

| # | File | Field | Documented allow-list | Recommended |
|---|---|---|---|---|
| 1 | `routes/photo_to_comic.py:2746` | `mode: str = "single_panel"` | `single_panel` \| `majority_failure` | `Literal["single_panel","majority_failure"]` |
| 2 | `routes/observability_routes.py:148` | `mode: str = "full"` | `full` \| `failed_stage` \| `failed_panels` | `Literal[...]` |
| 3 | `routes/photo_to_comic.py:685` | `mode: Optional[str] = None` (Query filter) | `avatar` \| `strip` | `Optional[Literal["avatar","strip"]]` |
| 4 | `routes/comment_reply_bank.py:55` | `mode: str = Field(..., description="single or full_pack")` | `single` \| `full_pack` | `Literal["single","full_pack"]` |
| 5 | `routes/instant_story.py:39` | `mode: str = Field("fresh", pattern="^(fresh|continue)$")` | already pattern-locked | upgrade to `Literal["fresh","continue"]` for OpenAPI clarity (no behavior change) |
| 6 | `routes/creator_tools.py:220` | `style: str = "all"` (query filter) | `all` plus catalog styles | `Optional[SlugStr]` if free, `Literal[...]` if catalog-bound |
| 7 | `routes/story_video_templates.py:367` | `style: Optional[str]` | story-video style catalog | `Optional[Literal[<catalog keys>]]` |
| 8 | `models/user_analytics.py` (27 raw `str`) | severity/level/category | log severity, analytics buckets | `Literal[...]` per field |
| 9 | `routes/admin*` | `tier`, `role`, `plan`, `policy_type`, `subscription_type` | finite admin sets | `Literal[...]` |
| 10 | `routes/growth_analytics.py` | `target_type`, `reaction_type` | finite engagement sets | `Literal[...]` |
| 11 | `routes/story_video_studio.py` (41 raw `str`) | render quality / aspect_ratio / resolution / aspect / encoding / format / tone | finite media-output sets | `Literal[...]` |
| 12 | `routes/security_vdp.py` | `policy_type`, `severity`, `disclosure_status` | finite VDP states | `Literal[...]` |
| 13 | `routes/login_activity.py` | `event_type`, `risk_level` | login-audit enums | `Literal[...]` |
| 14 | `routes/instagram_bio_generator.py` | `tone`, `vibe`, `niche_category` | catalog choices | `Literal[...]` or `SlugStr` |
| 15 | `routes/offer_generator.py` | `offer_type`, `urgency_tier` | finite offer types | `Literal[...]` |
| 16 | `routes/viral_flywheel.py` | `event_type`, `funnel_stage` | finite funnel labels | `Literal[...]` |

**P1 inventory size:** ~95 raw `str` fields that look enum-shaped. Roughly **35–45 of those are high-confidence Literal candidates** (canonical set documented in a comment). The remaining ~50 are categorical labels (`tone`, `niche`, `genre`) where the set is curated but evolves — those want `SlugStr` + a soft allow-list check inside the handler, not a hard `Literal`.

---

## 4. P2 — ID / slug risk

**Posture:** Opaque ID strings used in path/body. The bug pattern they protect against is identical to the `style` event-trap: a stray non-string reaches a Mongo query or path interpolation. `IdStr` / `JobIdStr` / `SlugStr` from `models/payload_validators.py` are drop-in.

| Group | Approx count | Example files | Recommended type |
|---|---|---|---|
| `job_id: str` in routes/path/body | ~20 | `routes/comic_storybook_v2.py`, `routes/photo_to_comic.py`, `routes/story_video_generation.py`, `routes/websocket_progress.py`, `routes/priority_scaling.py` | `JobIdStr` |
| `order_id: str` in routes/path/body | 6 | `routes/cashfree_payments.py`, `routes/recovery_ui.py`, `routes/revenue_analytics.py`, `routes/self_healing_monitoring.py` | `OrderIdStr` |
| `character_id`, `story_id`, `series_id`, `episode_id`, `chapter_id`, `battle_id`, `session_id`, `project_id`, `video_id`, `image_id`, `asset_id`, `template_id`, `draft_id` | ~70 | most route files | `IdStr` |
| `user_id: str` (typically dependency-injected from auth, not user-controlled) | ~30 | wide | keep `str`; auth dep already validates |
| Slug-like fields (`niche`, `genre`, `audience`, `tone`, `vibe`, `aspect_ratio`, `provider`) | ~30 | wide | `SlugStr` |

**P2 inventory size:** ~127 raw `str` fields matching target-key names; ~75 of those are genuinely user-controlled IDs/slugs that should switch to typed validators. The 30 `user_id` fields look risky but are populated by `Depends(get_current_user)` — verify per route during the tightening pass; don't tighten blindly.

---

## 5. P3 — Free-text / user content (likely keep as `str`)

**Posture:** These fields are intentionally free-form (`title`, `prompt`, `comment`, `caption`). They want `ShortText` / `LongText` length caps for DoS hygiene but NOT enum/regex locks.

| Group | Approx count | Example | Recommended |
|---|---|---|---|
| Display labels & titles | ~35 | `title`, `name`, `display_name`, `caption` | `ShortText` (`max_length=512`) |
| Prompts / story content | ~50 | `prompt`, `initial_prompt`, `story_text`, `description`, `body` | `LongText` (`max_length=8000`) |
| Comments / messages / replies | ~25 | `comment`, `message`, `reply`, `feedback_text` | `LongText` |
| Notes / details / summary | ~15 | `notes`, `details`, `summary`, `reason` | `ShortText` or `LongText` per route |
| URL fields (`avatar_url`, `webhook_url`, `cover_url`, …) | 8 | various | `HttpUrl` from Pydantic (separate audit) |

**P3 inventory size:** ~137 raw `str` fields. **No urgency to tighten.** Adding a `LongText` cap is defense-in-depth; the validation envelope already returns a clean 422 if a payload exceeds FastAPI's default body size.

---

## 6. Top 10 highest-risk fields (manual prioritization)

| Rank | File | Field | Risk class | Why this one |
|---|---|---|---|---|
| 1 | `routes/cashfree_payments.py` | `order_id: str` (×6 sites) | P0 | Money-flow gating. Used in `db.orders.find_one({"order_id": …})` — object/array shape today triggers Mongo-side casting and could surface as an opaque 500. |
| 2 | `routes/auth.py` | `token: str` (reset/verify) | P0 | Public-share token. Object/array today reaches JWT decode in business logic; a typed boundary fails fast with the canonical envelope. |
| 3 | `routes/wallet.py` | `LedgerEntry.entryType / refType / status` | P0 | Money ledger. Becoming `Literal[...]` locks the ledger schema for all writers. |
| 4 | `routes/anti_abuse_routes.py` | `otp: str` | P0 | OTP brute-force surface. Today accepts arbitrary strings of any length; should be 6-digit numeric. |
| 5 | `models/schemas.py` | `PaymentLog.status / currency` | P0 | Payment ledger response shape. `Literal` lock here makes drift impossible. |
| 6 | `routes/content_protection_routes.py` | `token: str` (×3) | P0 | Stream auth tokens. Same shape as auth tokens; same one-line fix. |
| 7 | `routes/comic_storybook_v2.py` | `job_id: str` (×3 paths) | P2-high | Storybook download/transitions/status. Sees the highest user traffic of any payload-keyed route. |
| 8 | `routes/photo_to_comic.py` | `style: str = Form("cartoon_fun")` | P1-high | Already partially protected (frontend coerces, backend has fallback). `Literal[...]` over the 17 SAFE_STYLES finishes the job. Mirrors the `mode` Literal we already shipped. |
| 9 | `routes/photo_to_comic.py:2746` | `mode: str = "single_panel"` | P1 | Internal admin-retry mode field; tiny blast radius but trivial 1-line fix. |
| 10 | `routes/observability_routes.py:148` | `mode: str = "full"` | P1 | Admin diagnostics; trivial 1-line fix. |

---

## 7. Recommended next freeze-safe tightening batch

Three small, surgical batches in this order. Each batch is independently testable and reversible.

### Batch A — Payment & auth boundary (P0, ~14 sites)
- Add `TokenStr` and `OrderIdStr` to `models/payload_validators.py` (the `OrderIdStr` already exists; `TokenStr` is new).
- Tighten the 6 Cashfree `order_id` sites + 5 token sites in `routes/auth.py` / `routes/content_protection_routes.py` / `routes/websocket_progress.py`.
- Tighten `otp` (numeric regex) + `password` length cap.
- Lock `wallet.LedgerEntry` and `PaymentLog` enums via `Literal`.
- Behavior risk: **near zero**. All values already match the new shapes.

### Batch B — `mode` Literal sweep (P1, ~6 sites)
- All `mode: str` fields with a documented `# value1 | value2` comment.
- Behavior risk: **none**. Same recipe as the prior `mode`/`style`/`voice_id` lock-downs that are already live.

### Batch C — `job_id` / `order_id` / `*_id` typed sweep (P2, ~20 sites)
- Apply `JobIdStr` to every path/body `job_id: str` (Comic Storybook, Photo-to-Comic, Story Video, WS).
- Apply `IdStr` to a small first-tier set: `character_id`, `series_id`, `story_id`, `asset_id`.
- Behavior risk: **low**. Existing IDs are UUIDs/ObjectIds/short slugs that match `^[A-Za-z0-9_-]{6,128}$`. Anything that didn't match was already broken upstream.

Each batch should ship with its own regression test that POSTs object/array/null payloads and asserts the canonical `VALIDATION_ERROR` envelope. We can reuse `test_backend_payload_acceptance_2026_05.py` as the template.

### Defer for later (Batch D+, NOT recommended in the current freeze)
- The remaining ~50 categorical labels (`tone`, `niche`, `genre`) — these evolve and want soft allow-list + slug constraint, not `Literal`.
- All ~137 free-text fields — `ShortText`/`LongText` caps are nice-to-have but no production bug ever traced back to them.
- The 30 `user_id` paths — auth dependency already validates; tightening here is theoretical.

---

## 8. Explicit no-code-changed confirmation

- ✅ Zero source files modified in this pass.
- ✅ Zero tests added.
- ✅ Zero validators added or wired.
- ✅ Zero supervisor restarts performed.
- ✅ Live preview backend untouched.
- ✅ Full reliability suite (149 passed / 1 skipped) status unchanged.

This document is the **plan** for the next surgical batch. No batch will land without an explicit greenlight from you naming which batch (A, B, or C) to ship.
