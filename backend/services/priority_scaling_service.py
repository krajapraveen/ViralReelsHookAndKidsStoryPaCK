"""
CreatorStudio AI - Auto-Scaling & Priority Lanes Service
=========================================================
Implements:
1. Intelligent auto-scaling based on queue depth, latency, and error rates
2. Priority lanes for premium users with guaranteed processing times
3. Dynamic worker allocation across job types
"""
import asyncio
import os
import sys
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import db, logger

# ============================================
# PRIORITY LANES CONFIGURATION
# ============================================

class UserTier(Enum):
    """User subscription tiers"""
    FREE = "free"
    BASIC = "basic"
    PRO = "pro"
    ENTERPRISE = "enterprise"

# Priority configuration per tier (lower number = higher priority)
TIER_PRIORITIES = {
    UserTier.ENTERPRISE: 1,
    UserTier.PRO: 2,
    UserTier.BASIC: 3,
    UserTier.FREE: 4
}

# Queue configuration per tier
TIER_CONFIG = {
    UserTier.ENTERPRISE: {
        "priority": 1,
        "max_concurrent_jobs": 20,
        "max_queue_size": 100,
        "timeout_multiplier": 1.5,  # 50% more time allowed
        "guaranteed_sla_seconds": 30,  # Job starts within 30s
        "retry_boost": 2,  # Extra retry attempts
        "dedicated_worker_percent": 30  # 30% of workers dedicated
    },
    UserTier.PRO: {
        "priority": 2,
        "max_concurrent_jobs": 10,
        "max_queue_size": 50,
        "timeout_multiplier": 1.2,
        "guaranteed_sla_seconds": 60,
        "retry_boost": 1,
        "dedicated_worker_percent": 20
    },
    UserTier.BASIC: {
        "priority": 3,
        "max_concurrent_jobs": 5,
        "max_queue_size": 25,
        "timeout_multiplier": 1.0,
        "guaranteed_sla_seconds": 120,
        "retry_boost": 0,
        "dedicated_worker_percent": 0
    },
    UserTier.FREE: {
        "priority": 4,
        "max_concurrent_jobs": 2,
        "max_queue_size": 10,
        "timeout_multiplier": 1.0,
        "guaranteed_sla_seconds": 300,  # 5 min SLA for free
        "retry_boost": 0,
        "dedicated_worker_percent": 0
    }
}

# ============================================
# AUTO-SCALING CONFIGURATION
# ============================================

@dataclass
class ScalingRule:
    """Define a scaling rule with conditions and actions"""
    name: str
    metric: str  # queue_depth, error_rate, latency_p95
    operator: str  # gt, lt, gte, lte
    threshold: float
    action: str  # scale_up, scale_down
    scale_amount: int = 1
    cooldown_seconds: int = 60
    sustained_seconds: int = 30  # Condition must persist
    enabled: bool = True

# Default scaling rules
DEFAULT_SCALING_RULES = [
    # Scale UP rules
    ScalingRule(
        name="high_queue_depth",
        metric="queue_depth",
        operator="gt",
        threshold=50,
        action="scale_up",
        scale_amount=2,
        cooldown_seconds=60,
        sustained_seconds=30
    ),
    ScalingRule(
        name="very_high_queue_depth",
        metric="queue_depth",
        operator="gt",
        threshold=100,
        action="scale_up",
        scale_amount=4,
        cooldown_seconds=30,
        sustained_seconds=15
    ),
    ScalingRule(
        name="high_latency",
        metric="latency_p95",
        operator="gt",
        threshold=5000,  # 5 seconds
        action="scale_up",
        scale_amount=1,
        cooldown_seconds=120,
        sustained_seconds=60
    ),
    ScalingRule(
        name="premium_queue_growing",
        metric="premium_queue_depth",
        operator="gt",
        threshold=10,
        action="scale_up",
        scale_amount=2,
        cooldown_seconds=30,
        sustained_seconds=15
    ),
    # Scale DOWN rules
    ScalingRule(
        name="low_queue_depth",
        metric="queue_depth",
        operator="lt",
        threshold=5,
        action="scale_down",
        scale_amount=1,
        cooldown_seconds=120,
        sustained_seconds=120
    ),
    ScalingRule(
        name="very_low_queue_depth",
        metric="queue_depth",
        operator="lt",
        threshold=2,
        action="scale_down",
        scale_amount=2,
        cooldown_seconds=180,
        sustained_seconds=180
    ),
]

