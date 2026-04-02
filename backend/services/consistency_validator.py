"""
Character Consistency Validator (P1.5-C)

Uses OpenCV FaceDetectorYN (YuNet) + FaceRecognizerSF (SFace) to:
1. Extract face embedding from source photo (once per job)
2. Extract face embedding from each generated panel
3. Compare: source→panel (primary), panel1→panelN (secondary)
4. Return per-panel verdict: accept / retry / no_face

Tiered thresholds:
  - HIGH_PASS >= 0.45   → accept (cosine similarity, SFace range)
  - BORDERLINE 0.30-0.45 → accept but flag
  - LOW < 0.30          → auto-retry once

Note: SFace cosine similarity range is typically 0.0-1.0 but real-world
comic panels (stylized art vs real photo) produce lower scores than
photo-to-photo comparisons. Thresholds are tuned for cross-domain matching.
"""

import os
import io
import base64
import logging
import numpy as np
from PIL import Image, ExifTags
import cv2
from datetime import datetime, timezone

logger = logging.getLogger("creatorstudio.consistency")

# ── Model paths ──
MODELS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models")
YUNET_PATH = os.path.join(MODELS_DIR, "face_detection_yunet.onnx")
SFACE_PATH = os.path.join(MODELS_DIR, "face_recognition_sface.onnx")

# ── Thresholds (tuned for stylized art vs real photo) ──
HIGH_PASS = 0.45      # Strong match — accept
BORDERLINE = 0.30     # Acceptable but flag
LOW_THRESHOLD = 0.30  # Below this — retry

# Panel-to-panel thresholds (within same style, should be more consistent)
P2P_HIGH_PASS = 0.50
P2P_BORDERLINE = 0.35

# ── Singleton models (loaded once) ──
_detector = None
_recognizer = None


def _get_detector(width, height):
    """Get or create face detector for given dimensions"""
    global _detector
    if not os.path.exists(YUNET_PATH):
        return None
    _detector = cv2.FaceDetectorYN.create(YUNET_PATH, "", (width, height), 0.6, 0.3, 5000)
    _detector.setInputSize((width, height))
    return _detector


def _get_recognizer():
    """Get or create face recognizer (singleton)"""
    global _recognizer
    if _recognizer is not None:
        return _recognizer
    if not os.path.exists(SFACE_PATH):
        return None
    _recognizer = cv2.FaceRecognizerSF.create(SFACE_PATH, "")
    return _recognizer


def _fix_orientation(img):
    """Fix EXIF orientation"""
    try:
        exif = img.getexif()
        if not exif:
            return img
        for k, v in ExifTags.TAGS.items():
            if v == 'Orientation':
                orient = exif.get(k)
                if orient == 3:
                    img = img.rotate(180, expand=True)
                elif orient == 6:
                    img = img.rotate(270, expand=True)
                elif orient == 8:
                    img = img.rotate(90, expand=True)
                break
    except Exception:
        pass
    return img


def _pil_to_cv2(img):
    """PIL Image → OpenCV BGR array"""
    if img.mode != 'RGB':
        img = img.convert('RGB')
    return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)


def _load_image(image_data):
    """Load image from bytes or base64 string → OpenCV BGR array"""
    if isinstance(image_data, str):
        # Handle data URI
        if image_data.startswith('data:'):
            image_data = image_data.split(',', 1)[1]
        image_data = base64.b64decode(image_data)

    pil_img = Image.open(io.BytesIO(image_data))
    pil_img = _fix_orientation(pil_img)

    # Resize for consistent processing
    max_dim = 640
    w, h = pil_img.size
    if max(w, h) > max_dim:
        scale = max_dim / max(w, h)
        pil_img = pil_img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

    return _pil_to_cv2(pil_img)


def extract_face_embedding(image_data):
    """
    Extract face embedding from image.
    Returns: (embedding, face_detected, face_score) or (None, False, 0)
    """
    try:
        cv_img = _load_image(image_data)
        h, w = cv_img.shape[:2]

        detector = _get_detector(w, h)
        recognizer = _get_recognizer()

        if detector is None or recognizer is None:
            logger.warning("Face models not available")
            return None, False, 0

        _, faces = detector.detect(cv_img)
        if faces is None or len(faces) == 0:
            return None, False, 0

        # Use the face with highest confidence
        best_idx = int(np.argmax(faces[:, -1]))
        best_face = faces[best_idx]
        face_score = float(best_face[-1])

        # Align and extract embedding
        aligned = recognizer.alignCrop(cv_img, best_face)
        embedding = recognizer.feature(aligned)

        return embedding, True, face_score
    except Exception as e:
        logger.warning(f"Face embedding extraction failed: {e}")
        return None, False, 0


def compute_similarity(emb1, emb2):
    """Cosine similarity between two embeddings using instance method"""
    if emb1 is None or emb2 is None:
        return 0.0
    try:
        recognizer = _get_recognizer()
        if recognizer is None:
            return 0.0
        score = recognizer.match(emb1, emb2, cv2.FaceRecognizerSF_FR_COSINE)
        return float(score)
    except Exception:
        return 0.0


