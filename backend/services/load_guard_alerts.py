"""
Load Guard Alert System
========================
Real-time notifications for load guard state changes with:
- Slack webhook delivery (primary channel)
- In-app admin alert log (always persisted to MongoDB)
- Deduplication / cooldown per alert type
- Resolution / recovery alerts
- Incident correlation via unique incident_id
- Non-blocking async delivery (Slack failures never break request flow)
"""

import asyncio
import hashlib
import json
import logging
import os
import time
import urllib.request
import uuid
from collections import deque
from datetime import datetime, timezone
from typing import Optional, Dict, List

from shared import db

logger = logging.getLogger("load_guard_alerts")

SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL", "")

# ─── ALERT TYPES ──────────────────────────────────────────────────────────

ALERT_MODE_ESCALATION = "mode_escalation"
ALERT_MODE_RECOVERY = "mode_recovery"
ALERT_GUARD_FLAPPING = "guard_flapping"
ALERT_DEAD_LETTER_GROWTH = "dead_letter_growth"
ALERT_STUCK_JOBS = "stuck_jobs"
ALERT_QUEUE_WAIT_CRITICAL = "queue_wait_critical"
ALERT_MANUAL_OVERRIDE = "manual_override"

# ─── COOLDOWN (seconds) ──────────────────────────────────────────────────

COOLDOWN_S = {
    ALERT_MODE_ESCALATION: 300,
    ALERT_MODE_RECOVERY: 300,
    ALERT_GUARD_FLAPPING: 600,
    ALERT_DEAD_LETTER_GROWTH: 600,
    ALERT_STUCK_JOBS: 600,
    ALERT_QUEUE_WAIT_CRITICAL: 300,
    ALERT_MANUAL_OVERRIDE: 0,
}

# ─── SLACK FORMATTING ────────────────────────────────────────────────────

MODE_COLORS = {
    "normal": "#36a64f",
    "stressed": "#daa520",
    "severe": "#ff8c00",
    "critical": "#dc143c",
}

MODE_SEVERITY = {"normal": 0, "stressed": 1, "severe": 2, "critical": 3}

FLAPPING_WINDOW_S = 600
FLAPPING_THRESHOLD = 3


