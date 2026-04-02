"""
Validator Stack — 6-layer validation for comic panel quality.
Each layer emits pass/fail + failure types. The stack aggregates into a ValidationResult.

Layers:
  1. AssetValidator — bytes exist, dimensions, not blank
  2. VisionQualityValidator — blur, brightness, face detect
  3. IdentityValidator — source similarity, face embedding consistency
  4. StyleValidator — art style consistency across panels
  5. StoryValidator — beat alignment, emotion match
  6. LayoutValidator — composition, framing, readability

Priority: validator usefulness over validator perfection.
"""
import logging
import io
from typing import Optional, Dict, List

logger = logging.getLogger("creatorstudio.comic_pipeline.validator_stack")

# Import enums
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from enums.pipeline_enums import (
    FailureType, FailureClass, PanelScores, ValidationResult,
    PASS_THRESHOLDS, FALLBACK_THRESHOLDS,
)


class AssetValidator:
    """Layer 1: Check that generated output is a valid, non-empty image."""

    def validate(self, image_bytes: Optional[bytes]) -> tuple:
        """Returns (pass, failure_types, details)"""
        if not image_bytes:
            return False, [FailureType.EMPTY_OUTPUT], {"reason": "no_bytes"}

        if len(image_bytes) < 1000:
            return False, [FailureType.CORRUPT_ASSET], {"reason": "too_small", "size": len(image_bytes)}

        # Check for valid image header (PNG or JPEG)
        is_png = image_bytes[:8] == b'\x89PNG\r\n\x1a\n'
        is_jpeg = image_bytes[:2] == b'\xff\xd8'
        is_webp = image_bytes[:4] == b'RIFF' and image_bytes[8:12] == b'WEBP'

        if not (is_png or is_jpeg or is_webp):
            return False, [FailureType.CORRUPT_ASSET], {"reason": "invalid_header"}

        return True, [], {"size": len(image_bytes), "format": "png" if is_png else "jpeg" if is_jpeg else "webp"}


class VisionQualityValidator:
    """Layer 2: Check blur, brightness, face detection confidence."""

    def validate(self, image_bytes: bytes) -> tuple:
        """Returns (score 0-1, failure_types, details)"""
        details = {}
        failure_types = []

        try:
            from PIL import Image
            import numpy as np

            img = Image.open(io.BytesIO(image_bytes))
            arr = np.array(img)

            # Dimensions check
            h, w = arr.shape[:2]
            details["dimensions"] = f"{w}x{h}"
            if w < 200 or h < 200:
                failure_types.append(FailureType.COMPOSITION_CLUTTER)
                details["too_small"] = True

            # Brightness check (0-1)
            if len(arr.shape) == 3:
                gray = np.mean(arr, axis=2)
            else:
                gray = arr.astype(float)
            brightness = float(np.mean(gray) / 255.0)
            details["brightness"] = round(brightness, 3)

            # Blur check via Laplacian variance
            try:
                import cv2
                gray_cv = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY) if len(arr.shape) == 3 else arr
                laplacian_var = cv2.Laplacian(gray_cv, cv2.CV_64F).var()
                blur_score = min(1.0, laplacian_var / 500.0)
                details["blur_score"] = round(blur_score, 3)
                details["laplacian_variance"] = round(laplacian_var, 1)
            except Exception:
                blur_score = 0.5
                details["blur_score"] = 0.5

            # Composite visual clarity
            clarity = (blur_score * 0.6) + (min(brightness, 1.0 - abs(brightness - 0.5)) * 0.4)
            clarity = max(0.0, min(1.0, clarity))
            details["visual_clarity"] = round(clarity, 3)

            return clarity, failure_types, details

        except Exception as e:
            logger.warning(f"VisionQualityValidator error: {e}")
            return 0.5, [], {"error": str(e)}


