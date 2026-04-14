"""
Kill Switches — Instant system controls for production safety.
Admin-toggleable via API. Takes effect immediately on all endpoints.

KS1: generation_disabled — blocks all story-engine/create, reel/comic/bedtime/brand create
KS2: payments_disabled — blocks cashfree create-order and webhook processing
KS3: battle_disabled — blocks quick-shot and battle submissions
KS4: readonly_mode — blocks ALL write operations (drafts, generation, payments, battle)
"""
import os
import sys
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared import db, get_current_user

logger = logging.getLogger("kill_switches")
router = APIRouter(prefix="/admin/kill-switch", tags=["Kill Switches"])

# In-memory cache for fast access (refreshed from DB on each check)
_switch_cache = {}
_cache_ts = 0

SWITCHES = {
    "generation_disabled": {
        "name": "KS1: Disable Generation",
        "description": "Blocks all content creation endpoints (story-engine, reel, comic, bedtime, brand, gif)",
        "default": False,
    },
    "payments_disabled": {
        "name": "KS2: Disable Payments",
        "description": "Blocks checkout creation and webhook credit grants",
        "default": False,
    },
    "battle_disabled": {
        "name": "KS3: Disable Battle Entry",
        "description": "Blocks quick-shot and battle submission endpoints",
        "default": False,
    },
    "readonly_mode": {
        "name": "KS4: Read-Only Mode",
        "description": "Blocks ALL write operations — generation, payments, drafts, battle",
        "default": False,
    },
}


async def _load_switches():
    """Load switch states from DB into memory cache."""
    global _switch_cache, _cache_ts
    import time
    now = time.time()
    # Refresh cache every 5 seconds
    if now - _cache_ts < 5 and _switch_cache:
        return _switch_cache

    states = {}
    for key, meta in SWITCHES.items():
        doc = await db.kill_switches.find_one({"key": key}, {"_id": 0, "enabled": 1})
        states[key] = doc["enabled"] if doc else meta["default"]

    _switch_cache = states
    _cache_ts = now
    return states


async def is_killed(switch_key: str) -> bool:
    """Check if a specific kill switch is active. Fast path via cache."""
    states = await _load_switches()
    # readonly_mode overrides everything
    if states.get("readonly_mode", False):
        return True
    return states.get(switch_key, False)


async def check_generation_allowed():
    """Middleware check: is generation allowed?"""
    if await is_killed("generation_disabled"):
        raise HTTPException(
            status_code=503,
            detail="Content generation is temporarily disabled for system maintenance. Your credits are safe."
        )


async def check_payments_allowed():
    """Middleware check: are payments allowed?"""
    if await is_killed("payments_disabled"):
        raise HTTPException(
            status_code=503,
            detail="Payments are temporarily disabled for system maintenance. No charges will be made."
        )


async def check_battle_allowed():
    """Middleware check: is battle entry allowed?"""
    if await is_killed("battle_disabled"):
        raise HTTPException(
            status_code=503,
            detail="Battle submissions are temporarily paused. Please try again shortly."
        )


async def check_writes_allowed():
    """Middleware check: are writes allowed? (readonly mode)"""
    if await is_killed("readonly_mode"):
        raise HTTPException(
            status_code=503,
            detail="System is in read-only mode for maintenance. Your data is safe."
        )


class SwitchToggle(BaseModel):
    enabled: bool
    reason: str = ""


@router.get("")
async def get_switches(current_user: dict = Depends(get_current_user)):
    """Get current state of all kill switches."""
    if current_user.get("role", "").upper() != "ADMIN":
        raise HTTPException(status_code=403, detail="Admin only")

    states = await _load_switches()
    result = {}
    for key, meta in SWITCHES.items():
        doc = await db.kill_switches.find_one({"key": key}, {"_id": 0})
        result[key] = {
            "name": meta["name"],
            "description": meta["description"],
            "enabled": states.get(key, False),
            "toggled_at": doc.get("toggled_at") if doc else None,
            "toggled_by": doc.get("toggled_by") if doc else None,
            "reason": doc.get("reason", "") if doc else "",
        }
    return {"switches": result}


@router.post("/{switch_id}")
async def toggle_switch(switch_id: str, body: SwitchToggle, current_user: dict = Depends(get_current_user)):
    """Toggle a kill switch. Takes effect immediately."""
    if current_user.get("role", "").upper() != "ADMIN":
        raise HTTPException(status_code=403, detail="Admin only")

    if switch_id not in SWITCHES:
        raise HTTPException(status_code=404, detail=f"Unknown switch: {switch_id}")

    now = datetime.now(timezone.utc).isoformat()
    admin_id = current_user.get("id", current_user.get("email", "unknown"))

    await db.kill_switches.update_one(
        {"key": switch_id},
        {"$set": {
            "key": switch_id,
            "enabled": body.enabled,
            "toggled_at": now,
            "toggled_by": admin_id,
            "reason": body.reason,
        }},
        upsert=True,
    )

    # Invalidate cache immediately
    global _switch_cache, _cache_ts
    _cache_ts = 0
    _switch_cache = {}

    # Log to audit
    await db.system_alerts.insert_one({
        "invariant_key": f"kill_switch_{switch_id}",
        "name": f"Kill Switch: {SWITCHES[switch_id]['name']}",
        "severity": "critical",
        "status": "open" if body.enabled else "resolved",
        "count": 1,
        "sample_entity_ids": [switch_id],
        "first_seen_at": now,
        "last_seen_at": now,
        "trigger_count": 1,
        "resolved_at": None if body.enabled else now,
        "description": f"{'ACTIVATED' if body.enabled else 'DEACTIVATED'} by {admin_id}: {body.reason}",
    })

    action = "ACTIVATED" if body.enabled else "DEACTIVATED"
    logger.warning(f"Kill switch {switch_id} {action} by {admin_id}: {body.reason}")

    return {
        "success": True,
        "switch": switch_id,
        "enabled": body.enabled,
        "message": f"{SWITCHES[switch_id]['name']} {'ACTIVATED' if body.enabled else 'DEACTIVATED'}",
    }