class AlertEngine:
    """Core alerting engine with deduplication, persistence, and Slack delivery."""

    def __init__(self):
        self._last_fire: Dict[str, float] = {}
        self._active_incidents: Dict[str, str] = {}
        self._mode_transitions: deque = deque(maxlen=20)
        base = os.environ.get("BACKEND_PUBLIC_URL", os.environ.get("FRONTEND_URL", "")).strip().strip('"')
        self._base_url = base.rstrip("/")

    # ─── DEDUPLICATION ────────────────────────────────────────────────

    def _dedupe_key(self, alert_type: str, mode: str = "", queues: str = "") -> str:
        raw = f"{alert_type}:{mode}:{queues}"
        return hashlib.md5(raw.encode()).hexdigest()[:16]

    def _on_cooldown(self, key: str, alert_type: str, severity_worsened: bool = False) -> bool:
        if alert_type == ALERT_MANUAL_OVERRIDE:
            return False
        if severity_worsened:
            return False
        last = self._last_fire.get(key, 0)
        return (time.time() - last) < COOLDOWN_S.get(alert_type, 300)

    # ─── LINKS ────────────────────────────────────────────────────────

    def _dashboard_link(self) -> str:
        return f"{self._base_url}/admin" if self._base_url else ""

    def _api_link(self) -> str:
        return f"{self._base_url}/api/admin/system-health/load-guard" if self._base_url else ""

    # ─── FIRE ALERT ──────────────────────────────────────────────────

    async def fire(
        self,
        alert_type: str,
        new_mode: str,
        previous_mode: str = "",
        affected_queues: Optional[List[str]] = None,
        signals: Optional[dict] = None,
        admin_id: str = "",
        extra_context: str = "",
    ):
        affected = affected_queues or []
        queues_str = ",".join(sorted(affected))
        key = self._dedupe_key(alert_type, new_mode, queues_str)

        severity_worsened = (
            alert_type == ALERT_MODE_ESCALATION
            and MODE_SEVERITY.get(new_mode, 0) > MODE_SEVERITY.get(previous_mode, 0)
        )

        payload = self._build_payload(
            alert_type, new_mode, previous_mode, affected, signals, admin_id, extra_context,
        )

        if self._on_cooldown(key, alert_type, severity_worsened):
            incident_id = self._active_incidents.get(key, str(uuid.uuid4())[:8])
            payload["incident_id"] = incident_id
            await self._persist(alert_type, "deduped", incident_id, payload)
            return

        # Resolve or reuse incident
        if alert_type == ALERT_MODE_RECOVERY:
            incident_id = self._active_incidents.pop(key, None)
            if not incident_id:
                esc_key = self._dedupe_key(ALERT_MODE_ESCALATION, previous_mode, queues_str)
                incident_id = self._active_incidents.pop(esc_key, str(uuid.uuid4())[:8])
        elif key in self._active_incidents:
            incident_id = self._active_incidents[key]
        else:
            incident_id = str(uuid.uuid4())[:8]
            if alert_type not in (ALERT_MANUAL_OVERRIDE,):
                self._active_incidents[key] = incident_id

        self._last_fire[key] = time.time()
        payload["incident_id"] = incident_id

        status = "resolved" if alert_type == ALERT_MODE_RECOVERY else "active"
        await self._persist(alert_type, status, incident_id, payload)
        asyncio.create_task(self._slack_send(alert_type, payload))

        logger.info(
            "[ALERT] %s: %s->%s incident=%s queues=%s",
            alert_type, previous_mode, new_mode, incident_id, queues_str or "all",
        )

    # ─── PAYLOAD BUILDER ─────────────────────────────────────────────

    def _build_payload(self, alert_type, new_mode, prev_mode, queues, signals, admin_id, extra) -> dict:
        s = signals or {}
        return {
            "alert_type": alert_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "previous_mode": prev_mode,
            "new_mode": new_mode,
            "affected_queues": queues,
            "queue_depth": s.get("total_queued", 0),
            "oldest_wait_s": round(s.get("max_wait_s", 0), 1),
            "worker_saturation_pct": round(s.get("system_saturation_pct", 0), 1),
            "admitted_jobs_per_sec": round(s.get("admitted_rate", 0), 2),
            "completed_jobs_per_sec": round(s.get("completed_rate", 0), 2),
            "dead_letter_count": s.get("dead_letter_recent", 0),
            "stuck_jobs": s.get("stuck_count", 0),
            "depth_trend_5min": s.get("depth_trend", 0),
            "admin_id": admin_id,
            "extra_context": extra,
            "dashboard_link": self._dashboard_link(),
            "api_link": self._api_link(),
        }

    # ─── PERSISTENCE ─────────────────────────────────────────────────

    async def _persist(self, alert_type: str, status: str, incident_id: str, payload: dict):
        try:
            doc = {
                "incident_id": incident_id,
                "alert_type": alert_type,
                "status": status,
                "payload": payload,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            if status == "resolved":
                doc["resolved_at"] = datetime.now(timezone.utc).isoformat()
                doc["resolution_summary"] = (
                    f"Guard recovered: {payload.get('previous_mode', '?')} -> {payload.get('new_mode', '?')}"
                )
            await db.load_guard_alerts.insert_one(doc)
        except Exception as e:
            logger.error("[ALERT] Persist failed: %s", e)

    # ─── SLACK DELIVERY ──────────────────────────────────────────────

    async def _slack_send(self, alert_type: str, payload: dict):
        webhook = SLACK_WEBHOOK_URL
        if not webhook:
            logger.debug("[ALERT] No SLACK_WEBHOOK_URL set, skipping Slack")
            return

        try:
            msg = self._format_slack(alert_type, payload)
            data = json.dumps(msg).encode()

            def _do():
                req = urllib.request.Request(
                    webhook, data=data, headers={"Content-Type": "application/json"},
                )
                urllib.request.urlopen(req, timeout=10)

            await asyncio.to_thread(_do)
            logger.info("[ALERT] Slack sent: %s", alert_type)
        except Exception as e:
            logger.warning("[ALERT] Slack delivery failed: %s", e)

    def _format_slack(self, alert_type: str, payload: dict) -> dict:
        mode = payload.get("new_mode", "unknown")
        prev = payload.get("previous_mode", "unknown")
        color = MODE_COLORS.get(mode, "#808080")

        titles = {
            ALERT_MODE_ESCALATION: f"Load Guard ESCALATED: {prev} -> {mode}",
            ALERT_MODE_RECOVERY: f"Load Guard RECOVERED: {prev} -> {mode}",
            ALERT_GUARD_FLAPPING: f"Load Guard FLAPPING (current: {mode})",
            ALERT_DEAD_LETTER_GROWTH: f"Dead Letter Growth (mode: {mode})",
            ALERT_STUCK_JOBS: f"Stuck Jobs Detected (mode: {mode})",
            ALERT_QUEUE_WAIT_CRITICAL: f"Queue Wait CRITICAL (mode: {mode})",
            ALERT_MANUAL_OVERRIDE: f"Manual Override: {prev} -> {mode}",
        }
        title = titles.get(alert_type, f"Load Guard: {alert_type}")

        fields = [
            {"title": "Guard Mode", "value": f"`{prev}` -> `{mode}`", "short": True},
            {"title": "Incident", "value": f"`{payload.get('incident_id', '?')}`", "short": True},
            {"title": "Queue Depth", "value": str(payload.get("queue_depth", 0)), "short": True},
            {"title": "Oldest Wait", "value": f"{payload.get('oldest_wait_s', 0)}s", "short": True},
            {"title": "Saturation", "value": f"{payload.get('worker_saturation_pct', 0)}%", "short": True},
            {"title": "Depth Trend (5m)", "value": f"{payload.get('depth_trend_5min', 0):+d}", "short": True},
            {"title": "Rates (adm/cmp)", "value": f"{payload.get('admitted_jobs_per_sec', 0):.1f} / {payload.get('completed_jobs_per_sec', 0):.1f}", "short": True},
            {"title": "Dead Letters", "value": str(payload.get("dead_letter_count", 0)), "short": True},
        ]

        if payload.get("stuck_jobs", 0) > 0:
            fields.append({"title": "Stuck Jobs", "value": str(payload["stuck_jobs"]), "short": True})
        if payload.get("affected_queues"):
            fields.append({"title": "Affected Queues", "value": ", ".join(payload["affected_queues"]), "short": False})
        if payload.get("admin_id"):
            fields.append({"title": "Admin", "value": payload["admin_id"], "short": True})
        if payload.get("extra_context"):
            fields.append({"title": "Context", "value": payload["extra_context"], "short": False})

        actions = []
        if payload.get("dashboard_link"):
            actions.append({"type": "button", "text": "Dashboard", "url": payload["dashboard_link"]})
        if payload.get("api_link"):
            actions.append({"type": "button", "text": "API Status", "url": payload["api_link"]})

        return {
            "attachments": [{
                "color": color,
                "title": title,
                "fields": fields,
                "actions": actions,
                "footer": "Load Guard Alert System",
                "ts": int(time.time()),
            }],
        }

    # ─── FLAPPING DETECTION ──────────────────────────────────────────

    def record_transition(self, old_mode: str, new_mode: str):
        self._mode_transitions.append((time.time(), old_mode, new_mode))

    def detect_flapping(self) -> bool:
        cutoff = time.time() - FLAPPING_WINDOW_S
        return sum(1 for t in self._mode_transitions if t[0] >= cutoff) >= FLAPPING_THRESHOLD

    # ─── SIGNAL-BASED CHECKS (called after each snapshot) ────────────

    async def check_signals(self, guard_status: dict):
        signals = guard_status.get("signals", {})
        per_queue = guard_status.get("per_queue", {})
        mode = guard_status.get("guard_mode", "normal")

        sig = {
            "total_queued": signals.get("total_queued", 0),
            "system_saturation_pct": signals.get("system_saturation_pct", 0),
            "dead_letter_recent": signals.get("dead_letter_last_hour", 0),
            "stuck_count": signals.get("stuck_jobs", 0),
            "depth_trend": signals.get("depth_trend_5min", 0),
            "admitted_rate": signals.get("admitted_rate_per_interval", 0),
            "completed_rate": signals.get("completed_rate_per_interval", 0),
            "max_wait_s": 0,
        }

        critical_queues = []
        for qt, qs in per_queue.items():
            if isinstance(qs, dict):
                w = qs.get("oldest_wait_s", 0)
                if w > sig["max_wait_s"]:
                    sig["max_wait_s"] = w
                if qs.get("critically_overloaded"):
                    critical_queues.append(qt)

        if signals.get("dead_letter_last_hour", 0) > 5:
            await self.fire(
                ALERT_DEAD_LETTER_GROWTH, mode, signals=sig,
                extra_context=f"Dead letters last hour: {signals['dead_letter_last_hour']}",
            )

        if signals.get("stuck_jobs", 0) > 2:
            await self.fire(
                ALERT_STUCK_JOBS, mode, signals=sig,
                extra_context=f"Stuck jobs: {signals['stuck_jobs']}",
            )

        if critical_queues:
            await self.fire(
                ALERT_QUEUE_WAIT_CRITICAL, mode,
                affected_queues=critical_queues, signals=sig,
                extra_context=f"Critical wait in: {', '.join(critical_queues)}",
            )

        if self.detect_flapping():
            await self.fire(
                ALERT_GUARD_FLAPPING, mode, signals=sig,
                extra_context="Multiple mode transitions in short window",
            )


# ─── SINGLETON ────────────────────────────────────────────────────────────

_engine: Optional[AlertEngine] = None


def get_alert_engine() -> AlertEngine:
    global _engine
    if _engine is None:
        _engine = AlertEngine()
    return _engine
