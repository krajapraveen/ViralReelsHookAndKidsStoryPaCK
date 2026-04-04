"""
Pricing Configuration — Single Source of Truth.

ALL pricing across the platform reads from this file.
No other file should define prices, credits, or plan details.
"""

# ═══════════════════════════════════════════════════════════════
# SUBSCRIPTION PLANS
# ═══════════════════════════════════════════════════════════════

SUBSCRIPTION_PLANS = {
    "weekly": {
        "id": "weekly",
        "name": "Weekly Plan",
        "period": "weekly",
        "duration_days": 7,
        "price_inr": 149,
        "credits": 40,
        "features": [
            "40 credits",
            "All core tools unlocked",
            "Standard support",
        ],
        "badge": None,
    },
    "monthly": {
        "id": "monthly",
        "name": "Monthly Plan",
        "period": "monthly",
        "duration_days": 30,
        "price_inr": 499,
        "credits": 200,
        "features": [
            "200 credits",
            "All core tools unlocked",
            "Priority generation",
            "HD downloads",
        ],
        "badge": "POPULAR",
    },
    "quarterly": {
        "id": "quarterly",
        "name": "Quarterly Plan",
        "period": "quarterly",
        "duration_days": 90,
        "price_inr": 1199,
        "credits": 750,
        "features": [
            "750 credits",
            "Faster generation queue",
            "Bonus styles / packs",
            "All core tools unlocked",
        ],
        "badge": "BEST VALUE",
    },
    "yearly": {
        "id": "yearly",
        "name": "Yearly Plan",
        "period": "yearly",
        "duration_days": 365,
        "price_inr": 3999,
        "credits": 3000,
        "features": [
            "3,000 credits",
            "Highest priority",
            "Early feature access",
            "Best value",
            "All core tools unlocked",
        ],
        "badge": "BEST DEAL",
    },
}

# ═══════════════════════════════════════════════════════════════
# TOP-UP PACKS
# ═══════════════════════════════════════════════════════════════

TOPUP_PACKS = {
    "topup_40": {
        "id": "topup_40",
        "name": "40 Credits",
        "credits": 40,
        "price_inr": 99,
        "popular": False,
    },
    "topup_120": {
        "id": "topup_120",
        "name": "120 Credits",
        "credits": 120,
        "price_inr": 249,
        "popular": False,
    },
    "topup_300": {
        "id": "topup_300",
        "name": "300 Credits",
        "credits": 300,
        "price_inr": 499,
        "popular": True,
    },
    "topup_700": {
        "id": "topup_700",
        "name": "700 Credits",
        "credits": 700,
        "price_inr": 999,
        "popular": False,
    },
}

# ═══════════════════════════════════════════════════════════════
# COMBINED PRODUCT CATALOG (used by payment gateway)
# ═══════════════════════════════════════════════════════════════

ALL_PRODUCTS = {}
for k, v in SUBSCRIPTION_PLANS.items():
    ALL_PRODUCTS[k] = {**v, "type": "subscription"}
for k, v in TOPUP_PACKS.items():
    ALL_PRODUCTS[k] = {**v, "type": "topup"}


def get_product(product_id: str) -> dict:
    """Look up any product (subscription or top-up) by ID."""
    return ALL_PRODUCTS.get(product_id)


def get_price(product_id: str) -> int:
    """Return INR price for a product. Raises KeyError if not found."""
    product = ALL_PRODUCTS.get(product_id)
    if not product:
        raise KeyError(f"Unknown product: {product_id}")
    return product["price_inr"]


# ═══════════════════════════════════════════════════════════════
# ORDER STATE MACHINE
# ═══════════════════════════════════════════════════════════════

ORDER_STATES = {
    "CREATED": "Order created, payment not yet initiated",
    "INITIATED": "User redirected to payment gateway",
    "PENDING": "Payment in progress at gateway",
    "SUCCESS": "Payment confirmed by gateway",
    "FAILED": "Payment failed",
    "CANCELLED": "Payment cancelled by user",
    "CREDIT_APPLIED": "Credits/subscription granted to user",
    "SUBSCRIPTION_ACTIVATED": "Subscription activated for user",
    "RECOVERY_REQUIRED": "Payment succeeded but entitlement failed — needs recovery",
    "EXPIRED": "Payment session expired",
}

VALID_TRANSITIONS = {
    "CREATED": ["INITIATED", "EXPIRED", "CANCELLED"],
    "INITIATED": ["PENDING", "SUCCESS", "FAILED", "CANCELLED", "EXPIRED"],
    "PENDING": ["SUCCESS", "FAILED", "CANCELLED", "EXPIRED"],
    "SUCCESS": ["CREDIT_APPLIED", "SUBSCRIPTION_ACTIVATED", "RECOVERY_REQUIRED"],
    "FAILED": [],
    "CANCELLED": [],
    "CREDIT_APPLIED": [],
    "SUBSCRIPTION_ACTIVATED": [],
    "RECOVERY_REQUIRED": ["CREDIT_APPLIED", "SUBSCRIPTION_ACTIVATED"],
    "EXPIRED": [],
}


def can_transition(current: str, target: str) -> bool:
    return target in VALID_TRANSITIONS.get(current, [])
