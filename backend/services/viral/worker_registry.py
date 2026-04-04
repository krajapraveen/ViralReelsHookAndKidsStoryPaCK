"""
Worker Registration — registers all queue handlers at app startup.
"""
import logging
from services.viral.task_dispatch import (
    register_handler,
    Q_ORCHESTRATOR, Q_TEXT_FAST, Q_IMAGE_FAST, Q_AUDIO_FAST, Q_VIDEO_FAST, Q_PACKAGING, Q_REPAIR,
)
from services.viral.workers.orchestrator_worker import handle_orchestrator
from services.viral.workers.text_fast_worker import handle_text_task
from services.viral.workers.image_fast_worker import handle_image_task
from services.viral.workers.audio_fast_worker import handle_audio_task
from services.viral.workers.video_fast_worker import handle_video_task
from services.viral.workers.packaging_worker import handle_packaging_task
from services.viral.workers.repair_worker import handle_repair_task

logger = logging.getLogger("viral.workers")


def register_all_workers():
    register_handler(Q_ORCHESTRATOR, handle_orchestrator)
    register_handler(Q_TEXT_FAST, handle_text_task)
    register_handler(Q_IMAGE_FAST, handle_image_task)
    register_handler(Q_AUDIO_FAST, handle_audio_task)
    register_handler(Q_VIDEO_FAST, handle_video_task)
    register_handler(Q_PACKAGING, handle_packaging_task)
    register_handler(Q_REPAIR, handle_repair_task)
    logger.info("[WORKERS] All viral workers registered (7 queues)")