@dataclass
class AutoScalingConfig:
    """Main auto-scaling configuration"""
    min_workers: int = 2
    max_workers: int = 20
    current_workers: int = 2
    scale_up_cooldown: int = 60
    scale_down_cooldown: int = 120
    last_scale_up: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_scale_down: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    rules: List[ScalingRule] = field(default_factory=lambda: DEFAULT_SCALING_RULES.copy())


# ============================================
# PRIORITY LANE MANAGER
# ============================================

class PriorityLaneManager:
    """
    Manages priority lanes for different user tiers
    Ensures premium users get faster processing
    """
    
    def __init__(self):
        self.lane_stats: Dict[str, Dict] = {
            tier.value: {
                "queued": 0,
                "processing": 0,
                "completed_today": 0,
                "avg_wait_time": 0,
                "sla_violations": 0
            }
            for tier in UserTier
        }
    
    @staticmethod
    async def get_user_tier(user_id: str) -> UserTier:
        """Get user's subscription tier"""
        try:
            user = await db.users.find_one({"id": user_id}, {"subscription_tier": 1, "is_premium": 1})
            if not user:
                return UserTier.FREE
            
            tier_str = user.get("subscription_tier", "free")
            if user.get("is_premium") and tier_str == "free":
                tier_str = "basic"  # Upgrade premium flag users to basic
            
            try:
                return UserTier(tier_str.lower())
            except ValueError:
                return UserTier.FREE
        except Exception:
            return UserTier.FREE
    
    @staticmethod
    def get_tier_config(tier: UserTier) -> Dict:
        """Get configuration for a tier"""
        return TIER_CONFIG.get(tier, TIER_CONFIG[UserTier.FREE])
    
    async def assign_priority(self, user_id: str, job_type: str) -> Dict[str, Any]:
        """
        Assign priority to a job based on user tier
        Returns priority settings for the job
        """
        tier = await self.get_user_tier(user_id)
        config = self.get_tier_config(tier)
        
        # Check if user has exceeded concurrent job limit
        active_jobs = await db.jobs.count_documents({
            "user_id": user_id,
            "state": {"$in": ["pending", "in_progress", "retrying"]}
        })
        
        if active_jobs >= config["max_concurrent_jobs"]:
            return {
                "allowed": False,
                "reason": f"Max concurrent jobs ({config['max_concurrent_jobs']}) reached",
                "tier": tier.value,
                "upgrade_suggestion": self._get_upgrade_suggestion(tier)
            }
        
        # Calculate effective priority (lower = higher priority)
        # Base priority from tier + job type modifier
        job_type_modifiers = {
            "video": 0,      # Video gets slight boost
            "image": 0.1,
            "text": 0.2,
            "export": 0.3,
            "gif": 0.2
        }
        
        base_priority = config["priority"]
        modifier = job_type_modifiers.get(job_type, 0.5)
        effective_priority = base_priority + modifier
        
        return {
            "allowed": True,
            "tier": tier.value,
            "priority": effective_priority,
            "timeout_multiplier": config["timeout_multiplier"],
            "retry_boost": config["retry_boost"],
            "sla_seconds": config["guaranteed_sla_seconds"],
            "is_premium": tier in [UserTier.PRO, UserTier.ENTERPRISE]
        }
    
    def _get_upgrade_suggestion(self, current_tier: UserTier) -> Optional[str]:
        """Get upgrade suggestion based on current tier"""
        suggestions = {
            UserTier.FREE: "Upgrade to Basic for 5 concurrent jobs",
            UserTier.BASIC: "Upgrade to Pro for 10 concurrent jobs and priority processing",
            UserTier.PRO: "Upgrade to Enterprise for unlimited concurrent jobs"
        }
        return suggestions.get(current_tier)
    
    async def get_queue_position(self, job_id: str, user_id: str) -> Dict[str, Any]:
        """
        Get job's position in the priority queue
        """
        tier = await self.get_user_tier(user_id)
        config = self.get_tier_config(tier)
        
        # Get the job
        job = await db.jobs.find_one({"job_id": job_id}, {"_id": 0})
        if not job:
            return {"error": "Job not found"}
        
        job_priority = job.get("priority", 4)
        job_created = job.get("created_at")
        
        # Count jobs ahead in queue
        ahead_query = {
            "state": "pending",
            "$or": [
                {"priority": {"$lt": job_priority}},
                {
                    "priority": job_priority,
                    "created_at": {"$lt": job_created}
                }
            ]
        }
        
        jobs_ahead = await db.jobs.count_documents(ahead_query)
        
        # Estimate wait time based on current processing rate
        avg_processing_time = 30  # Default 30s
        estimated_wait = jobs_ahead * avg_processing_time
        
        return {
            "position": jobs_ahead + 1,
            "jobs_ahead": jobs_ahead,
            "estimated_wait_seconds": estimated_wait,
            "tier": tier.value,
            "sla_seconds": config["guaranteed_sla_seconds"],
            "within_sla": estimated_wait <= config["guaranteed_sla_seconds"]
        }
    
    async def get_lane_stats(self) -> Dict[str, Any]:
        """Get statistics for all priority lanes"""
        stats = {}
        
        for tier in UserTier:
            tier_value = tier.value
            config = self.get_tier_config(tier)
            
            # Get counts from database
            queued = await db.jobs.count_documents({
                "tier": tier_value,
                "state": "pending"
            })
            
            processing = await db.jobs.count_documents({
                "tier": tier_value,
                "state": "in_progress"
            })
            
            # Get completed in last 24h
            yesterday = datetime.now(timezone.utc) - timedelta(hours=24)
            completed = await db.jobs.count_documents({
                "tier": tier_value,
                "state": "completed",
                "completed_at": {"$gte": yesterday.isoformat()}
            })
            
            stats[tier_value] = {
                "queued": queued,
                "processing": processing,
                "completed_24h": completed,
                "priority": config["priority"],
                "sla_seconds": config["guaranteed_sla_seconds"],
                "max_concurrent": config["max_concurrent_jobs"]
            }
        
        return stats