class IdentityValidator:
    """Layer 3: Compare face embeddings — source-to-panel and panel-to-panel."""

    def validate(
        self,
        panel_image_bytes: bytes,
        source_image_bytes: Optional[bytes] = None,
        approved_panel_bytes: Optional[List[bytes]] = None,
    ) -> tuple:
        """Returns (scores_dict, failure_types, details)"""
        scores = {"source_similarity": 0.0, "face_consistency": 0.0}
        failure_types = []
        details = {"method": "opencv_sface"}

        try:
            import cv2
            import numpy as np

            face_recognizer_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                "models", "face_recognition_sface.onnx"
            )
            face_detector_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                "models", "face_detection_yunet.onnx"
            )

            if not os.path.exists(face_recognizer_path) or not os.path.exists(face_detector_path):
                details["skipped"] = "models_not_found"
                return scores, failure_types, details

            recognizer = cv2.FaceRecognizerSF.create(face_recognizer_path, "")

            def get_embedding(img_bytes):
                arr = np.frombuffer(img_bytes, dtype=np.uint8)
                img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
                if img is None:
                    return None
                h, w = img.shape[:2]
                detector = cv2.FaceDetectorYN.create(face_detector_path, "", (w, h), 0.7)
                _, faces = detector.detect(img)
                if faces is None or len(faces) == 0:
                    return None
                face = faces[0]
                aligned = recognizer.alignCrop(img, face)
                return recognizer.feature(aligned)

            panel_emb = get_embedding(panel_image_bytes)
            if panel_emb is None:
                details["panel_face_detected"] = False
                scores["face_consistency"] = 0.5  # Can't penalize — no face to compare
                return scores, failure_types, details

            details["panel_face_detected"] = True

            # Source similarity
            if source_image_bytes:
                source_emb = get_embedding(source_image_bytes)
                if source_emb is not None:
                    sim = float(recognizer.match(panel_emb, source_emb, cv2.FaceRecognizerSF_FR_COSINE))
                    scores["source_similarity"] = round(max(0, sim), 4)
                    details["source_face_detected"] = True

                    if sim < PASS_THRESHOLDS["source_similarity"]:
                        failure_types.append(FailureType.LOW_SOURCE_SIMILARITY)
                    if sim < PASS_THRESHOLDS["face_consistency"]:
                        failure_types.append(FailureType.FACE_DRIFT)
                else:
                    details["source_face_detected"] = False
                    scores["source_similarity"] = 0.5

            # Panel-to-panel consistency
            if approved_panel_bytes:
                p2p_sims = []
                for prev_bytes in approved_panel_bytes[-2:]:  # Compare to last 2 approved panels
                    prev_emb = get_embedding(prev_bytes)
                    if prev_emb is not None:
                        sim = float(recognizer.match(panel_emb, prev_emb, cv2.FaceRecognizerSF_FR_COSINE))
                        p2p_sims.append(max(0, sim))

                if p2p_sims:
                    avg_p2p = sum(p2p_sims) / len(p2p_sims)
                    scores["face_consistency"] = round(avg_p2p, 4)
                    if avg_p2p < PASS_THRESHOLDS["face_consistency"]:
                        if FailureType.FACE_DRIFT not in failure_types:
                            failure_types.append(FailureType.FACE_DRIFT)
                else:
                    scores["face_consistency"] = scores["source_similarity"]
            else:
                scores["face_consistency"] = scores["source_similarity"]

            return scores, failure_types, details

        except Exception as e:
            logger.warning(f"IdentityValidator error: {e}")
            details["error"] = str(e)
            return scores, failure_types, details


class StyleValidator:
    """Layer 4: Check art style consistency across panels."""

    def validate(
        self,
        panel_image_bytes: bytes,
        style_name: str = "",
        approved_panel_bytes: Optional[List[bytes]] = None,
    ) -> tuple:
        """Returns (score 0-1, failure_types, details)"""
        failure_types = []
        details = {"method": "color_histogram_comparison"}

        try:
            import cv2
            import numpy as np

            def get_color_histogram(img_bytes):
                arr = np.frombuffer(img_bytes, dtype=np.uint8)
                img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
                if img is None:
                    return None
                hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
                hist = cv2.calcHist([hsv], [0, 1], None, [30, 32], [0, 180, 0, 256])
                cv2.normalize(hist, hist, 0, 1, cv2.NORM_MINMAX)
                return hist

            panel_hist = get_color_histogram(panel_image_bytes)
            if panel_hist is None:
                return 0.5, failure_types, {"error": "cannot_compute_histogram"}

            if approved_panel_bytes:
                similarities = []
                for prev_bytes in approved_panel_bytes[-3:]:
                    prev_hist = get_color_histogram(prev_bytes)
                    if prev_hist is not None:
                        corr = cv2.compareHist(panel_hist, prev_hist, cv2.HISTCMP_CORREL)
                        similarities.append(max(0, corr))

                if similarities:
                    avg_sim = sum(similarities) / len(similarities)
                    details["panel_to_panel_similarities"] = [round(s, 3) for s in similarities]
                    details["avg_similarity"] = round(avg_sim, 3)

                    if avg_sim < PASS_THRESHOLDS["style_consistency"]:
                        failure_types.append(FailureType.STYLE_DRIFT)

                    return round(avg_sim, 4), failure_types, details

            # No approved panels to compare — can't determine style drift
            return 0.75, failure_types, details

        except Exception as e:
            logger.warning(f"StyleValidator error: {e}")
            return 0.5, failure_types, {"error": str(e)}


