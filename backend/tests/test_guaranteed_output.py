"""
Tests for Guaranteed Output — Style-Aware Deterministic Filters.

Tests verify:
1. Each style produces output (no crashes)
2. Different styles produce different output (style distinctness)
3. Panels within a style are unique (per-panel variation)
4. Metadata is correctly attached
5. Fallback works when source image is missing/corrupt
6. Edge cases (unknown style, empty scenes, etc.)
"""
import io
import hashlib
import pytest
from PIL import Image, ImageDraw

from services.comic_pipeline.guaranteed_output import (
    generate_guaranteed_panels,
    STYLE_RENDERER_MAP,
    DEFAULT_RENDERER,
)

# ── Fixtures ──

def _make_test_image(w=200, h=200) -> bytes:
    img = Image.new("RGB", (w, h), (128, 100, 80))
    draw = ImageDraw.Draw(img)
    draw.ellipse([50, 50, 150, 150], fill=(200, 170, 140))
    draw.ellipse([70, 80, 90, 95], fill=(50, 50, 50))
    draw.ellipse([110, 80, 130, 95], fill=(50, 50, 50))
    draw.arc([80, 110, 120, 140], 0, 180, fill=(100, 50, 50), width=2)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


VALID_PNG = _make_test_image()
SCENES = [
    {"scene": "Hero stands ready", "dialogue": "Let's go!"},
    {"scene": "Action begins", "dialogue": "Watch out!"},
    {"scene": "Challenge faced", "dialogue": None},
    {"scene": "Victory", "dialogue": "We won!"},
]


# ══════════════════════════════════════════════════════════════════════════════
# BASIC FUNCTIONALITY
# ══════════════════════════════════════════════════════════════════════════════

class TestBasicOutput:
    def test_returns_correct_panel_count(self):
        for n in [1, 2, 4, 6]:
            panels = generate_guaranteed_panels(VALID_PNG, SCENES, n)
            assert len(panels) == n

    def test_panel_structure(self):
        panels = generate_guaranteed_panels(VALID_PNG, SCENES, 4)
        for p in panels:
            assert "panelNumber" in p
            assert "scene" in p
            assert "imageBytes" in p
            assert "status" in p
            assert "pipeline_status" in p
            assert "guaranteed_output" in p
            assert "filter_used" in p
            assert "style_applied" in p

    def test_panels_have_valid_image_bytes(self):
        panels = generate_guaranteed_panels(VALID_PNG, SCENES, 4)
        for p in panels:
            img = Image.open(io.BytesIO(p["imageBytes"]))
            assert img.width > 0
            assert img.height > 0

    def test_all_panels_marked_ready(self):
        panels = generate_guaranteed_panels(VALID_PNG, SCENES, 4)
        for p in panels:
            assert p["status"] == "READY"
            assert p["pipeline_status"] == "PASSED_GUARANTEED"
            assert p["guaranteed_output"] is True

    def test_panel_numbering(self):
        panels = generate_guaranteed_panels(VALID_PNG, SCENES, 4)
        for i, p in enumerate(panels):
            assert p["panelNumber"] == i + 1

    def test_scene_text_preserved(self):
        panels = generate_guaranteed_panels(VALID_PNG, SCENES, 2)
        assert panels[0]["scene"] == "Hero stands ready"
        assert panels[1]["scene"] == "Action begins"

    def test_dialogue_preserved(self):
        panels = generate_guaranteed_panels(VALID_PNG, SCENES, 4)
        assert panels[0]["dialogue"] == "Let's go!"
        assert panels[2]["dialogue"] is None


# ══════════════════════════════════════════════════════════════════════════════
# STYLE DISTINCTNESS — THE CORE FIX
# ══════════════════════════════════════════════════════════════════════════════

