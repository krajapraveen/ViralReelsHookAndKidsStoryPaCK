"""
Photo Quality Scoring Service
Uses OpenCV DNN (FaceDetectorYN / YuNet) + Pillow for fast pre-generation checks.

Returns a compact quality JSON:
  - face_detected: bool
  - face_count: int
  - face_score: float (0-1, detection confidence)
  - face_size_pct: float (face area as % of image)
  - blur_score: float (higher = sharper)
  - brightness: float (0-255 mean)
  - overall: "good" | "acceptable" | "poor"
  - warnings: list[str]
  - can_proceed: bool

Design:
  - Pillow: load, EXIF fix, convert
  - OpenCV: FaceDetectorYN for face detection, Laplacian for blur, histogram for brightness
  - Target: < 1 second total
"""

import io
import os
import hashlib
import numpy as np
from PIL import Image, ExifTags
import cv2

# ── Model path ──
YUNET_MODEL_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models", "face_detection_yunet.onnx")

# ── Thresholds ──
MIN_FACE_SIZE_PCT = 2.0        # face must be at least 2% of image area
BLUR_THRESHOLD_BAD = 30.0      # below this = very blurry
BLUR_THRESHOLD_WARN = 80.0     # below this = somewhat blurry
BRIGHTNESS_LOW = 40.0          # too dark
BRIGHTNESS_HIGH = 230.0        # too bright
FACE_SCORE_THRESHOLD = 0.7     # YuNet confidence threshold


def _fix_exif_orientation(img: Image.Image) -> Image.Image:
    """Fix image orientation based on EXIF data (common with phone photos)"""
    try:
        exif = img.getexif()
        if not exif:
            return img
        orientation_key = None
        for k, v in ExifTags.TAGS.items():
            if v == 'Orientation':
                orientation_key = k
                break
        if orientation_key and orientation_key in exif:
            orientation = exif[orientation_key]
            if orientation == 3:
                img = img.rotate(180, expand=True)
            elif orientation == 6:
                img = img.rotate(270, expand=True)
            elif orientation == 8:
                img = img.rotate(90, expand=True)
    except Exception:
        pass
    return img


def _pil_to_cv2(img: Image.Image) -> np.ndarray:
    """Convert PIL Image to OpenCV BGR numpy array"""
    if img.mode == 'RGBA':
        img = img.convert('RGB')
    elif img.mode != 'RGB':
        img = img.convert('RGB')
    return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)


def _compute_blur(gray: np.ndarray) -> float:
    """Laplacian variance — higher = sharper"""
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def _compute_brightness(gray: np.ndarray) -> float:
    """Mean brightness from grayscale image"""
    return float(np.mean(gray))


def _detect_faces(cv_img: np.ndarray) -> list:
    """Use OpenCV FaceDetectorYN (YuNet) for face detection"""
    if not os.path.exists(YUNET_MODEL_PATH):
        return []

    h, w = cv_img.shape[:2]
    detector = cv2.FaceDetectorYN.create(
        YUNET_MODEL_PATH,
        "",
        (w, h),
        FACE_SCORE_THRESHOLD,
        0.3,   # NMS threshold
        5000   # top_k
    )

    _, faces = detector.detect(cv_img)
    if faces is None:
        return []

    results = []
    for face in faces:
        x, y, fw, fh = int(face[0]), int(face[1]), int(face[2]), int(face[3])
        score = float(face[14]) if len(face) > 14 else float(face[-1])
        area_pct = (fw * fh) / (w * h) * 100
        results.append({
            "x": x, "y": y, "w": fw, "h": fh,
            "score": round(score, 3),
            "area_pct": round(area_pct, 1)
        })
    return results


def compute_image_hash(image_bytes: bytes) -> str:
    """SHA-256 hash of image bytes for caching"""
    return hashlib.sha256(image_bytes).hexdigest()[:32]


def score_photo_quality(image_bytes: bytes) -> dict:
    """
    Score photo quality for comic generation.
    Returns a compact quality assessment dict.
    """
    warnings = []

    # 1. Load with Pillow + EXIF fix
    try:
        pil_img = Image.open(io.BytesIO(image_bytes))
        pil_img = _fix_exif_orientation(pil_img)
    except Exception as e:
        return {
            "face_detected": False,
            "face_count": 0,
            "face_score": 0,
            "face_size_pct": 0,
            "blur_score": 0,
            "brightness": 0,
            "overall": "poor",
            "warnings": [f"Could not read image: {str(e)}"],
            "can_proceed": False,
        }

    # Resize for fast processing (max 640px on longest side)
    max_dim = 640
    w, h = pil_img.size
    if max(w, h) > max_dim:
        scale = max_dim / max(w, h)
        pil_img = pil_img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

    # 2. Convert to OpenCV
    cv_img = _pil_to_cv2(pil_img)
    gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)

    # 3. Face detection
    faces = _detect_faces(cv_img)
    face_count = len(faces)
    face_detected = face_count > 0
    best_face_score = max((f["score"] for f in faces), default=0)
    best_face_area = max((f["area_pct"] for f in faces), default=0)

    # 4. Blur detection
    blur_score = _compute_blur(gray)

    # 5. Brightness
    brightness = _compute_brightness(gray)

    # ── Build warnings ──
    if not face_detected:
        warnings.append("No face detected. Please upload a photo with a visible face.")
    elif face_count > 1:
        warnings.append(f"Multiple faces detected ({face_count}). For best results, use a single-person photo.")

    if face_detected and best_face_area < MIN_FACE_SIZE_PCT:
        warnings.append("Face is very small in the frame. Try a closer photo for better results.")

    if blur_score < BLUR_THRESHOLD_BAD:
        warnings.append("Photo appears very blurry. A sharper photo will produce better comic art.")
    elif blur_score < BLUR_THRESHOLD_WARN:
        warnings.append("Photo is slightly blurry. Results may be affected.")

    if brightness < BRIGHTNESS_LOW:
        warnings.append("Photo is very dark. Better lighting will improve results.")
    elif brightness > BRIGHTNESS_HIGH:
        warnings.append("Photo is very bright/overexposed. Adjust lighting for better results.")

    # ── Overall score ──
    if not face_detected:
        overall = "poor"
        can_proceed = False
    elif blur_score < BLUR_THRESHOLD_BAD or brightness < BRIGHTNESS_LOW:
        overall = "poor"
        can_proceed = True  # Let them try, but warn
    elif face_count > 1 or blur_score < BLUR_THRESHOLD_WARN or best_face_area < MIN_FACE_SIZE_PCT:
        overall = "acceptable"
        can_proceed = True
    else:
        overall = "good"
        can_proceed = True

    return {
        "face_detected": face_detected,
        "face_count": face_count,
        "face_score": round(best_face_score, 2),
        "face_size_pct": round(best_face_area, 1),
        "blur_score": round(blur_score, 1),
        "brightness": round(brightness, 1),
        "overall": overall,
        "warnings": warnings,
        "can_proceed": can_proceed,
        "checks": {
            "face": "pass" if face_detected and face_count == 1 else ("warn" if face_count > 1 else "fail"),
            "clarity": "pass" if blur_score >= BLUR_THRESHOLD_WARN else ("warn" if blur_score >= BLUR_THRESHOLD_BAD else "fail"),
            "lighting": "pass" if BRIGHTNESS_LOW <= brightness <= BRIGHTNESS_HIGH else "warn",
            "framing": "pass" if best_face_area >= MIN_FACE_SIZE_PCT else "warn",
        }
    }