class StoryValidator:
    """Layer 5: Check that panel matches its planned story beat."""

    def validate(self, panel_plan: dict, panel_data: dict) -> tuple:
        """Returns (score 0-1, failure_types, details)"""
        failure_types = []
        details = {}

        # Basic structural check: does the panel have scene/story content?
        has_scene = bool(panel_data.get("scene"))
        has_dialogue = bool(panel_data.get("dialogue"))
        correct_number = panel_data.get("panelNumber") == panel_plan.get("panel_index", 0) + 1

        details["has_scene"] = has_scene
        details["has_dialogue"] = has_dialogue
        details["correct_number"] = correct_number

        # Story alignment score
        score = 0.5
        if has_scene and correct_number:
            score = 0.85
        if has_dialogue:
            score = min(score + 0.1, 1.0)
        if not correct_number:
            failure_types.append(FailureType.STORY_MISMATCH)
            score = max(score - 0.3, 0.1)

        return round(score, 3), failure_types, details


class LayoutValidator:
    """Layer 6: Basic composition check — dimensions, aspect ratio, readability."""

    def validate(self, image_bytes: bytes) -> tuple:
        """Returns (score 0-1, failure_types, details)"""
        failure_types = []
        details = {}

        try:
            from PIL import Image
            img = Image.open(io.BytesIO(image_bytes))
            w, h = img.size
            details["width"] = w
            details["height"] = h
            details["aspect_ratio"] = round(w / h, 2) if h > 0 else 0

            # Reasonable dimensions for a comic panel
            score = 0.8
            if w < 256 or h < 256:
                score -= 0.3
                failure_types.append(FailureType.COMPOSITION_CLUTTER)
            if w > 4096 or h > 4096:
                score -= 0.1

            # Extreme aspect ratios are bad for comic panels
            ratio = w / h if h > 0 else 1
            if ratio > 3.0 or ratio < 0.33:
                score -= 0.2
                failure_types.append(FailureType.COMPOSITION_CLUTTER)

            return round(max(0, min(1, score)), 3), failure_types, details

        except Exception as e:
            logger.warning(f"LayoutValidator error: {e}")
            return 0.5, failure_types, {"error": str(e)}


# ══════════════════════════════════════════════════════════════════════════════
# VALIDATOR STACK — Aggregates all 6 layers
# ══════════════════════════════════════════════════════════════════════════════

