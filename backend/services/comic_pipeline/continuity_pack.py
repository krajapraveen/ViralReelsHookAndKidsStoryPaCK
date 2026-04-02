"""
Continuity Pack — Curated reference selection for cross-panel consistency.
NOT a raw history dump. Selects the RIGHT prior evidence for each panel.

For generation: compact, curated references (anchor + latest high-confidence)
For validation: stronger reference set (all approved panels available)
"""
import logging
from typing import List, Dict, Optional, Tuple
import base64

logger = logging.getLogger("creatorstudio.comic_pipeline.continuity_pack")


class ContinuityPack:
    """
    Manages curated panel references for cross-panel continuity.
    Panel N does NOT need all prior panels — it needs the RIGHT prior evidence.
    """

    def __init__(self):
        # Approved panel data: {panel_index: {bytes, scores, pipeline_status}}
        self._approved: Dict[int, Dict] = {}

    def register_approved_panel(
        self,
        panel_index: int,
        image_bytes: bytes,
        validation_scores: Optional[Dict] = None,
        pipeline_status: str = "PASSED",
    ):
        """Register a panel that passed validation."""
        self._approved[panel_index] = {
            "bytes": image_bytes,
            "scores": validation_scores or {},
            "pipeline_status": pipeline_status,
            "face_confidence": (validation_scores or {}).get("face_consistency", 0),
            "style_confidence": (validation_scores or {}).get("style_consistency", 0),
        }
        logger.info(
            f"[CONTINUITY] Registered panel {panel_index + 1} "
            f"(face={self._approved[panel_index]['face_confidence']:.3f}, "
            f"style={self._approved[panel_index]['style_confidence']:.3f})"
        )

    def get_generation_context(self, current_panel_index: int) -> Optional[List[bytes]]:
        """
        Get curated references for GENERATION.
        Returns a small, focused list:
          1. Anchor panel (Panel 0) — always included if approved
          2. Latest high-confidence character panel — best face match
          3. Previous panel — for local transition continuity

        Panel 6 does NOT get all prior panels. It gets the RIGHT 2-3.
        """
        if not self._approved:
            return None

        refs: List[Tuple[int, bytes]] = []
        used_indices = set()

        # 1. Anchor panel (Panel 0)
        if 0 in self._approved and 0 != current_panel_index:
            refs.append((0, self._approved[0]["bytes"]))
            used_indices.add(0)

        # 2. Latest high-confidence character panel (best face_consistency)
        best_face_idx = None
        best_face_score = 0
        for idx, data in self._approved.items():
            if idx >= current_panel_index or idx in used_indices:
                continue
            if data["face_confidence"] > best_face_score:
                best_face_score = data["face_confidence"]
                best_face_idx = idx

        if best_face_idx is not None:
            refs.append((best_face_idx, self._approved[best_face_idx]["bytes"]))
            used_indices.add(best_face_idx)

        # 3. Previous panel for local transition (if not already included)
        prev_idx = current_panel_index - 1
        if prev_idx >= 0 and prev_idx in self._approved and prev_idx not in used_indices:
            refs.append((prev_idx, self._approved[prev_idx]["bytes"]))

        # Sort by panel index for coherent context
        refs.sort(key=lambda x: x[0])

        if not refs:
            return None

        return [r[1] for r in refs]

    def get_validation_context(self, current_panel_index: int) -> Optional[List[bytes]]:
        """
        Get references for VALIDATION.
        Validation can compare against a broader set than generation.
        Returns: all approved panels before current (up to 4 most relevant).
        """
        if not self._approved:
            return None

        # Get all approved before current, sorted by relevance
        candidates = [
            (idx, data) for idx, data in self._approved.items()
            if idx < current_panel_index
        ]

        if not candidates:
            return None

        # Prioritize: anchor, best face, best style, previous
        # Sort by a composite relevance score
        def relevance(item):
            idx, data = item
            score = 0
            if idx == 0:
                score += 100  # Anchor always most relevant
            score += data["face_confidence"] * 50
            score += data["style_confidence"] * 30
            if idx == current_panel_index - 1:
                score += 20  # Previous panel is locally relevant
            return -score  # Negative for ascending sort

        candidates.sort(key=relevance)

        # Return up to 4 most relevant
        return [data["bytes"] for _, data in candidates[:4]]

    @property
    def approved_count(self) -> int:
        return len(self._approved)

    @property
    def approved_indices(self) -> List[int]:
        return sorted(self._approved.keys())

    def get_summary(self) -> Dict:
        """Get a summary for logging/metrics."""
        return {
            "approved_count": self.approved_count,
            "approved_indices": self.approved_indices,
            "avg_face_confidence": round(
                sum(d["face_confidence"] for d in self._approved.values()) / len(self._approved), 3
            ) if self._approved else 0,
            "avg_style_confidence": round(
                sum(d["style_confidence"] for d in self._approved.values()) / len(self._approved), 3
            ) if self._approved else 0,
        }
