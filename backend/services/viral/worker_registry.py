"""
Worker Registration — registers all queue handlers at app startup.
Call register_all_workers() once during FastAPI lifespan.
"""
import logging
from services.viral.task_dispatch import register_handler, Q_ORCHESTRATOR, Q_TEXT_FAST, Q_IMAGE_FAST, Q_PACKAGING
from services.viral.workers.orchestrator_worker import handle_orchestrator
from services.viral.workers.text_fast_worker import handle_text_task
from services.viral.workers.image_fast_worker import handle_image_task
from services.viral.workers.packaging_worker import handle_packaging_task

logger = logging.getLogger("viral.workers")


def register_all_workers():
    register_handler(Q_ORCHESTRATOR, handle_orchestrator)
    register_handler(Q_TEXT_FAST, handle_text_task)
    register_handler(Q_IMAGE_FAST, handle_image_task)
    register_handler(Q_PACKAGING, handle_packaging_task)
    logger.info("[WORKERS] All viral workers registered")
