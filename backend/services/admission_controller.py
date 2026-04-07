"""
Load Guard & Admission Controller
==================================
Intelligent pre-job gate with time-series trend detection, per-queue awareness,
graded degradation, and hysteresis recovery.

Guard Modes (aligned with degradation_matrix.py):
  NORMAL    -> All jobs admitted normally
  STRESSED  -> Heavy jobs rejected for free; paid reduced; premium bypass
  SEVERE    -> Most generation rejected except premium/admin
  CRITICAL  -> Hard 429 for all except admin emergency bypass

Signals (30s rolling snapshots, 10-min window):
  - Queue wait time (oldest queued job age per queue)
  - Queue depth trend (net growth over rolling window)
  - Worker saturation (processing / max_concurrent)
  - Dead-letter / stuck-job growth rate
  - Admitted vs completed rate balance

Recovery requires sustained healthy metrics for RECOVERY_HOLD_S
before stepping down one mode. Anti-flap by design.
"""

import asyncio
import logging
import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, List, Tuple

from shared import db

logger = logging.getLogger("load_guard")

# ─── GUARD MODES (match degradation_matrix.py keys) ──────────────────────

GUARD_NORMAL = "normal"
GUARD_STRESSED = "stressed"
GUARD_SEVERE = "severe"
GUARD_CRITICAL = "critical"

# Backward-compatibility aliases used by pipeline_routes.py
LOAD_NORMAL = GUARD_NORMAL
LOAD_STRESSED = GUARD_STRESSED
LOAD_SEVERE = GUARD_SEVERE
LOAD_CRITICAL = GUARD_CRITICAL

MODE_SEVERITY = {
    GUARD_NORMAL: 0,
    GUARD_STRESSED: 1,
    GUARD_SEVERE: 2,
    GUARD_CRITICAL: 3,
}
SEVERITY_TO_MODE = {v: k for k, v in MODE_SEVERITY.items()}

# ─── QUEUE CONFIGURATION ─────────────────────────────────────────────────

QUEUE_TYPES = ["text", "image", "video", "audio", "export", "webhook", "analytics", "batch"]

QUEUE_CAPACITY = {
    "text": 5, "image": 3, "video": 2, "audio": 3,
    "export": 3, "webhook": 5, "analytics": 2, "batch": 1,
}
TOTAL_CAPACITY = sum(QUEUE_CAPACITY.values())

QUEUE_WEIGHT = {
    "text": "light", "webhook": "light", "analytics": "light",
    "image": "medium", "audio": "medium", "export": "medium",
    "video": "heavy", "batch": "heavy",
}

JOB_TYPE_TO_QUEUE = {
    "STORY_GENERATION": "text", "REEL_GENERATION": "text", "CAPTION_GENERATION": "text",
    "TEXT_TO_IMAGE": "image", "COMIC_GENERATION": "image", "PHOTO_TO_COMIC": "image",
    "TEXT_TO_VIDEO": "video", "IMAGE_TO_VIDEO": "video", "VIDEO_REMIX": "video", "STORY_VIDEO": "video",
    "VOICEOVER": "audio", "TTS_GENERATION": "audio", "AUDIO_GENERATION": "audio",
    "EXPORT_VIDEO": "export", "DOWNLOAD_PREP": "export", "WATERMARK_APPLY": "export",
    "BATCH_EXPORT": "batch", "BULK_GENERATE": "batch",
    "COMIC_STORYBOOK": "image",
}

# ─── THRESHOLDS ───────────────────────────────────────────────────────────

WAIT_THRESHOLDS = {
    "light":  {"warn": 15,  "degraded": 30,  "critical": 60},
    "medium": {"warn": 30,  "degraded": 60,  "critical": 120},
    "heavy":  {"warn": 60,  "degraded": 120, "critical": 300},
}

SATURATION_WARN = 85
SATURATION_DEGRADED = 95
SATURATION_CRITICAL = 100

SATURATION_SUSTAIN_S = {"warn": 120, "degraded": 150, "critical": 180}

DEPTH_TREND_WINDOW_S = 300
DEPTH_TREND_THRESHOLD = 3
DEPTH_TREND_SEVERE_MULT = 3

RECOVERY_HOLD_S = 180

SNAPSHOT_INTERVAL_S = 30
MAX_SNAPSHOTS = 20

# Escalation sustain: candidate must persist this long before confirming
ESCALATION_SUSTAIN_S = {
    GUARD_STRESSED: 120,
    GUARD_SEVERE: 150,
    GUARD_CRITICAL: 180,
}

# ─── CONCURRENCY LIMITS PER PLAN ─────────────────────────────────────────

