"""
Tier-Aware Degradation Matrix — Deterministic config object.

Maps (load_level, user_tier) → enforced limits.
No scattered if/else. One config. One truth.

Load levels: NORMAL, STRESSED, SEVERE, CRITICAL
Tiers: free, paid, premium (collapsed from plan names)
"""

TIER_MAP = {
    "free": "free",
    "starter": "paid", "weekly": "paid", "monthly": "paid",
    "creator": "paid", "quarterly": "paid", "yearly": "paid",
    "pro": "premium", "premium": "premium", "enterprise": "premium",
    "admin": "premium", "demo": "premium",
}

# Deterministic matrix: load_level → tier → limits
# max_pages=0 means BLOCKED
# retries: max retries per panel
DEGRADATION_MATRIX = {
    "normal": {
        "free":    {"max_pages": 20, "max_retries": 1, "blocked": False},
        "paid":    {"max_pages": 20, "max_retries": 2, "blocked": False},
        "premium": {"max_pages": 30, "max_retries": 3, "blocked": False},
    },
    "stressed": {
        "free":    {"max_pages": 10, "max_retries": 1, "blocked": False},
        "paid":    {"max_pages": 20, "max_retries": 2, "blocked": False},
        "premium": {"max_pages": 30, "max_retries": 3, "blocked": False},
    },
    "severe": {
        "free":    {"max_pages": 0,  "max_retries": 0, "blocked": True},
        "paid":    {"max_pages": 10, "max_retries": 1, "blocked": False},
        "premium": {"max_pages": 20, "max_retries": 2, "blocked": False},
    },
    "critical": {
        "free":    {"max_pages": 0,  "max_retries": 0, "blocked": True},
        "paid":    {"max_pages": 0,  "max_retries": 0, "blocked": True},
        "premium": {"max_pages": 10, "max_retries": 1, "blocked": False},
    },
}

# Partial success thresholds: what % of panels must succeed for PARTIAL_COMPLETE
PARTIAL_SUCCESS_THRESHOLDS = {
    "free": 0.70,
    "paid": 0.80,
    "premium": 0.90,
}


def resolve_tier(plan: str) -> str:
    return TIER_MAP.get(str(plan).lower().strip(), "free")


def get_degraded_limits(load_level: str, plan: str) -> dict:
    """Get deterministic limits for a given load level and plan."""
    tier = resolve_tier(plan)
    level = load_level if load_level in DEGRADATION_MATRIX else "normal"
    return DEGRADATION_MATRIX[level][tier]


def get_partial_threshold(plan: str) -> float:
    """Get the partial success threshold for a plan."""
    tier = resolve_tier(plan)
    return PARTIAL_SUCCESS_THRESHOLDS.get(tier, 0.70)
