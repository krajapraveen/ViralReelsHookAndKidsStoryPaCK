"""
Activation Digest Scheduler — 08:00 IST = 02:30 UTC
"""
import asyncio
import logging
from datetime import datetime, timezone, timedelta

from services.activation_digest_service import get_activation_digest_service

logger = logging.getLogger(__name__)

IST_HOUR = 8
IST_MINUTE = 0
UTC_HOUR = 2
UTC_MINUTE = 30  # 08:00 IST minus 05:30 = 02:30 UTC

_task = None
_running = False


async def _loop(db):
    global _running
    logger.info("Activation digest scheduler started (08:00 IST = 02:30 UTC)")
    while _running:
        try:
            now = datetime.now(timezone.utc)
            next_run = now.replace(hour=UTC_HOUR, minute=UTC_MINUTE, second=0, microsecond=0)
            if now >= next_run:
                next_run += timedelta(days=1)
            wait_s = (next_run - now).total_seconds()
            ist_at = next_run + timedelta(hours=5, minutes=30)
            logger.info(
                "Activation digest: next run at %s IST (in %.1f h)",
                ist_at.strftime("%Y-%m-%d %H:%M"),
                wait_s / 3600.0,
            )
            await asyncio.sleep(wait_s)
            if not _running:
                break
            svc = get_activation_digest_service(db)
            res = await svc.run_once(also_email=True)
            logger.info(
                "Activation digest fired · confidence=%s · sample=%s · email=%s",
                res["digest"]["confidence"],
                res["digest"]["traffic_sample"],
                res["email"].get("success"),
            )
            await asyncio.sleep(60)  # avoid double-fire if loop drifts
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error("Activation digest scheduler error: %s", e)
            await asyncio.sleep(300)


def start_activation_digest_scheduler(db):
    global _task, _running
    if _running:
        return
    _running = True
    _task = asyncio.create_task(_loop(db))


def stop_activation_digest_scheduler():
    global _running, _task
    _running = False
    if _task:
        _task.cancel()