def validate_panel_consistency(
    source_embedding,
    panel_embedding,
    panel1_embedding,
    panel_number,
    source_face_detected=True,
    panel_face_detected=True,
):
    """
    Validate a single panel's character consistency.

    Returns dict:
      - verdict: "accept" | "borderline" | "retry" | "no_face" | "skip"
      - source_similarity: float
      - panel1_similarity: float (0 if panel 1)
      - face_detected: bool
    """
    # If source has no face, skip consistency check entirely
    if not source_face_detected or source_embedding is None:
        return {
            "verdict": "skip",
            "source_similarity": 0,
            "panel1_similarity": 0,
            "face_detected": panel_face_detected,
            "reason": "source_no_face",
        }

    # If panel has no detectable face — different failure mode, not identity drift
    if not panel_face_detected or panel_embedding is None:
        return {
            "verdict": "no_face",
            "source_similarity": 0,
            "panel1_similarity": 0,
            "face_detected": False,
            "reason": "panel_no_face",
        }

    # Primary: source → panel
    source_sim = compute_similarity(source_embedding, panel_embedding)

    # Secondary: panel1 → panelN (only for panels after panel 1)
    panel1_sim = 0.0
    if panel_number > 1 and panel1_embedding is not None:
        panel1_sim = compute_similarity(panel1_embedding, panel_embedding)

    # Tiered verdict
    if source_sim >= HIGH_PASS:
        verdict = "accept"
    elif source_sim >= BORDERLINE:
        verdict = "borderline"
    else:
        verdict = "retry"

    return {
        "verdict": verdict,
        "source_similarity": round(source_sim, 4),
        "panel1_similarity": round(panel1_sim, 4),
        "face_detected": True,
        "reason": None,
    }


async def run_consistency_validation(db, job_id, source_photo_bytes, panels, style, model_used="gemini"):
    """
    Run full consistency validation on all generated panels.

    Args:
        db: MongoDB database
        job_id: Job ID
        source_photo_bytes: Raw bytes of source photo
        panels: List of panel dicts with imageUrl and status
        style: Style ID used
        model_used: Model used for generation

    Returns:
        List of panel verdicts, with panels that need retry flagged.
    """
    results = []

    # 1. Extract source embedding (once)
    source_emb, source_face, source_score = extract_face_embedding(source_photo_bytes)

    if not source_face:
        # No face in source — skip all consistency checks
        logger.info(f"Job {job_id}: No face in source photo, skipping consistency validation")
        for i, panel in enumerate(panels):
            result = {
                "panel_number": i + 1,
                "verdict": "skip",
                "source_similarity": 0,
                "panel1_similarity": 0,
                "face_detected_in_panel": False,
                "reason": "source_no_face",
            }
            results.append(result)

        # Log to consistency_logs
        await _log_consistency(db, job_id, style, model_used, results, source_face)
        return results

    # 2. Extract embeddings from each panel
    panel_embeddings = []
    panel_face_flags = []

    for panel in panels:
        if panel.get("status") != "READY" or not panel.get("imageUrl"):
            panel_embeddings.append(None)
            panel_face_flags.append(False)
            continue

        # Get panel image bytes
        panel_bytes = await _get_panel_bytes(panel["imageUrl"])
        if panel_bytes is None:
            panel_embeddings.append(None)
            panel_face_flags.append(False)
            continue

        emb, detected, _ = extract_face_embedding(panel_bytes)
        panel_embeddings.append(emb)
        panel_face_flags.append(detected)

    # 3. Validate each panel
    panel1_emb = panel_embeddings[0] if panel_embeddings else None

    for i, panel in enumerate(panels):
        if panel.get("status") != "READY":
            results.append({
                "panel_number": i + 1,
                "verdict": "skip",
                "source_similarity": 0,
                "panel1_similarity": 0,
                "face_detected_in_panel": False,
                "reason": "panel_not_ready",
            })
            continue

        verdict = validate_panel_consistency(
            source_embedding=source_emb,
            panel_embedding=panel_embeddings[i],
            panel1_embedding=panel1_emb,
            panel_number=i + 1,
            source_face_detected=True,
            panel_face_detected=panel_face_flags[i],
        )

        results.append({
            "panel_number": i + 1,
            "verdict": verdict["verdict"],
            "source_similarity": verdict["source_similarity"],
            "panel1_similarity": verdict["panel1_similarity"],
            "face_detected_in_panel": verdict["face_detected"],
            "reason": verdict.get("reason"),
        })

    # 4. Log rich metadata
    await _log_consistency(db, job_id, style, model_used, results, source_face)

    return results


async def _get_panel_bytes(image_url):
    """Download panel image bytes from URL or decode base64"""
    try:
        if image_url.startswith('data:'):
            b64 = image_url.split(',', 1)[1]
            return base64.b64decode(b64)
        else:
            import httpx
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(image_url)
                if resp.status_code == 200:
                    return resp.content
    except Exception as e:
        logger.warning(f"Failed to fetch panel image: {e}")
    return None


async def _log_consistency(db, job_id, style, model_used, results, source_face_detected):
    """Log rich drift metadata to consistency_logs collection"""
    try:
        accepted = sum(1 for r in results if r["verdict"] == "accept")
        borderline = sum(1 for r in results if r["verdict"] == "borderline")
        retry_needed = sum(1 for r in results if r["verdict"] == "retry")
        no_face = sum(1 for r in results if r["verdict"] == "no_face")
        skipped = sum(1 for r in results if r["verdict"] == "skip")
        sims = [r["source_similarity"] for r in results if r["source_similarity"] > 0]

        log_doc = {
            "job_id": job_id,
            "style": style,
            "model_used": model_used,
            "source_face_detected": source_face_detected,
            "total_panels": len(results),
            "accepted": accepted,
            "borderline": borderline,
            "retry_needed": retry_needed,
            "no_face_panels": no_face,
            "skipped": skipped,
            "avg_source_similarity": round(sum(sims) / len(sims), 4) if sims else 0,
            "min_source_similarity": round(min(sims), 4) if sims else 0,
            "max_source_similarity": round(max(sims), 4) if sims else 0,
            "panel_details": results,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        await db.consistency_logs.insert_one(log_doc)
    except Exception as e:
        logger.warning(f"Failed to log consistency data: {e}")
