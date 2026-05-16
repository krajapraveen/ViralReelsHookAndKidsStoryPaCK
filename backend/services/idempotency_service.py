"""
Idempotency Service - Prevents Duplicate Job Processing
Implements request deduplication with configurable TTL
"""
import hashlib
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class IdempotencyService:
    """Service for managing idempotency keys to prevent duplicate operations"""

    COLLECTION_NAME = "idempotency_keys"
    DEFAULT_TTL_HOURS = 24
    # P0 2026-05-19 — auto-expire PENDING records whose owning request died
    # before reaching update_result / mark_failed.
    #
    # Previous value (10 min) was the source of the production "Your comic
    # is already generating" lock-trap: when a worker crashed or a client
    # disconnect (asyncio.CancelledError) interrupted /generate AFTER the
    # PENDING row was inserted but BEFORE either update_result or
    # mark_failed ran, the user was soft-locked for 10 minutes with a dead
    # toast and no way to recover.
    #
    # 2 minutes is the new ceiling. The longest synchronous /generate path
    # on healthy infra is <5 s; the new BaseException guard on the route
    # also calls mark_failed on CancelledError so legitimate retries
    # rarely have to wait for this TTL anymore.
    STALE_PENDING_MINUTES = 2
    
    def __init__(self, db):
        self.db = db
    
    async def initialize(self):
        """Create indexes for idempotency collection"""
        try:
            # Unique index on idempotency key
            await self.db[self.COLLECTION_NAME].create_index("key", unique=True)
            # TTL index to auto-expire old keys
            await self.db[self.COLLECTION_NAME].create_index(
                "expiresAt", 
                expireAfterSeconds=0
            )
            logger.info("Idempotency indexes created")
        except Exception as e:
            logger.warning(f"Idempotency index creation: {e}")
    
    def generate_key(self, user_id: str, job_type: str, input_data: Dict[str, Any]) -> str:
        """
        Generate an idempotency key from request parameters.
        Same inputs will always generate the same key.
        """
        # Create a deterministic hash of the inputs
        key_data = {
            "user_id": user_id,
            "job_type": job_type,
            "input_data": json.dumps(input_data, sort_keys=True)
        }
        key_string = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(key_string.encode()).hexdigest()[:32]
    
    async def check_and_store(
        self, 
        idempotency_key: str, 
        ttl_hours: int = None
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Check if an idempotency key exists and store it if not.
        
        Returns:
            (is_duplicate, existing_result)
            - (False, None) if key is new - proceed with operation
            - (True, result_dict) if key exists - return cached result
        """
        if ttl_hours is None:
            ttl_hours = self.DEFAULT_TTL_HOURS

        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(hours=ttl_hours)

        # Try to find existing key
        existing = await self.db[self.COLLECTION_NAME].find_one(
            {"key": idempotency_key},
            {"_id": 0}
        )

        if existing:
            status = (existing.get("status") or "").upper()

            # ─── P0 2026-05 — Auto-recover stuck records ───────────────
            # FAILED keys must NOT block retries.
            # PENDING keys older than STALE_PENDING_MINUTES are assumed to
            # have crashed (request died between insert and update_result).
            is_failed = status == "FAILED"
            is_stale_pending = False
            if status == "PENDING":
                created_raw = existing.get("createdAt")
                try:
                    if isinstance(created_raw, str):
                        created_dt = datetime.fromisoformat(created_raw.replace("Z", "+00:00"))
                    else:
                        created_dt = created_raw
                    if created_dt and created_dt.tzinfo is None:
                        created_dt = created_dt.replace(tzinfo=timezone.utc)
                    if created_dt and (now - created_dt) > timedelta(minutes=self.STALE_PENDING_MINUTES):
                        is_stale_pending = True
                except Exception:
                    # Unparseable createdAt — treat as stale so we don't soft-lock the user.
                    is_stale_pending = True

            if is_failed or is_stale_pending:
                logger.info(
                    f"Idempotency key {idempotency_key[:8]}... recovered "
                    f"(status={status}, stale_pending={is_stale_pending}) — allowing retry"
                )
                await self.db[self.COLLECTION_NAME].delete_one({"key": idempotency_key})
                # Fall through to fresh-insert path below.
            else:
                logger.info(f"Idempotency key {idempotency_key[:8]}... already exists (status={status})")
                return (True, existing.get("result"))

        # Try to insert new key (will fail if another request beat us)
        try:
            await self.db[self.COLLECTION_NAME].insert_one({
                "key": idempotency_key,
                "status": "PENDING",
                "createdAt": now.isoformat(),
                "expiresAt": expires_at,
                "result": None
            })
            logger.info(f"Idempotency key {idempotency_key[:8]}... created")
            return (False, None)
        except Exception as e:
            # Duplicate key error - another request created it first
            if "duplicate key" in str(e).lower() or "E11000" in str(e):
                existing = await self.db[self.COLLECTION_NAME].find_one(
                    {"key": idempotency_key},
                    {"_id": 0}
                )
                return (True, existing.get("result") if existing else None)
            raise
    
    async def update_result(
        self, 
        idempotency_key: str, 
        result: Dict[str, Any],
        status: str = "COMPLETED"
    ):
        """Update the result for an idempotency key"""
        await self.db[self.COLLECTION_NAME].update_one(
            {"key": idempotency_key},
            {
                "$set": {
                    "result": result,
                    "status": status,
                    "completedAt": datetime.now(timezone.utc).isoformat()
                }
            }
        )
        logger.info(f"Idempotency key {idempotency_key[:8]}... result stored")
    
    async def mark_failed(self, idempotency_key: str, error: str):
        """Mark an idempotency key as failed (allows retry)"""
        await self.db[self.COLLECTION_NAME].update_one(
            {"key": idempotency_key},
            {
                "$set": {
                    "status": "FAILED",
                    "error": error,
                    "completedAt": datetime.now(timezone.utc).isoformat()
                }
            }
        )
    
    async def delete_key(self, idempotency_key: str):
        """Delete an idempotency key (allows immediate retry)"""
        await self.db[self.COLLECTION_NAME].delete_one({"key": idempotency_key})
    
    async def get_key_status(self, idempotency_key: str) -> Optional[Dict[str, Any]]:
        """Get the status of an idempotency key"""
        return await self.db[self.COLLECTION_NAME].find_one(
            {"key": idempotency_key},
            {"_id": 0}
        )
    
    async def cleanup_expired(self) -> int:
        """Manually cleanup expired keys (TTL index handles this automatically)"""
        result = await self.db[self.COLLECTION_NAME].delete_many({
            "expiresAt": {"$lt": datetime.now(timezone.utc)}
        })
        return result.deleted_count


# Decorator for idempotent endpoints
def idempotent_endpoint(ttl_hours: int = 24):
    """
    Decorator to make an endpoint idempotent.
    Requires 'Idempotency-Key' header or generates one from request body.
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # This is a template - actual implementation depends on FastAPI integration
            return await func(*args, **kwargs)
        return wrapper
    return decorator


# Singleton instance
_idempotency_service: Optional[IdempotencyService] = None


async def get_idempotency_service(db) -> IdempotencyService:
    """Get or create the idempotency service singleton"""
    global _idempotency_service
    if _idempotency_service is None:
        _idempotency_service = IdempotencyService(db)
        await _idempotency_service.initialize()
    return _idempotency_service