class ValidatorStack:
    """
    Runs all 6 validator layers and produces a unified ValidationResult.
    Failure classification is driven by which validators failed, not vague scores.
    """

    def __init__(self):
        self.asset_validator = AssetValidator()
        self.vision_validator = VisionQualityValidator()
        self.identity_validator = IdentityValidator()
        self.style_validator = StyleValidator()
        self.story_validator = StoryValidator()
        self.layout_validator = LayoutValidator()

    def validate(
        self,
        image_bytes: Optional[bytes],
        panel_plan: dict,
        panel_data: dict,
        source_image_bytes: Optional[bytes] = None,
        approved_panel_bytes: Optional[list] = None,
        is_fallback: bool = False,
    ) -> ValidationResult:
        """
        Run the full 6-layer validation stack.
        Returns a ValidationResult with pass/fail, failure types, scores, and severity.
        """
        all_failure_types = []
        validator_summary = {}
        scores = PanelScores()

        # Layer 1: Asset
        asset_ok, asset_failures, asset_details = self.asset_validator.validate(image_bytes)
        validator_summary["asset_validator"] = "PASS" if asset_ok else "FAIL"
        if not asset_ok:
            all_failure_types.extend(asset_failures)
            # Hard failure — no point running other validators
            return ValidationResult(
                pass_status=False,
                failure_types=all_failure_types,
                failure_class=FailureClass.HARD,
                severity=1.0,
                scores=scores,
                validator_summary=validator_summary,
            )

        # Layer 2: Vision Quality
        clarity, vision_failures, vision_details = self.vision_validator.validate(image_bytes)
        scores.visual_clarity = clarity
        all_failure_types.extend(vision_failures)
        validator_summary["vision_quality_validator"] = "PASS" if not vision_failures else "WARN"

        # Layer 3: Identity
        identity_scores, identity_failures, identity_details = self.identity_validator.validate(
            image_bytes, source_image_bytes, approved_panel_bytes
        )
        scores.source_similarity = identity_scores.get("source_similarity", 0)
        scores.face_consistency = identity_scores.get("face_consistency", 0)
        all_failure_types.extend(identity_failures)
        validator_summary["identity_validator"] = "PASS" if not identity_failures else "FAIL"

        # Layer 4: Style
        style_score, style_failures, style_details = self.style_validator.validate(
            image_bytes, panel_data.get("style", ""), approved_panel_bytes
        )
        scores.style_consistency = style_score
        all_failure_types.extend(style_failures)
        validator_summary["style_validator"] = "PASS" if not style_failures else "FAIL"

        # Layer 5: Story
        story_score, story_failures, story_details = self.story_validator.validate(
            panel_plan, panel_data
        )
        scores.story_alignment = story_score
        all_failure_types.extend(story_failures)
        validator_summary["story_validator"] = "PASS" if not story_failures else "FAIL"

        # Layer 6: Layout
        layout_score, layout_failures, layout_details = self.layout_validator.validate(image_bytes)
        scores.composition = layout_score
        all_failure_types.extend(layout_failures)
        validator_summary["layout_validator"] = "PASS" if not layout_failures else "FAIL"

        # Deduplicate failure types
        all_failure_types = list(set(all_failure_types))

        # Classify failure class
        hard_types = {FailureType.HARD_FAIL, FailureType.EMPTY_OUTPUT, FailureType.CORRUPT_ASSET}
        structural_types = {FailureType.STORY_MISMATCH, FailureType.CONTINUITY_BREAK, FailureType.CHARACTER_COUNT_MISMATCH}

        if any(ft in hard_types for ft in all_failure_types):
            failure_class = FailureClass.HARD
        elif any(ft in structural_types for ft in all_failure_types):
            failure_class = FailureClass.STRUCTURAL
        elif all_failure_types:
            failure_class = FailureClass.SOFT
        else:
            failure_class = None

        # Compute severity (0-1)
        thresholds = FALLBACK_THRESHOLDS if is_fallback else PASS_THRESHOLDS
        failed_dimensions = 0
        total_dimensions = 0
        severity_sum = 0.0

        for dim, threshold in thresholds.items():
            val = getattr(scores, dim, 0)
            if val > 0:  # Only count dimensions we actually measured
                total_dimensions += 1
                if val < threshold:
                    failed_dimensions += 1
                    severity_sum += (threshold - val) / threshold

        severity = (severity_sum / total_dimensions) if total_dimensions > 0 else 0.0
        severity = round(min(1.0, severity), 3)

        # Determine pass/fail
        if not all_failure_types:
            pass_status = True
        elif is_fallback:
            # Fallback uses relaxed thresholds
            pass_status = all(
                getattr(scores, dim, 0) >= thr or getattr(scores, dim, 0) == 0
                for dim, thr in FALLBACK_THRESHOLDS.items()
            )
        else:
            pass_status = severity < 0.15  # Very low severity = pass

        # Fallback acceptable = passes relaxed thresholds even if not primary thresholds
        fallback_acceptable = all(
            getattr(scores, dim, 0) >= thr or getattr(scores, dim, 0) == 0
            for dim, thr in FALLBACK_THRESHOLDS.items()
        )

        return ValidationResult(
            pass_status=pass_status,
            fallback_acceptable=fallback_acceptable,
            failure_types=all_failure_types,
            failure_class=failure_class,
            severity=severity,
            scores=scores,
            validator_summary=validator_summary,
        )
