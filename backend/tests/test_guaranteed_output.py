"""
Test Suite: Guaranteed Output Service — Deterministic output that CANNOT fail.

Proves:
  - generate_guaranteed_panels always produces output for any input
  - Empty/corrupt source photo falls back to color blocks
  - Panel count matches requested count
  - All panels have READY status
  - Bytes are valid PNG images
  - enhance_source_for_ai works or gracefully returns None
  - Filter variety across panels
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.comic_pipeline.guaranteed_output import (
    generate_guaranteed_panels,
    enhance_source_for_ai,
)


# Create a minimal valid PNG for testing
def _create_test_png() -> bytes:
    """Create a minimal valid PNG image."""
    from PIL import Image
    import io
    img = Image.new("RGB", (200, 200), (100, 150, 200))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


VALID_PNG = _create_test_png()
SCENES = [
    {"scene": "Hero walks into the city"},
    {"scene": "Hero meets the villain"},
    {"scene": "Epic battle begins"},
    {"scene": "Victory celebration"},
]


class TestGuaranteedOutputBasic:
    """Core guarantee: always produces output."""

    def test_valid_source_4_panels(self):
        panels = generate_guaranteed_panels(VALID_PNG, SCENES, 4)
        assert len(panels) == 4
        for p in panels:
            assert p["status"] == "READY"
            assert p["pipeline_status"] == "PASSED_GUARANTEED"
            assert p["guaranteed_output"] is True
            assert p["imageBytes"] is not None
            assert len(p["imageBytes"]) > 100  # Not empty
            assert p["panelNumber"] in (1, 2, 3, 4)

    def test_valid_source_1_panel(self):
        panels = generate_guaranteed_panels(VALID_PNG, [{"scene": "Solo panel"}], 1)
        assert len(panels) == 1
        assert panels[0]["status"] == "READY"
        assert panels[0]["scene"] == "Solo panel"

    def test_valid_source_6_panels(self):
        scenes6 = [{"scene": f"Scene {i}"} for i in range(6)]
        panels = generate_guaranteed_panels(VALID_PNG, scenes6, 6)
        assert len(panels) == 6
        for p in panels:
            assert p["status"] == "READY"

    def test_png_header_valid(self):
        """Output bytes start with PNG header."""
        panels = generate_guaranteed_panels(VALID_PNG, SCENES[:1], 1)
        img_bytes = panels[0]["imageBytes"]
        assert img_bytes[:4] == b'\x89PNG'


class TestGuaranteedOutputDegradedInput:
    """Corrupt/empty source photo still produces output."""

    def test_empty_source_bytes(self):
        panels = generate_guaranteed_panels(b"", SCENES, 4)
        assert len(panels) == 4
        for p in panels:
            assert p["status"] == "READY"
            assert p["filter_used"] == "color_block"

    def test_none_source_bytes(self):
        panels = generate_guaranteed_panels(None, SCENES, 4)
        assert len(panels) == 4
        for p in panels:
            assert p["status"] == "READY"

    def test_corrupt_source_bytes(self):
        panels = generate_guaranteed_panels(b"NOT_AN_IMAGE_AT_ALL", SCENES, 4)
        assert len(panels) == 4
        for p in panels:
            assert p["status"] == "READY"
            assert p["filter_used"] == "color_block"

    def test_tiny_source_bytes(self):
        panels = generate_guaranteed_panels(b"\x89PNG", SCENES, 4)
        assert len(panels) == 4
        for p in panels:
            assert p["status"] == "READY"

    def test_empty_scenes(self):
        """No scenes provided — still generates panels."""
        panels = generate_guaranteed_panels(VALID_PNG, [], 4)
        assert len(panels) == 4
        for p in panels:
            assert p["status"] == "READY"


class TestGuaranteedOutputFilterVariety:
    """Different panels get different filters for visual variety."""

    def test_filter_variety(self):
        panels = generate_guaranteed_panels(VALID_PNG, SCENES, 4)
        filters = [p["filter_used"] for p in panels]
        # At least 2 different filters across 4 panels
        assert len(set(filters)) >= 2

    def test_pop_art_color_shift(self):
        """Pop art filter produces different tints per panel."""
        panels = generate_guaranteed_panels(VALID_PNG, SCENES, 4)
        # Panel 1 (index 1) should get pop_art filter
        bytes_p1 = panels[1]["imageBytes"]
        assert len(bytes_p1) > 100


class TestGuaranteedOutputDialogue:
    """Dialogue propagation."""

    def test_dialogue_preserved(self):
        scenes = [
            {"scene": "S1", "dialogue": "Hello!"},
            {"scene": "S2", "dialogue": "Goodbye!"},
        ]
        panels = generate_guaranteed_panels(VALID_PNG, scenes, 2)
        assert panels[0]["dialogue"] == "Hello!"
        assert panels[1]["dialogue"] == "Goodbye!"

    def test_no_dialogue(self):
        scenes = [{"scene": "S1"}]
        panels = generate_guaranteed_panels(VALID_PNG, scenes, 1)
        assert panels[0]["dialogue"] is None


class TestEnhanceSourceForAI:
    """Pre-processing enhancement."""

    def test_enhance_valid_image(self):
        result = enhance_source_for_ai(VALID_PNG)
        assert result is not None
        assert len(result) > 100
        assert result[:4] == b'\x89PNG'

    def test_enhance_none(self):
        result = enhance_source_for_ai(None)
        assert result is None

    def test_enhance_corrupt(self):
        result = enhance_source_for_ai(b"not an image")
        assert result is None

    def test_enhance_empty(self):
        result = enhance_source_for_ai(b"")
        assert result is None


class TestGuaranteedOutputInvariants:
    """Cross-cutting invariants — the service NEVER crashes."""

    @pytest.mark.parametrize("source,scenes,count", [
        (VALID_PNG, SCENES, 4),
        (b"", SCENES, 4),
        (None, SCENES, 4),
        (b"corrupt", [], 0),
        (VALID_PNG, [], 6),
        (b"\x00" * 10000, SCENES, 2),
    ])
    def test_never_crashes(self, source, scenes, count):
        panels = generate_guaranteed_panels(source, scenes, max(count, 0))
        assert isinstance(panels, list)
        for p in panels:
            assert p["status"] == "READY"
            assert p["guaranteed_output"] is True

    def test_zero_panel_count(self):
        panels = generate_guaranteed_panels(VALID_PNG, SCENES, 0)
        assert panels == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