class TestStyleDistinctness:
    """Every style must produce visually distinct output."""

    STYLES_TO_TEST = [
        "bold_superhero", "cartoon_fun", "soft_manga",
        "noir_comic", "retro_action", "scifi_neon",
        "dreamy_pastel", "sketch_outline",
    ]

    def _get_panel_hashes(self, style):
        panels = generate_guaranteed_panels(VALID_PNG, SCENES, 4, style_name=style)
        return [hashlib.md5(p["imageBytes"]).hexdigest() for p in panels]

    def test_each_style_uses_its_own_renderer(self):
        """No two style families share the same renderer function."""
        renderers_seen = {}
        for style, renderer in STYLE_RENDERER_MAP.items():
            name = renderer.__name__
            if name not in renderers_seen:
                renderers_seen[name] = []
            renderers_seen[name].append(style)
        # We should have multiple distinct renderers
        assert len(renderers_seen) >= 6, f"Expected 6+ renderers, got {len(renderers_seen)}: {list(renderers_seen.keys())}"

    def test_bold_hero_vs_manga_different(self):
        h1 = self._get_panel_hashes("bold_superhero")
        h2 = self._get_panel_hashes("soft_manga")
        identical = sum(1 for a, b in zip(h1, h2) if a == b)
        assert identical == 0, f"bold_superhero and soft_manga share {identical}/4 panels"

    def test_cartoon_vs_noir_different(self):
        h1 = self._get_panel_hashes("cartoon_fun")
        h2 = self._get_panel_hashes("noir_comic")
        identical = sum(1 for a, b in zip(h1, h2) if a == b)
        assert identical == 0, f"cartoon_fun and noir_comic share {identical}/4 panels"

    def test_retro_vs_neon_different(self):
        h1 = self._get_panel_hashes("retro_action")
        h2 = self._get_panel_hashes("scifi_neon")
        identical = sum(1 for a, b in zip(h1, h2) if a == b)
        assert identical == 0, f"retro_action and scifi_neon share {identical}/4 panels"

    def test_pastel_vs_sketch_different(self):
        h1 = self._get_panel_hashes("dreamy_pastel")
        h2 = self._get_panel_hashes("sketch_outline")
        identical = sum(1 for a, b in zip(h1, h2) if a == b)
        assert identical == 0, f"dreamy_pastel and sketch_outline share {identical}/4 panels"

    def test_all_8_styles_are_pairwise_distinct(self):
        """No two styles produce the same panel 1 output."""
        panel1_hashes = {}
        for style in self.STYLES_TO_TEST:
            panels = generate_guaranteed_panels(VALID_PNG, SCENES, 1, style_name=style)
            h = hashlib.md5(panels[0]["imageBytes"]).hexdigest()
            panel1_hashes[style] = h
        unique = len(set(panel1_hashes.values()))
        assert unique == len(self.STYLES_TO_TEST), (
            f"Only {unique}/{len(self.STYLES_TO_TEST)} distinct panel 1 outputs"
        )

    def test_style_applied_metadata(self):
        for style in self.STYLES_TO_TEST:
            panels = generate_guaranteed_panels(VALID_PNG, SCENES, 1, style_name=style)
            assert panels[0]["style_applied"] == style

    def test_filter_used_is_renderer_name(self):
        panels = generate_guaranteed_panels(VALID_PNG, SCENES, 1, style_name="bold_superhero")
        assert panels[0]["filter_used"] == "_render_bold_hero"
        panels = generate_guaranteed_panels(VALID_PNG, SCENES, 1, style_name="noir_comic")
        assert panels[0]["filter_used"] == "_render_noir"


# ══════════════════════════════════════════════════════════════════════════════
# WITHIN-STYLE PANEL VARIATION
# ══════════════════════════════════════════════════════════════════════════════

class TestWithinStyleVariation:
    """Panels within the same style should not be identical."""

    def test_bold_hero_panels_vary(self):
        panels = generate_guaranteed_panels(VALID_PNG, SCENES, 4, style_name="bold_superhero")
        hashes = [hashlib.md5(p["imageBytes"]).hexdigest() for p in panels]
        unique = len(set(hashes))
        assert unique >= 3, f"Expected 3+ unique panels, got {unique}"

    def test_cartoon_panels_vary(self):
        panels = generate_guaranteed_panels(VALID_PNG, SCENES, 4, style_name="cartoon_fun")
        hashes = [hashlib.md5(p["imageBytes"]).hexdigest() for p in panels]
        unique = len(set(hashes))
        assert unique >= 3, f"Expected 3+ unique panels, got {unique}"

    def test_neon_panels_vary_by_color(self):
        panels = generate_guaranteed_panels(VALID_PNG, SCENES, 4, style_name="scifi_neon")
        hashes = [hashlib.md5(p["imageBytes"]).hexdigest() for p in panels]
        assert len(set(hashes)) == 4, "Neon panels should have 4 unique outputs (4 neon colors)"

    def test_retro_pop_panels_vary(self):
        panels = generate_guaranteed_panels(VALID_PNG, SCENES, 4, style_name="retro_action")
        hashes = [hashlib.md5(p["imageBytes"]).hexdigest() for p in panels]
        assert len(set(hashes)) == 4, "Retro panels should vary by color shift"


# ══════════════════════════════════════════════════════════════════════════════
# EDGE CASES & FALLBACKS
# ══════════════════════════════════════════════════════════════════════════════

class TestEdgeCases:
    def test_unknown_style_uses_default(self):
        panels = generate_guaranteed_panels(VALID_PNG, SCENES, 4, style_name="nonexistent_xyz")
        assert len(panels) == 4
        for p in panels:
            assert p["status"] == "READY"
            assert p["style_applied"] == "nonexistent_xyz"

    def test_none_source_gets_color_blocks(self):
        panels = generate_guaranteed_panels(None, SCENES, 4)
        assert len(panels) == 4
        for p in panels:
            assert p["filter_used"] == "color_block"
            assert p["status"] == "READY"

    def test_corrupt_source_gets_color_blocks(self):
        panels = generate_guaranteed_panels(b"not_an_image", SCENES, 4)
        assert len(panels) == 4
        for p in panels:
            assert p["filter_used"] == "color_block"

    def test_empty_scenes(self):
        panels = generate_guaranteed_panels(VALID_PNG, [], 3)
        assert len(panels) == 3
        for p in panels:
            assert p["status"] == "READY"

    def test_single_panel(self):
        panels = generate_guaranteed_panels(VALID_PNG, SCENES[:1], 1, style_name="noir_comic")
        assert len(panels) == 1
        assert panels[0]["filter_used"] == "_render_noir"

    def test_large_panel_count(self):
        panels = generate_guaranteed_panels(VALID_PNG, SCENES, 8, style_name="cartoon_fun")
        assert len(panels) == 8
        for p in panels:
            assert p["status"] == "READY"

    def test_tiny_source_image(self):
        tiny = Image.new("RGB", (10, 10), (255, 0, 0))
        buf = io.BytesIO()
        tiny.save(buf, format="PNG")
        panels = generate_guaranteed_panels(buf.getvalue(), SCENES, 2)
        assert len(panels) == 2
        for p in panels:
            assert p["status"] == "READY"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