# ============================================
# AUTO-SCALING ENGINE
# ============================================

class AutoScalingEngine:
    """
    Intelligent auto-scaling engine that adjusts worker count
    based on multiple metrics and configurable rules
    """
    
    def __init__(self):
        self.config = AutoScalingConfig()
        self.metric_history: Dict[str, List[Dict]] = {
            "queue_depth": [],
            "error_rate": [],
            "latency_p95": [],
            "premium_queue_depth": [],
            "worker_utilization": []
        }
        self.scaling_history: List[Dict] = []
        self._running = False
        self._task = None
    
    async def start(self):
        """Start the auto-scaling engine"""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._scaling_loop())
        logger.info("Auto-scaling engine started")
    
    async def stop(self):
        """Stop the auto-scaling engine"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Auto-scaling engine stopped")
    
    async def _scaling_loop(self):
        """Main scaling loop - runs every 10 seconds"""
        while self._running:
            try:
                await self._collect_metrics()
                await self._evaluate_rules()
                await asyncio.sleep(10)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Auto-scaling error: {e}")
                await asyncio.sleep(30)
    
    async def _collect_metrics(self):
        """Collect current metrics"""
        now = datetime.now(timezone.utc)
        
        # Queue depth
        queue_depth = await db.jobs.count_documents({"state": "pending"})
        self._record_metric("queue_depth", queue_depth)
        
        # Premium queue depth (Enterprise + Pro users)
        premium_depth = await db.jobs.count_documents({
            "state": "pending",
            "tier": {"$in": ["enterprise", "pro"]}
        })
        self._record_metric("premium_queue_depth", premium_depth)
        
        # Processing jobs
        processing = await db.jobs.count_documents({"state": "in_progress"})
        if self.config.current_workers > 0:
            utilization = (processing / self.config.current_workers) * 100
            self._record_metric("worker_utilization", utilization)
        
        # Calculate latency from recent completed jobs
        recent_jobs = await db.jobs.find(
            {
                "state": "completed",
                "completed_at": {"$gte": (now - timedelta(minutes=5)).isoformat()}
            },
            {"_id": 0, "created_at": 1, "started_at": 1}
        ).to_list(100)
        
        if recent_jobs:
            latencies = []
            for job in recent_jobs:
                try:
                    created = datetime.fromisoformat(job.get("created_at", "").replace("Z", "+00:00"))
                    started = datetime.fromisoformat(job.get("started_at", "").replace("Z", "+00:00"))
                    latencies.append((started - created).total_seconds() * 1000)
                except:
                    pass
            
            if latencies:
                latencies.sort()
                p95_idx = int(len(latencies) * 0.95)
                p95_latency = latencies[p95_idx] if p95_idx < len(latencies) else latencies[-1]
                self._record_metric("latency_p95", p95_latency)
        
        # Error rate (failures in last 5 min)
        five_min_ago = now - timedelta(minutes=5)
        total_jobs = await db.jobs.count_documents({
            "updated_at": {"$gte": five_min_ago.isoformat()}
        })
        failed_jobs = await db.jobs.count_documents({
            "state": "failed",
            "updated_at": {"$gte": five_min_ago.isoformat()}
        })
        
        if total_jobs > 0:
            error_rate = (failed_jobs / total_jobs) * 100
            self._record_metric("error_rate", error_rate)
    
    def _record_metric(self, metric: str, value: float):
        """Record a metric value"""
        if metric not in self.metric_history:
            self.metric_history[metric] = []
        
        self.metric_history[metric].append({
            "value": value,
            "time": datetime.now(timezone.utc).isoformat()
        })
        
        # Keep last 60 samples (10 minutes at 10s intervals)
        if len(self.metric_history[metric]) > 60:
            self.metric_history[metric].pop(0)
    
    def _get_metric_value(self, metric: str, window_seconds: int = 30) -> Optional[float]:
        """Get average metric value over window"""
        if metric not in self.metric_history or not self.metric_history[metric]:
            return None
        
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=window_seconds)
        recent = [
            m["value"] for m in self.metric_history[metric]
            if datetime.fromisoformat(m["time"].replace("Z", "+00:00")) >= cutoff
        ]
        
        if not recent:
            return None
        
        return sum(recent) / len(recent)
    
    def _check_condition(self, value: float, operator: str, threshold: float) -> bool:
        """Check if a condition is met"""
        if operator == "gt":
            return value > threshold
        elif operator == "lt":
            return value < threshold
        elif operator == "gte":
            return value >= threshold
        elif operator == "lte":
            return value <= threshold
        return False
    
    async def _evaluate_rules(self):
        """Evaluate scaling rules and take action"""
        now = datetime.now(timezone.utc)
        
        for rule in self.config.rules:
            if not rule.enabled:
                continue
            
            # Get metric value over sustained period
            value = self._get_metric_value(rule.metric, rule.sustained_seconds)
            if value is None:
                continue
            
            # Check condition
            if not self._check_condition(value, rule.operator, rule.threshold):
                continue
            
            # Check cooldown
            if rule.action == "scale_up":
                if (now - self.config.last_scale_up).total_seconds() < rule.cooldown_seconds:
                    continue
                
                # Perform scale up
                new_workers = min(
                    self.config.current_workers + rule.scale_amount,
                    self.config.max_workers
                )
                
                if new_workers > self.config.current_workers:
                    await self._perform_scaling(
                        "up", 
                        new_workers - self.config.current_workers,
                        rule.name,
                        value,
                        rule.threshold
                    )
                    self.config.last_scale_up = now
                    break  # Only one scale action per cycle
            
            elif rule.action == "scale_down":
                if (now - self.config.last_scale_down).total_seconds() < rule.cooldown_seconds:
                    continue
                
                # Perform scale down
                new_workers = max(
                    self.config.current_workers - rule.scale_amount,
                    self.config.min_workers
                )
                
                if new_workers < self.config.current_workers:
                    await self._perform_scaling(
                        "down",
                        self.config.current_workers - new_workers,
                        rule.name,
                        value,
                        rule.threshold
                    )
                    self.config.last_scale_down = now
                    break
    
    async def _perform_scaling(
        self, 
        direction: str, 
        amount: int, 
        rule_name: str,
        metric_value: float,
        threshold: float
    ):
        """Perform the scaling operation"""
        old_workers = self.config.current_workers
        
        if direction == "up":
            self.config.current_workers += amount
        else:
            self.config.current_workers -= amount
        
        scaling_event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "direction": direction,
            "amount": amount,
            "old_workers": old_workers,
            "new_workers": self.config.current_workers,
            "triggered_by": rule_name,
            "metric_value": metric_value,
            "threshold": threshold
        }
        
        self.scaling_history.append(scaling_event)
        
        # Keep last 100 scaling events
        if len(self.scaling_history) > 100:
            self.scaling_history.pop(0)
        
        # Log to database
        await db.scaling_events.insert_one({**scaling_event, "_id": None})
        
        logger.info(
            f"Scaled {direction}: {old_workers} -> {self.config.current_workers} workers "
            f"(rule: {rule_name}, {metric_value:.2f} vs threshold {threshold})"
        )
    
    async def manual_scale(self, target_workers: int, reason: str = "manual") -> Dict[str, Any]:
        """Manually set worker count"""
        old_workers = self.config.current_workers
        new_workers = max(
            self.config.min_workers,
            min(target_workers, self.config.max_workers)
        )
        
        if new_workers == old_workers:
            return {
                "success": True,
                "message": "No change needed",
                "workers": self.config.current_workers
            }
        
        direction = "up" if new_workers > old_workers else "down"
        amount = abs(new_workers - old_workers)
        
        await self._perform_scaling(direction, amount, reason, 0, 0)
        
        return {
            "success": True,
            "message": f"Scaled {direction} by {amount}",
            "old_workers": old_workers,
            "new_workers": self.config.current_workers
        }
    
    def get_status(self) -> Dict[str, Any]:
        """Get current auto-scaling status"""
        return {
            "current_workers": self.config.current_workers,
            "min_workers": self.config.min_workers,
            "max_workers": self.config.max_workers,
            "running": self._running,
            "metrics": {
                metric: self._get_metric_value(metric)
                for metric in self.metric_history.keys()
            },
            "last_scale_up": self.config.last_scale_up.isoformat(),
            "last_scale_down": self.config.last_scale_down.isoformat(),
            "recent_scaling_events": self.scaling_history[-10:],
            "active_rules": [
                {
                    "name": rule.name,
                    "metric": rule.metric,
                    "threshold": rule.threshold,
                    "action": rule.action
                }
                for rule in self.config.rules
                if rule.enabled
            ]
        }
    
    async def update_rules(self, rules: List[Dict]) -> Dict[str, Any]:
        """Update scaling rules"""
        new_rules = []
        for rule_dict in rules:
            try:
                rule = ScalingRule(**rule_dict)
                new_rules.append(rule)
            except Exception as e:
                logger.warning(f"Invalid rule: {e}")
        
        if new_rules:
            self.config.rules = new_rules
            return {"success": True, "rules_count": len(new_rules)}
        
        return {"success": False, "message": "No valid rules provided"}
    
    async def update_config(
        self,
        min_workers: Optional[int] = None,
        max_workers: Optional[int] = None
    ) -> Dict[str, Any]:
        """Update scaling configuration"""
        if min_workers is not None:
            self.config.min_workers = max(1, min_workers)
        
        if max_workers is not None:
            self.config.max_workers = max(self.config.min_workers, max_workers)
        
        # Adjust current workers if needed
        if self.config.current_workers < self.config.min_workers:
            self.config.current_workers = self.config.min_workers
        elif self.config.current_workers > self.config.max_workers:
            self.config.current_workers = self.config.max_workers
        
        return {
            "success": True,
            "min_workers": self.config.min_workers,
            "max_workers": self.config.max_workers,
            "current_workers": self.config.current_workers
        }


# ============================================
# GLOBAL INSTANCES
# ============================================

priority_lane_manager = PriorityLaneManager()
auto_scaling_engine = AutoScalingEngine()


# ============================================
# HELPER FUNCTIONS
# ============================================

async def initialize_priority_scaling():
    """Initialize the priority and scaling systems"""
    await auto_scaling_engine.start()
    logger.info("Priority lanes and auto-scaling initialized")

async def shutdown_priority_scaling():
    """Shutdown the priority and scaling systems"""
    await auto_scaling_engine.stop()
    logger.info("Priority lanes and auto-scaling shut down")


# ============================================
# EXPORTS
# ============================================

__all__ = [
    'UserTier',
    'TIER_CONFIG',
    'TIER_PRIORITIES',
    'PriorityLaneManager',
    'AutoScalingEngine',
    'priority_lane_manager',
    'auto_scaling_engine',
    'initialize_priority_scaling',
    'shutdown_priority_scaling',
    'ScalingRule',
    'AutoScalingConfig'
]
