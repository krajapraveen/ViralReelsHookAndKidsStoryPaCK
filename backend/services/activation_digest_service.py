"""
Activation Digest Service — 2026-05 P0
Founder directive: brutally concise 8 AM IST digest with operational truth only.

Outputs at most these fields:
  LEAK        — single biggest funnel drop (step + magnitude)
  IMPROVE     — single biggest improvement vs prior 24h
  BOTTLENECK  — current worst-conversion step
  DELTA       — pre/post-P0-4 activation delta (when launch ts is set)
  ALERTS[]    — RED if any critical metric drops >20% day-over-day
  NEXT        — exactly ONE recommended next move

Rules:
  • Never fabricate. INSUFFICIENT_DATA verdict if landing sessions < threshold.
  • Confidence label: LOW / MEDIUM / HIGH based on sample size.
  • Keep last 30 digests in DB (`activation_digests`).
  • Email is secondary delivery (SendGrid breaker pattern reused).
  • Admin endpoints must always work even if SendGrid fails.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ─── Thresholds (founder directive — operational only) ────────────
LOW_TRAFFIC_THRESHOLD = 50          # landing sessions / window
MEDIUM_TRAFFIC_THRESHOLD = 200
HIGH_TRAFFIC_THRESHOLD = 1000
REGRESSION_PCT_TRIGGER = 20.0       # >20% drop day-over-day → RED alert
MAX_DIGESTS_RETAINED = 30
COLLECTION_NAME = "activation_digests"

# Reuse the daily-report SendGrid plumbing — same breaker, same logger.
try:
    import sendgrid
    from sendgrid.helpers.mail import Mail, Email, To, HtmlContent
except Exception:
    sendgrid = None
    Mail = Email = To = HtmlContent = None

SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY")
SENDER_EMAIL = os.environ.get("SENDGRID_FROM_EMAIL", "krajapraveen@visionary-suite.com")
DEFAULT_RECIPIENTS = [
    os.environ.get("ACTIVATION_DIGEST_RECIPIENT", "admin@creatorstudio.ai"),
]

# Auth-failure circuit breaker (shared pattern w/ daily_report_service)
_SEND_BREAKER = {"tripped": False, "last_status": None}


# ─── Internal helpers ─────────────────────────────────────────────
def _confidence(landing_sessions: int) -> str:
    if landing_sessions < LOW_TRAFFIC_THRESHOLD:
        return "INSUFFICIENT_DATA"
    if landing_sessions < MEDIUM_TRAFFIC_THRESHOLD:
        return "LOW"
    if landing_sessions < HIGH_TRAFFIC_THRESHOLD:
        return "MEDIUM"
    return "HIGH"


async def _unique_sessions(db, base: dict, step: str | List[str], extra: dict | None = None) -> int:
    match = {**base}
    if isinstance(step, list):
        match["step"] = {"$in": step}
    else:
        match["step"] = step
    if extra:
        match.update(extra)
    rows = await db.funnel_events.aggregate([
        {"$match": match},
        {"$group": {"_id": "$session_id"}},
        {"$count": "n"},
    ]).to_list(1)
    return rows[0]["n"] if rows else 0


async def _activation_metrics(db, window_start: str, window_end: str) -> Dict[str, Any]:
    """Compute the minimum operational metric set for ONE 24h window."""
    base = {"timestamp": {"$gte": window_start, "$lt": window_end}}

    landing = await _unique_sessions(db, base, "landing_view")
    cta = await _unique_sessions(db, base, "hero_cta_clicked")
    prompt_started = await _unique_sessions(db, base, "story_prompt_started")
    generated = await _unique_sessions(
        db, base, ["story_generation_completed", "story_generated_success"]
    )

    # Identify single biggest drop in canonical order
    chain = [
        ("landing_view", landing, "Landing"),
        ("hero_cta_clicked", cta, "CTA Clicked"),
        ("story_prompt_started", prompt_started, "Prompt Started"),
        ("story_generated", generated, "Story Generated"),
    ]
    biggest_drop = None
    for i in range(1, len(chain)):
        prev_step, prev_n, prev_label = chain[i - 1]
        curr_step, curr_n, curr_label = chain[i]
        if prev_n <= 0:
            continue
        conv = (curr_n / prev_n) * 100
        drop_pct = round(100 - conv, 1)
        if biggest_drop is None or drop_pct > biggest_drop["drop_pct"]:
            biggest_drop = {
                "from_step": prev_step,
                "to_step": curr_step,
                "from_label": prev_label,
                "to_label": curr_label,
                "from_sessions": prev_n,
                "to_sessions": curr_n,
                "drop_pct": drop_pct,
                "conv_pct": round(conv, 1),
            }

    # Auth-wall (operational signal for activation collapse)
    auth_wall_rows = await db.funnel_events.aggregate([
        {"$match": {**base, "$or": [
            {"abandonment_reason": {"$in": ["auth_wall_before_preview", "payment_wall_pre_wow"]}},
            {"step": "auth_redirect_loop_detected"},
        ]}},
        {"$group": {"_id": "$session_id"}},
        {"$count": "n"},
    ]).to_list(1)
    auth_wall = auth_wall_rows[0]["n"] if auth_wall_rows else 0

    # Teaser latency median
    latency_rows: List[float] = []
    cursor = db.funnel_events.find(
        {**base, "step": "prompt_to_teaser", "latency_ms": {"$gt": 0}},
        {"_id": 0, "latency_ms": 1},
    )
    async for d in cursor:
        v = d.get("latency_ms")
        if isinstance(v, (int, float)):
            latency_rows.append(v)
    latency_rows.sort()
    teaser_median_ms = int(latency_rows[len(latency_rows) // 2]) if latency_rows else None

    cta_to_gen = round((generated / cta) * 100, 1) if cta else 0.0
    landing_to_gen = round((generated / landing) * 100, 1) if landing else 0.0

    return {
        "landing_sessions": landing,
        "cta_clicked": cta,
        "prompt_started": prompt_started,
        "story_generated": generated,
        "cta_to_generation_pct": cta_to_gen,
        "landing_to_generation_pct": landing_to_gen,
        "auth_wall_sessions": auth_wall,
        "teaser_median_ms": teaser_median_ms,
        "biggest_drop": biggest_drop,
    }


async def _p04_delta(db) -> Optional[Dict[str, Any]]:
    """If P0-4 launch ts is set, return story_generated delta pre vs post."""
    cfg = await db.funnel_config.find_one({"_id": "p04"}, {"_id": 0})
    if not cfg or not cfg.get("p04_launch_ts"):
        return None
    try:
        launch_dt = datetime.fromisoformat(cfg["p04_launch_ts"].replace("Z", "+00:00"))
    except Exception:
        return None

    now = datetime.now(timezone.utc)
    # Symmetric windows: hours_since_launch (capped at 7d), same length pre-launch
    hrs = max(1.0, min((now - launch_dt).total_seconds() / 3600.0, 168.0))
    window = timedelta(hours=hrs)

    pre = await _activation_metrics(db, (launch_dt - window).isoformat(), launch_dt.isoformat())
    post = await _activation_metrics(db, launch_dt.isoformat(), now.isoformat())

    return {
        "p04_launch_ts": cfg["p04_launch_ts"],
        "window_hours": round(hrs, 1),
        "pre_story_generated": pre["story_generated"],
        "post_story_generated": post["story_generated"],
        "story_generated_delta": post["story_generated"] - pre["story_generated"],
        "pre_cta_to_generation_pct": pre["cta_to_generation_pct"],
        "post_cta_to_generation_pct": post["cta_to_generation_pct"],
        "cta_to_generation_pct_delta": round(
            post["cta_to_generation_pct"] - pre["cta_to_generation_pct"], 1
        ),
        "pre_auth_wall": pre["auth_wall_sessions"],
        "post_auth_wall": post["auth_wall_sessions"],
    }


def _detect_regressions(today: Dict[str, Any], yesterday: Dict[str, Any]) -> List[Dict[str, Any]]:
    """RED alert if any critical metric drops >20% day-over-day."""
    alerts: List[Dict[str, Any]] = []

    def _check(metric: str, label: str, higher_better: bool = True):
        t = today.get(metric)
        y = yesterday.get(metric)
        if t is None or y is None or y == 0:
            return
        delta_pct = ((t - y) / y) * 100
        regressed = (higher_better and delta_pct < -REGRESSION_PCT_TRIGGER) or (
            not higher_better and delta_pct > REGRESSION_PCT_TRIGGER
        )
        if regressed:
            alerts.append({
                "metric": metric,
                "label": label,
                "today": t,
                "yesterday": y,
                "delta_pct": round(delta_pct, 1),
                "severity": "RED",
            })

    _check("story_generated", "Story Generated", higher_better=True)
    _check("cta_to_generation_pct", "CTA→Generation %", higher_better=True)
    _check("landing_to_generation_pct", "Landing→Generation %", higher_better=True)
    _check("auth_wall_sessions", "Auth-wall hits", higher_better=False)
    _check("teaser_median_ms", "Teaser latency (ms)", higher_better=False)
    return alerts


def _recommend_next(today: Dict[str, Any], regressions: List[Dict[str, Any]]) -> str:
    """Return EXACTLY ONE next-move string. Operational only."""
    if regressions:
        worst = max(regressions, key=lambda r: abs(r["delta_pct"]))
        return f"INVESTIGATE: {worst['label']} regressed {worst['delta_pct']}%. Check upstream changes in last 24h."

    drop = today.get("biggest_drop")
    if not drop:
        return "Wait for more traffic — current sample too thin for directional decision."

    fr = drop["from_step"]
    if fr == "landing_view":
        return "Reduce above-the-fold load on Landing → CTA: shorten hero, remove dead UI, A/B simpler primary CTA copy."
    if fr == "hero_cta_clicked":
        return "Ship example prompts under the input box (kill blank creative state)."
    if fr == "story_prompt_started":
        return "Ship instant teaser streaming so users see text within 1s of submit."
    if fr == "story_generated":
        return "Improve post-generation hook (Continue CTA visibility) — users see story but don't engage further."
    return "Hold. No clear single intervention yet."


def _format_digest_text(d: Dict[str, Any]) -> str:
    """Brutally concise 6-line operational text. No fluff."""
    lines = [
        f"ACTIVATION DIGEST · {d['report_date']} 08:00 IST",
        f"CONFIDENCE:  {d['confidence']}  (traffic_sample={d['traffic_sample']})",
    ]
    if d["confidence"] == "INSUFFICIENT_DATA":
        lines.append("STATUS:      INSUFFICIENT_DATA — not enough traffic to call directionality.")
        lines.append(f"NEXT:        {d['next_action']}")
        return "\n".join(lines)

    leak = d.get("leak")
    leak_str = (
        f"{leak['from_label']} → {leak['to_label']}  {leak['drop_pct']}%  ({leak['to_sessions']}/{leak['from_sessions']})"
        if leak else "n/a"
    )
    lines.append(f"LEAK:        {leak_str}")

    improve = d.get("improvement")
    improve_str = (
        f"{improve['label']}  {improve['delta_pp']:+}pp"
        if improve else "—"
    )
    lines.append(f"IMPROVE:     {improve_str}")

    bottleneck = d.get("bottleneck")
    bot_str = (
        f"{bottleneck['label']}  {bottleneck['conv_pct']}% conv"
        if bottleneck else "—"
    )
    lines.append(f"BOTTLENECK:  {bot_str}")

    p04 = d.get("p04_delta")
    if p04:
        lines.append(
            f"DELTA:       story_generated {p04['pre_story_generated']} → {p04['post_story_generated']} "
            f"(Δ{p04['story_generated_delta']:+})  ·  cta→gen {p04['cta_to_generation_pct_delta']:+}pp"
        )
    else:
        lines.append("DELTA:       p04_launch_ts not set — call POST /api/funnel/p04-launch on prod")

    alerts = d.get("alerts", [])
    if alerts:
        for a in alerts:
            lines.append(f"ALERT [RED]: {a['label']} {a['delta_pct']}% (today={a['today']} yest={a['yesterday']})")
    else:
        lines.append("ALERTS:      none")

    lines.append(f"NEXT:        {d['next_action']}")
    return "\n".join(lines)


def _format_digest_html(d: Dict[str, Any]) -> str:
    text = _format_digest_text(d)
    return (
        '<div style="font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;'
        'background:#0a0a10;color:#e2e8f0;padding:20px;border-radius:8px;'
        'white-space:pre-wrap;font-size:13px;line-height:1.6;">'
        + text.replace("<", "&lt;").replace(">", "&gt;")
        + "</div>"
    )


# ─── Public service ───────────────────────────────────────────────
class ActivationDigestService:
    def __init__(self, db):
        self.db = db
        self.sg = sendgrid.SendGridAPIClient(api_key=SENDGRID_API_KEY) if (sendgrid and SENDGRID_API_KEY) else None

    async def compute(self, now: Optional[datetime] = None) -> Dict[str, Any]:
        now = now or datetime.now(timezone.utc)
        today_start = now - timedelta(hours=24)
        yesterday_start = now - timedelta(hours=48)

        today = await _activation_metrics(self.db, today_start.isoformat(), now.isoformat())
        yesterday = await _activation_metrics(self.db, yesterday_start.isoformat(), today_start.isoformat())

        confidence = _confidence(today["landing_sessions"])

        # Improvement (highest +pp on conversion rate vs yesterday)
        improvement = None
        for metric, label in [
            ("cta_to_generation_pct", "CTA→Generation"),
            ("landing_to_generation_pct", "Landing→Generation"),
        ]:
            delta = round(today[metric] - yesterday[metric], 1)
            if improvement is None or delta > improvement["delta_pp"]:
                improvement = {"metric": metric, "label": label, "delta_pp": delta}

        # Bottleneck = current biggest drop (same as leak; surface conv side)
        bottleneck = today.get("biggest_drop")
        if bottleneck:
            bottleneck = {
                "step": bottleneck["from_step"],
                "label": f"{bottleneck['from_label']}→{bottleneck['to_label']}",
                "conv_pct": bottleneck["conv_pct"],
            }

        alerts = _detect_regressions(today, yesterday)
        next_action = _recommend_next(today, alerts)

        if confidence == "INSUFFICIENT_DATA":
            next_action = "Wait for traffic. Sample too small for directionality. Push distribution."
            alerts = []  # don't fabricate alerts on noise

        p04_delta = await _p04_delta(self.db)

        digest = {
            "report_date": now.strftime("%Y-%m-%d"),
            "generated_at": now.isoformat(),
            "confidence": confidence,
            "traffic_sample": today["landing_sessions"],
            "leak": today.get("biggest_drop"),
            "improvement": improvement,
            "bottleneck": bottleneck,
            "alerts": alerts,
            "next_action": next_action,
            "p04_delta": p04_delta,
            "today_metrics": today,
            "yesterday_metrics": yesterday,
        }
        return digest

    async def persist(self, digest: Dict[str, Any]) -> str:
        """Insert + trim to MAX_DIGESTS_RETAINED."""
        await self.db[COLLECTION_NAME].insert_one({**digest})
        # Trim — keep newest MAX_DIGESTS_RETAINED
        count = await self.db[COLLECTION_NAME].count_documents({})
        if count > MAX_DIGESTS_RETAINED:
            to_drop = count - MAX_DIGESTS_RETAINED
            oldest = self.db[COLLECTION_NAME].find({}, {"_id": 1}).sort("generated_at", 1).limit(to_drop)
            ids = [d["_id"] async for d in oldest]
            if ids:
                await self.db[COLLECTION_NAME].delete_many({"_id": {"$in": ids}})
        return digest["report_date"]

    async def email(self, digest: Dict[str, Any], recipients: Optional[List[str]] = None) -> Dict[str, Any]:
        """Secondary delivery — never fail loud."""
        recipients = recipients or DEFAULT_RECIPIENTS
        if not self.sg:
            return {"success": False, "error": "SendGrid not configured", "skipped": True}
        if _SEND_BREAKER["tripped"]:
            return {"success": False, "error": f"SendGrid breaker tripped ({_SEND_BREAKER['last_status']})", "skipped": True}

        html = _format_digest_html(digest)
        text = _format_digest_text(digest)
        results = []
        for r in recipients:
            try:
                msg = Mail(
                    from_email=Email(SENDER_EMAIL, "Visionary Suite · Activation"),
                    to_emails=To(r),
                    subject=f"Activation Digest · {digest['report_date']} · {digest['confidence']}",
                    html_content=HtmlContent(html),
                )
                resp = self.sg.send(msg)
                results.append({"recipient": r, "status_code": resp.status_code,
                                "success": resp.status_code in (200, 201, 202)})
            except Exception as e:
                emsg = str(e)
                if "401" in emsg or "403" in emsg:
                    _SEND_BREAKER["tripped"] = True
                    _SEND_BREAKER["last_status"] = "401" if "401" in emsg else "403"
                    logger.warning("[ActivationDigest] SendGrid auth failed (%s); breaker tripped",
                                   _SEND_BREAKER["last_status"])
                results.append({"recipient": r, "success": False, "error": emsg})
        return {"success": all(x["success"] for x in results), "recipients": results,
                "preview_text": text}

    async def run_once(self, also_email: bool = True) -> Dict[str, Any]:
        digest = await self.compute()
        await self.persist(digest)
        email_result = {"skipped": True}
        if also_email:
            email_result = await self.email(digest)
        return {"digest": digest, "email": email_result, "text": _format_digest_text(digest)}


# Singleton
_svc: Optional[ActivationDigestService] = None


def get_activation_digest_service(db) -> ActivationDigestService:
    global _svc
    if _svc is None:
        _svc = ActivationDigestService(db)
    return _svc
