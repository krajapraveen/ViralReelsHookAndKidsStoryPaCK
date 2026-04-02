"""
Character Lock Service — Lightweight character identity management.
Phase 1: source reference traits + approved panel context + simple face/visual lock.
"""
import logging
from typing import Optional, Dict, List

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from enums.pipeline_enums import CharacterLock

logger = logging.getLogger("creatorstudio.comic_pipeline.character_lock")


class CharacterLockService:
    """
    Manages character identity context across panels.
    Phase 1: lightweight — stores traits and approved panel references.
    """

    def __init__(self, db):
        self.db = db

    def initialize_from_source(
        self,
        source_image_bytes: bytes,
        style_name: str = "",
    ) -> CharacterLock:
        """
        Create initial character lock from the source photo.
        Phase 1: basic face detection + visual trait extraction.
        """
        lock = CharacterLock()

        try:
            import cv2
            import numpy as np

            arr = np.frombuffer(source_image_bytes, dtype=np.uint8)
            img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            if img is None:
                return lock

            h, w = img.shape[:2]

            # Face detection
            face_detector_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                "models", "face_detection_yunet.onnx"
            )
            if os.path.exists(face_detector_path):
                detector = cv2.FaceDetectorYN.create(face_detector_path, "", (w, h), 0.7)
                _, faces = detector.detect(img)
                lock.source_face_detected = faces is not None and len(faces) > 0

            # Extract basic visual traits from the image
            hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
            avg_brightness = float(np.mean(hsv[:, :, 2]) / 255.0)
            avg_saturation = float(np.mean(hsv[:, :, 1]) / 255.0)

            lock.visual_traits = {
                "avg_brightness": f"{avg_brightness:.2f}",
                "avg_saturation": f"{avg_saturation:.2f}",
                "image_dimensions": f"{w}x{h}",
            }

            lock.style_traits = {
                "requested_style": style_name,
            }

            logger.info(f"[CHAR_LOCK] Initialized: face={lock.source_face_detected}, dims={w}x{h}")

        except Exception as e:
            logger.warning(f"[CHAR_LOCK] Init error: {e}")

        return lock

    def update_with_approved_panel(self, lock: CharacterLock, panel_index: int) -> CharacterLock:
        """Record that a panel was approved, extending the continuity chain."""
        if panel_index not in lock.approved_panels:
            lock.approved_panels.append(panel_index)
        return lock

    def get_continuity_context(self, lock: CharacterLock) -> Dict:
        """Get context dict for prompt composition."""
        return {
            "source_face_detected": lock.source_face_detected,
            "visual_traits": lock.visual_traits,
            "style_traits": lock.style_traits,
            "approved_panel_count": len(lock.approved_panels),
            "last_approved_panel": lock.approved_panels[-1] if lock.approved_panels else None,
        }