CONCURRENCY_LIMITS = {
    "free": 1, "starter": 3, "weekly": 3, "monthly": 3,
    "creator": 3, "quarterly": 3, "yearly": 3,
    "pro": 5, "premium": 5, "enterprise": 5, "admin": 10, "demo": 5,
}

PREMIUM_PLANS = frozenset(["pro", "premium", "enterprise", "admin", "demo"])
PAID_PLANS = frozenset([
    "weekly", "monthly", "quarterly", "yearly",
    "starter", "creator", "pro", "premium", "enterprise", "admin", "demo",
])

# ─── DATA STRUCTURES ─────────────────────────────────────────────────────


@dataclass
class QueueSnapshot:
    timestamp: float
    queued: int
    processing: int
    oldest_wait_s: float
    max_concurrent: int

    @property
    def saturation_pct(self) -> float:
        if self.max_concurrent == 0:
            return 0.0
        return min(100.0, self.processing / self.max_concurrent * 100)


@dataclass
class SystemSnapshot:
    timestamp: float
    total_queued: int
    total_processing: int
    dead_letter_recent: int
    stuck_count: int
    per_queue: Dict[str, QueueSnapshot]
    admitted_since_last: int
    completed_since_last: int

    @property
    def saturation_pct(self) -> float:
        if TOTAL_CAPACITY == 0:
            return 0.0
        return min(100.0, self.total_processing / TOTAL_CAPACITY * 100)


class AdmissionResult:
    """Result of an admission check. Backward-compatible with existing callers."""
    __slots__ = (
        "admitted", "reason", "retry_after_sec", "load_level",
        "affected_job_types", "queue_position", "eta_sec", "degraded_max_scenes",
    )

    def __init__(
        self, admitted: bool, reason: str = "", retry_after_sec: int = 0,
        load_level: str = GUARD_NORMAL, affected_job_types: list = None,
        queue_position: int = 0, eta_sec: int = 0, degraded_max_scenes: int = 0,
    ):
        self.admitted = admitted
        self.reason = reason
        self.retry_after_sec = retry_after_sec
        self.load_level = load_level
        self.affected_job_types = affected_job_types or []
        self.queue_position = queue_position
        self.eta_sec = eta_sec
        self.degraded_max_scenes = degraded_max_scenes

    def to_dict(self) -> dict:
        d = {
            "admitted": self.admitted,
            "reason": self.reason,
            "guard_mode": self.load_level,
            "load_level": self.load_level,
        }
        if self.degraded_max_scenes:
            d["degraded_max_scenes"] = self.degraded_max_scenes
        if not self.admitted:
            if self.retry_after_sec:
                d["retry_after_sec"] = self.retry_after_sec
            if self.affected_job_types:
                d["affected_job_types"] = self.affected_job_types
            if self.queue_position:
                d["queue_position"] = self.queue_position
            if self.eta_sec:
                d["eta_sec"] = self.eta_sec
        return d


# ─── LOAD GUARD ───────────────────────────────────────────────────────────


