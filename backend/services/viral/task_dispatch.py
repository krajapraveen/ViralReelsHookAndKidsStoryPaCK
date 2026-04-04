"""
Queue Abstraction Layer
Preview: asyncio background tasks
Production: swap to Redis/Celery with minimal changes
"""
import asyncio
import logging
import uuid

logger = logging.getLogger("viral.dispatch")

_QUEUE_HANDLERS = {}


def register_handler(queue_name: str, handler):
    _QUEUE_HANDLERS[queue_name] = handler
    logger.info(f"[DISPATCH] Registered handler for queue: {queue_name}")


async def dispatch_task(queue_name: str, payload: dict) -> str:
    task_id = payload.get("task_id", str(uuid.uuid4()))
    handler = _QUEUE_HANDLERS.get(queue_name)
    if not handler:
        logger.error(f"[DISPATCH] No handler for queue: {queue_name}")
        return task_id

    logger.info(f"[DISPATCH] queue={queue_name} task_id={task_id}")
    asyncio.create_task(_safe_run(handler, payload, queue_name, task_id))
    return task_id


async def _safe_run(handler, payload, queue_name, task_id):
    try:
        await handler(payload)
    except Exception as e:
        logger.error(f"[DISPATCH] Task failed: queue={queue_name} task_id={task_id} error={e}", exc_info=True)


# Queue name constants
Q_ORCHESTRATOR = "q_orchestrator_start"
Q_TEXT_FAST = "q_text_fast"
Q_IMAGE_FAST = "q_image_fast"
Q_PACKAGING = "q_packaging"