class LoadGuard:
    """
    Time-series aware load guard with per-queue intelligence,
    graded degradation, and hysteresis recovery.
    """

    def __init__(self):
        self._snapshots: deque = deque(maxlen=MAX_SNAPSHOTS)
        self._per_queue: Dict[str, deque] = {qt: deque(maxlen=MAX_SNAPSHOTS) for qt in QUEUE_TYPES}

        self._mode = GUARD_NORMAL
        self._mode_since = time.time()
        self._trigger_reasons: List[str] = []

        self._candidate_mode = GUARD_NORMAL
        self._candidate_since: Optional[float] = None

        self._recovery_start: Optional[float] = None

        self._manual_mode: Optional[str] = None
        self._auto_enabled: bool = True
        self._premium_bypass: bool = True
        self._audit_log: deque = deque(maxlen=100)

        self._admitted_since_snapshot: int = 0
        self._completed_at_last_snapshot: int = 0

        self._recent_decisions: deque = deque(maxlen=500)

        self._running = False
        self._task: Optional[asyncio.Task] = None

    # ─── LIFECYCLE ────────────────────────────────────────────────────

    async def start(self):
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._collection_loop())
        logger.info("[LOAD_GUARD] Background snapshot collector started (interval=%ds)", SNAPSHOT_INTERVAL_S)

    def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()

    async def _collection_loop(self):
        while self._running:
            try:
                await self._collect_snapshot()
                self._evaluate_and_update_mode()
            except Exception as e:
                logger.error("[LOAD_GUARD] Snapshot collection error: %s", e, exc_info=True)
            await asyncio.sleep(SNAPSHOT_INTERVAL_S)

    # ─── SNAPSHOT COLLECTION ──────────────────────────────────────────

    async def _collect_snapshot(self):
        now = time.time()
        utc_now = datetime.now(timezone.utc)
        hour_ago = (utc_now - timedelta(hours=1)).isoformat()

        # 1. Aggregation: per-queue counts (queued + processing)
        queue_counts: Dict[tuple, int] = {}
        try:
            pipeline = [
                {"$match": {"status": {"$in": ["QUEUED", "PROCESSING"]}}},
                {"$group": {
                    "_id": {
                        "qt": {"$ifNull": ["$queueType", "unrouted"]},
                        "st": "$status",
                    },
                    "c": {"$sum": 1},
                }},
            ]
            async for doc in db.genstudio_jobs.aggregate(pipeline):
                qt = doc["_id"]["qt"]
                st = doc["_id"]["st"]
                queue_counts[(qt, st)] = doc["c"]
        except Exception as e:
            logger.warning("[LOAD_GUARD] Queue count aggregation failed: %s", e)

        # 2. Aggregation: oldest queued job per queue
        oldest_times: Dict[str, float] = {}
        try:
            oldest_pipe = [
                {"$match": {"status": "QUEUED"}},
                {"$group": {"_id": {"$ifNull": ["$queueType", "unrouted"]}, "oldest": {"$min": "$createdAt"}}},
            ]
            async for doc in db.genstudio_jobs.aggregate(oldest_pipe):
                qt = doc["_id"]
                oldest_str = doc.get("oldest")
                if oldest_str:
                    try:
                        created = datetime.fromisoformat(str(oldest_str).replace("Z", "+00:00"))
                        oldest_times[qt] = max(0.0, (utc_now - created).total_seconds())
                    except Exception:
                        pass
        except Exception as e:
            logger.warning("[LOAD_GUARD] Oldest job aggregation failed: %s", e)

        # 3. Build per-queue snapshots
        per_queue = {}
        total_queued = 0
        total_processing = 0
        for qt in QUEUE_TYPES:
            queued = queue_counts.get((qt, "QUEUED"), 0)
            processing = queue_counts.get((qt, "PROCESSING"), 0)
            qs = QueueSnapshot(
                timestamp=now,
                queued=queued,
                processing=processing,
                oldest_wait_s=oldest_times.get(qt, 0.0),
                max_concurrent=QUEUE_CAPACITY.get(qt, 1),
            )
            per_queue[qt] = qs
            self._per_queue[qt].append(qs)
            total_queued += queued
            total_processing += processing

        total_queued += queue_counts.get(("unrouted", "QUEUED"), 0)
        total_processing += queue_counts.get(("unrouted", "PROCESSING"), 0)

        # 4. Dead letter + stuck jobs
        dead_recent = 0
        stuck = 0
        try:
            dead_recent = await db.dead_letter_jobs.count_documents({"dead_at": {"$gte": hour_ago}})
            stuck_cutoff = (utc_now - timedelta(minutes=10)).isoformat()
            stuck = await db.genstudio_jobs.count_documents({
                "status": "PROCESSING", "startedAt": {"$lt": stuck_cutoff},
            })
        except Exception as e:
            logger.warning("[LOAD_GUARD] Dead-letter/stuck query failed: %s", e)

        # 5. Completed delta
        completed_delta = 0
        try:
            completed_now = await db.genstudio_jobs.count_documents({"status": "COMPLETED"})
            if self._completed_at_last_snapshot > 0:
                completed_delta = max(0, completed_now - self._completed_at_last_snapshot)
            self._completed_at_last_snapshot = completed_now
        except Exception as e:
            logger.warning("[LOAD_GUARD] Completed count failed: %s", e)

        admitted_delta = self._admitted_since_snapshot
        self._admitted_since_snapshot = 0

        snap = SystemSnapshot(
            timestamp=now,
            total_queued=total_queued,
            total_processing=total_processing,
            dead_letter_recent=dead_recent,
            stuck_count=stuck,
            per_queue=per_queue,
            admitted_since_last=admitted_delta,
            completed_since_last=completed_delta,
        )
        self._snapshots.append(snap)

    # ─── MODE EVALUATION ─────────────────────────────────────────────

    def _evaluate_and_update_mode(self):
        # Manual override takes precedence
        if self._manual_mode is not None:
            if self._mode != self._manual_mode:
                old = self._mode
                self._mode = self._manual_mode
                self._mode_since = time.time()
                self._trigger_reasons = [f"Manual override to {self._manual_mode}"]
                logger.warning("[LOAD_GUARD] Manual mode: %s -> %s", old, self._mode)
            return

        if not self._auto_enabled:
            if self._mode != GUARD_NORMAL:
                self._mode = GUARD_NORMAL
                self._mode_since = time.time()
                self._trigger_reasons = []
            return

        if not self._snapshots:
            return

        candidate, reasons = self._compute_candidate_mode()
        now = time.time()
        cand_sev = MODE_SEVERITY[candidate]
        curr_sev = MODE_SEVERITY[self._mode]

        if cand_sev > curr_sev:
            # ── ESCALATION ────────────────────────────────────────────
            self._recovery_start = None
            if self._candidate_mode != candidate:
                self._candidate_mode = candidate
                self._candidate_since = now
                logger.info("[LOAD_GUARD] Escalation candidate: %s (reasons: %s)",
                            candidate, "; ".join(reasons))
            else:
                sustained = now - (self._candidate_since or now)
                required = ESCALATION_SUSTAIN_S.get(candidate, 120)
                if sustained >= required:
                    old = self._mode
                    self._mode = candidate
                    self._mode_since = now
                    self._trigger_reasons = reasons
                    self._candidate_mode = GUARD_NORMAL
                    self._candidate_since = None
                    logger.warning(
                        "[LOAD_GUARD] ESCALATED: %s -> %s (sustained %.0fs, reasons: %s)",
                        old, self._mode, sustained, "; ".join(reasons),
                    )

        elif cand_sev < curr_sev:
            # ── RECOVERY (step down one level at a time) ──────────────
            self._candidate_mode = GUARD_NORMAL
            self._candidate_since = None
            if self._recovery_start is None:
                self._recovery_start = now
                logger.info("[LOAD_GUARD] Recovery conditions met, holding for %ds", RECOVERY_HOLD_S)
            else:
                held = now - self._recovery_start
                if held >= RECOVERY_HOLD_S:
                    new_sev = max(curr_sev - 1, cand_sev)
                    new_mode = SEVERITY_TO_MODE[new_sev]
                    old = self._mode
                    self._mode = new_mode
                    self._mode_since = now
                    self._trigger_reasons = reasons if new_mode != GUARD_NORMAL else []
                    self._recovery_start = None
                    logger.info("[LOAD_GUARD] DE-ESCALATED: %s -> %s (held %.0fs)", old, new_mode, held)
        else:
            # ── STABLE ────────────────────────────────────────────────
            self._candidate_mode = GUARD_NORMAL
            self._candidate_since = None
            self._recovery_start = None
            self._trigger_reasons = reasons

    def _compute_candidate_mode(self) -> Tuple[str, List[str]]:
        votes: List[int] = []
        reasons: List[str] = []
        latest = self._snapshots[-1]

        # ── Signal 1: Per-queue wait times ────────────────────────────
        for qt in QUEUE_TYPES:
            snaps = self._per_queue.get(qt)
            if not snaps:
                continue
            qs = snaps[-1]
            if qs.queued == 0:
                continue
            weight = QUEUE_WEIGHT.get(qt, "medium")
            th = WAIT_THRESHOLDS[weight]

            if qs.oldest_wait_s >= th["critical"]:
                sev = 2 if weight in ("heavy", "medium") else 1
                if qs.oldest_wait_s >= th["critical"] * 2:
                    sev = min(sev + 1, 3)
                votes.append(sev)
                reasons.append(f"{qt} wait {qs.oldest_wait_s:.0f}s >= critical({th['critical']}s)")
            elif qs.oldest_wait_s >= th["degraded"]:
                votes.append(1)
                reasons.append(f"{qt} wait {qs.oldest_wait_s:.0f}s >= degraded({th['degraded']}s)")

        # ── Signal 2: System-wide worker saturation (sustained) ───────
        if self._check_sustained(lambda s: s.saturation_pct >= SATURATION_CRITICAL, SATURATION_SUSTAIN_S["critical"]):
            votes.append(3)
            reasons.append(f"System saturation >= {SATURATION_CRITICAL}% sustained {SATURATION_SUSTAIN_S['critical']}s")
        elif self._check_sustained(lambda s: s.saturation_pct >= SATURATION_DEGRADED, SATURATION_SUSTAIN_S["degraded"]):
            votes.append(2)
            reasons.append(f"System saturation >= {SATURATION_DEGRADED}% sustained {SATURATION_SUSTAIN_S['degraded']}s")
        elif self._check_sustained(lambda s: s.saturation_pct >= SATURATION_WARN, SATURATION_SUSTAIN_S["warn"]):
            votes.append(1)
            reasons.append(f"System saturation >= {SATURATION_WARN}% sustained {SATURATION_SUSTAIN_S['warn']}s")

        # ── Signal 3: Queue depth trend ───────────────────────────────
        depth_trend = self._get_depth_trend()
        median = self._get_median_depth(120)
        if depth_trend > DEPTH_TREND_THRESHOLD * DEPTH_TREND_SEVERE_MULT and median > 10:
            votes.append(2)
            reasons.append(f"Queue depth surging (net +{depth_trend}, median={median:.0f})")
        elif depth_trend > DEPTH_TREND_THRESHOLD and median > 5:
            votes.append(1)
            reasons.append(f"Queue depth rising (net +{depth_trend}, median={median:.0f})")

        # ── Signal 4: Admitted > Completed rate imbalance ─────────────
        a_rate, c_rate = self._get_rates()
        if a_rate > 0 and c_rate >= 0 and a_rate > max(c_rate, 0.1) * 2 and latest.total_queued > 5:
            votes.append(1)
            reasons.append(f"Admission imbalance ({a_rate:.1f} vs {c_rate:.1f}/interval)")

        # ── Signal 5: Dead-letter / stuck growth ──────────────────────
        if latest.stuck_count > 5:
            votes.append(2)
            reasons.append(f"Stuck jobs: {latest.stuck_count}")
        elif latest.stuck_count > 2:
            votes.append(1)
            reasons.append(f"Stuck jobs: {latest.stuck_count}")

        if latest.dead_letter_recent > 10:
            votes.append(2)
            reasons.append(f"Dead letters last hour: {latest.dead_letter_recent}")
        elif latest.dead_letter_recent > 5:
            votes.append(1)
            reasons.append(f"Dead letters last hour: {latest.dead_letter_recent}")

        # ── Signal 6: Per-queue saturation + rising wait (compound) ───
        high_wait_queues = 0
        for qt in QUEUE_TYPES:
            snaps = self._per_queue.get(qt)
            if not snaps:
                continue
            qs = snaps[-1]
            if qs.saturation_pct >= 100 and qs.queued > 0:
                w = QUEUE_WEIGHT.get(qt, "medium")
                sev = 2 if w == "heavy" else 1
                votes.append(sev)
                reasons.append(f"{qt} saturated ({qs.processing}/{qs.max_concurrent}) +{qs.queued} queued")
            if qs.oldest_wait_s > 30:
                high_wait_queues += 1

        if latest.saturation_pct >= SATURATION_DEGRADED and high_wait_queues >= 2:
            compound = min((max(votes) if votes else 0) + 1, 3)
            votes.append(compound)
            reasons.append(f"Compound: saturation {latest.saturation_pct:.0f}% + {high_wait_queues} queues elevated wait")

        max_vote = max(votes) if votes else 0
        mode = SEVERITY_TO_MODE.get(min(max_vote, 3), GUARD_NORMAL)
        return mode, reasons

    # ─── HELPER METHODS ──────────────────────────────────────────────

    def _check_sustained(self, condition, duration_s: float) -> bool:
        if len(self._snapshots) < 2:
            return False
        cutoff = time.time() - duration_s
        relevant = [s for s in self._snapshots if s.timestamp >= cutoff]
        expected = duration_s / SNAPSHOT_INTERVAL_S
        if not relevant or len(relevant) < expected * 0.5:
            return False
        return all(condition(s) for s in relevant)

    def _get_depth_trend(self) -> int:
        if len(self._snapshots) < 2:
            return 0
        cutoff = time.time() - DEPTH_TREND_WINDOW_S
        older = [s for s in self._snapshots if s.timestamp <= cutoff]
        old_snap = older[-1] if older else self._snapshots[0]
        return self._snapshots[-1].total_queued - old_snap.total_queued

    def _get_median_depth(self, window_s: float) -> float:
        cutoff = time.time() - window_s
        depths = [s.total_queued for s in self._snapshots if s.timestamp >= cutoff]
        if not depths:
            return 0
        return sorted(depths)[len(depths) // 2]

    def _get_rates(self) -> Tuple[float, float]:
        if len(self._snapshots) < 2:
            return 0, 0
        recent = list(self._snapshots)[-5:]
        a = sum(s.admitted_since_last for s in recent) / len(recent)
        c = sum(s.completed_since_last for s in recent) / len(recent)
        return a, c

    def _is_queue_overloaded(self, queue_type: str) -> bool:
        snaps = self._per_queue.get(queue_type)
        if not snaps:
            return False
        qs = snaps[-1]
        w = QUEUE_WEIGHT.get(queue_type, "medium")
        th = WAIT_THRESHOLDS[w]
        return qs.oldest_wait_s >= th["degraded"] or (qs.saturation_pct >= 95 and qs.queued > 0)

    def _is_queue_critically_overloaded(self, queue_type: str) -> bool:
        snaps = self._per_queue.get(queue_type)
        if not snaps:
            return False
        qs = snaps[-1]
        w = QUEUE_WEIGHT.get(queue_type, "medium")
        th = WAIT_THRESHOLDS[w]
        return qs.oldest_wait_s >= th["critical"]

    def _get_affected_job_types(self, mode: str) -> list:
        if mode == GUARD_CRITICAL:
            return list(JOB_TYPE_TO_QUEUE.keys())
        if mode == GUARD_SEVERE:
            return [jt for jt, qt in JOB_TYPE_TO_QUEUE.items() if QUEUE_WEIGHT.get(qt) in ("heavy", "medium")]
        if mode == GUARD_STRESSED:
            return [jt for jt, qt in JOB_TYPE_TO_QUEUE.items() if QUEUE_WEIGHT.get(qt) == "heavy"]
        return []

    # ─── ADMISSION CHECK ─────────────────────────────────────────────

    async def check_admission(self, user_id: str, user_plan: str, job_type: str = "") -> AdmissionResult:
        plan = str(user_plan).lower().strip()
        is_paid = plan in PAID_PLANS
        is_premium = plan in PREMIUM_PLANS
        is_admin = plan == "admin"
        job_queue = JOB_TYPE_TO_QUEUE.get(job_type, "")
        job_weight = QUEUE_WEIGHT.get(job_queue, "medium") if job_queue else "medium"

        # ── Check 1: User concurrency limit ───────────────────────────
        max_concurrent = CONCURRENCY_LIMITS.get(plan, CONCURRENCY_LIMITS["free"])
        active_jobs = await db.pipeline_jobs.count_documents({
            "user_id": user_id,
            "status": {"$in": ["QUEUED", "PROCESSING"]},
        })

        if active_jobs >= max_concurrent:
            reason = (
                f"You have {active_jobs} active job(s). Your plan allows {max_concurrent} concurrent jobs. "
                "Please wait for a job to finish."
            ) if is_paid else (
                f"You already have an active video being generated. Free accounts can run "
                f"{max_concurrent} job at a time. Please wait for it to finish or upgrade your plan."
            )
            result = AdmissionResult(
                admitted=False, reason=reason,
                retry_after_sec=30 if is_paid else 60,
                load_level=self._mode,
            )
            self._log_decision(user_id, plan, job_type, result, "concurrency_limit")
            return result

        # ── Check 2: Per-queue specific overload (queue-class aware) ──
        if job_queue and self._is_queue_critically_overloaded(job_queue) and not is_premium:
            affected = [jt for jt, qt in JOB_TYPE_TO_QUEUE.items() if qt == job_queue]
            result = AdmissionResult(
                admitted=False,
                reason="This type of generation is experiencing high demand. Please try again in a few minutes or upgrade to skip the queue.",
                retry_after_sec=60,
                load_level=self._mode,
                affected_job_types=affected,
            )
            self._log_decision(user_id, plan, job_type, result, "queue_overloaded")
            return result

        # ── Check 3: System-wide Load Guard mode ──────────────────────
        guard_mode = self._mode

        if guard_mode == GUARD_CRITICAL:
            if not is_admin:
                result = AdmissionResult(
                    admitted=False,
                    reason="We're under extremely high demand right now. Service is temporarily limited to essential operations only. Please try again shortly.",
                    retry_after_sec=180,
                    load_level=guard_mode,
                    affected_job_types=self._get_affected_job_types(guard_mode),
                )
                self._log_decision(user_id, plan, job_type, result, "critical_guard")
                return result

        if guard_mode == GUARD_SEVERE:
            if not is_premium:
                result = AdmissionResult(
                    admitted=False,
                    reason="We're under high demand right now. Please try again in a few minutes or upgrade your plan.",
                    retry_after_sec=120,
                    load_level=guard_mode,
                    affected_job_types=self._get_affected_job_types(guard_mode),
                )
                self._log_decision(user_id, plan, job_type, result, "severe_guard")
                return result
            if job_weight == "heavy":
                result = AdmissionResult(
                    admitted=False,
                    reason="Heavy processing jobs are temporarily paused due to high demand. Please try a lighter task or wait a few minutes.",
                    retry_after_sec=90,
                    load_level=guard_mode,
                    affected_job_types=[jt for jt, qt in JOB_TYPE_TO_QUEUE.items() if QUEUE_WEIGHT.get(qt) == "heavy"],
                )
                self._log_decision(user_id, plan, job_type, result, "severe_heavy_reject")
                return result

        if guard_mode == GUARD_STRESSED:
            if not is_paid and job_weight == "heavy":
                result = AdmissionResult(
                    admitted=False,
                    reason="Video generation is temporarily paused for free accounts due to high demand. Please try again shortly or upgrade.",
                    retry_after_sec=60,
                    load_level=guard_mode,
                    affected_job_types=[jt for jt, qt in JOB_TYPE_TO_QUEUE.items() if QUEUE_WEIGHT.get(qt) == "heavy"],
                )
                self._log_decision(user_id, plan, job_type, result, "stressed_free_heavy")
                return result
            if not is_paid and job_weight == "medium" and job_queue and self._is_queue_overloaded(job_queue):
                result = AdmissionResult(
                    admitted=False,
                    reason="This type of generation is under high demand right now. Please try again shortly or upgrade.",
                    retry_after_sec=45,
                    load_level=guard_mode,
                    affected_job_types=[jt for jt, qt in JOB_TYPE_TO_QUEUE.items() if qt == job_queue],
                )
                self._log_decision(user_id, plan, job_type, result, "stressed_free_medium_overloaded")
                return result

        # ── Admitted ──────────────────────────────────────────────────
        self._admitted_since_snapshot += 1

        reason = ""
        degraded_scenes = 0
        if guard_mode != GUARD_NORMAL:
            reason = f"System is busy (mode: {guard_mode}). Your request is accepted but may take longer."
            if guard_mode == GUARD_STRESSED and not is_paid:
                degraded_scenes = 2

        result = AdmissionResult(
            admitted=True, reason=reason,
            load_level=guard_mode,
            degraded_max_scenes=degraded_scenes,
        )
        self._log_decision(user_id, plan, job_type, result, "admitted")
        return result

    # ─── DECISION LOGGING ────────────────────────────────────────────

    def _log_decision(self, user_id: str, plan: str, job_type: str, result: AdmissionResult, decision_type: str):
        latest = self._snapshots[-1] if self._snapshots else None
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "user": user_id[:8] if user_id else "?",
            "plan": plan,
            "job_type": job_type or "unknown",
            "decision": decision_type,
            "admitted": result.admitted,
            "guard_mode": result.load_level,
            "queue_depth": latest.total_queued if latest else -1,
            "processing": latest.total_processing if latest else -1,
            "saturation_pct": round(latest.saturation_pct, 1) if latest else -1,
        }
        self._recent_decisions.append(entry)

        log_fn = logger.info if result.admitted else logger.warning
        log_fn(
            "[ADMISSION] %s user=%s plan=%s job=%s mode=%s depth=%d proc=%d sat=%.0f%%",
            decision_type, entry["user"], plan, job_type or "?",
            result.load_level, entry["queue_depth"], entry["processing"], entry["saturation_pct"],
        )

    # ─── ADMIN CONTROLS ──────────────────────────────────────────────

    def set_manual_mode(self, mode: Optional[str], admin_id: str):
        if mode is not None and mode not in MODE_SEVERITY:
            raise ValueError(f"Invalid mode: {mode}. Valid: {list(MODE_SEVERITY.keys())}")
        old_manual = self._manual_mode
        old_mode = self._mode
        self._manual_mode = mode
        # Immediately apply the mode change
        if mode is not None:
            self._mode = mode
            self._mode_since = time.time()
            self._trigger_reasons = [f"Manual override to {mode}"]
            self._recovery_start = None
            self._candidate_since = None
        else:
            # Clearing manual mode: revert to NORMAL, let auto recalculate
            self._mode = GUARD_NORMAL
            self._mode_since = time.time()
            self._trigger_reasons = []
        self._audit_log.append({
            "action": "set_manual_mode", "from": old_manual, "to": mode,
            "mode_was": old_mode, "mode_now": self._mode,
            "admin": admin_id, "ts": datetime.now(timezone.utc).isoformat(),
        })
        logger.warning("[LOAD_GUARD] Admin %s set manual mode: %s -> %s (mode: %s -> %s)",
                        admin_id, old_manual, mode, old_mode, self._mode)

    def set_auto_enabled(self, enabled: bool, admin_id: str):
        old = self._auto_enabled
        self._auto_enabled = enabled
        self._audit_log.append({
            "action": "set_auto_enabled", "from": old, "to": enabled,
            "admin": admin_id, "ts": datetime.now(timezone.utc).isoformat(),
        })
        logger.warning("[LOAD_GUARD] Admin %s set auto_enabled: %s -> %s", admin_id, old, enabled)

    def set_premium_bypass(self, enabled: bool, admin_id: str):
        old = self._premium_bypass
        self._premium_bypass = enabled
        self._audit_log.append({
            "action": "set_premium_bypass", "from": old, "to": enabled,
            "admin": admin_id, "ts": datetime.now(timezone.utc).isoformat(),
        })
        logger.warning("[LOAD_GUARD] Admin %s set premium_bypass: %s -> %s", admin_id, old, enabled)

    # ─── STATUS ──────────────────────────────────────────────────────

    def get_status(self) -> dict:
        latest = self._snapshots[-1] if self._snapshots else None
        now = time.time()

        per_queue_status = {}
        for qt in QUEUE_TYPES:
            snaps = self._per_queue.get(qt)
            if snaps and len(snaps) > 0:
                qs = snaps[-1]
                per_queue_status[qt] = {
                    "queued": qs.queued,
                    "processing": qs.processing,
                    "max_concurrent": qs.max_concurrent,
                    "saturation_pct": round(qs.saturation_pct, 1),
                    "oldest_wait_s": round(qs.oldest_wait_s, 1),
                    "weight_class": QUEUE_WEIGHT.get(qt, "medium"),
                    "overloaded": self._is_queue_overloaded(qt),
                    "critically_overloaded": self._is_queue_critically_overloaded(qt),
                }
            else:
                per_queue_status[qt] = {"status": "no_data"}

        a_rate, c_rate = self._get_rates()
        depth_trend = self._get_depth_trend()

        return {
            "guard_mode": self._mode,
            "mode_since": datetime.fromtimestamp(self._mode_since, tz=timezone.utc).isoformat(),
            "mode_duration_s": round(now - self._mode_since),
            "trigger_reasons": self._trigger_reasons,
            "config": {
                "auto_enabled": self._auto_enabled,
                "manual_mode": self._manual_mode,
                "premium_bypass": self._premium_bypass,
            },
            "signals": {
                "system_saturation_pct": round(latest.saturation_pct, 1) if latest else 0,
                "total_queued": latest.total_queued if latest else 0,
                "total_processing": latest.total_processing if latest else 0,
                "depth_trend_5min": depth_trend,
                "median_depth_2min": round(self._get_median_depth(120), 1),
                "admitted_rate_per_interval": round(a_rate, 1),
                "completed_rate_per_interval": round(c_rate, 1),
                "dead_letter_last_hour": latest.dead_letter_recent if latest else 0,
                "stuck_jobs": latest.stuck_count if latest else 0,
            },
            "per_queue": per_queue_status,
            "recovery": {
                "in_recovery": self._recovery_start is not None,
                "recovery_hold_remaining_s": max(0, round(RECOVERY_HOLD_S - (now - self._recovery_start))) if self._recovery_start else 0,
            },
            "escalation": {
                "candidate_mode": self._candidate_mode,
                "candidate_since": datetime.fromtimestamp(self._candidate_since, tz=timezone.utc).isoformat() if self._candidate_since else None,
                "sustained_s": round(now - self._candidate_since) if self._candidate_since else 0,
            },
            "snapshots_collected": len(self._snapshots),
            "recent_decisions_count": len(self._recent_decisions),
            "audit_log": list(self._audit_log)[-10:],
        }

    def get_recent_decisions(self, limit: int = 50) -> list:
        return list(self._recent_decisions)[-limit:]


# ─── SINGLETON & PUBLIC API ──────────────────────────────────────────────

_load_guard: Optional[LoadGuard] = None


def get_load_guard() -> LoadGuard:
    global _load_guard
    if _load_guard is None:
        _load_guard = LoadGuard()
    return _load_guard


async def check_admission(user_id: str, user_plan: str, job_type: str = "") -> AdmissionResult:
    """Public API: admission check with load guard intelligence."""
    guard = get_load_guard()
    return await guard.check_admission(user_id, user_plan, job_type)


async def get_system_status() -> dict:
    """Backward-compatible system status dict."""
    guard = get_load_guard()
    status = guard.get_status()
    queued = status["signals"]["total_queued"]
    processing = status["signals"]["total_processing"]
    return {
        "queued_jobs": queued,
        "processing_jobs": processing,
        "load_level": status["guard_mode"],
        "system_overloaded": status["guard_mode"] in (GUARD_SEVERE, GUARD_CRITICAL),
        "degradation_active": status["guard_mode"] != GUARD_NORMAL,
        "guard": status,
    }
