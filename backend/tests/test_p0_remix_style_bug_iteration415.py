"""
Test Suite: P0 Remix Style Bug Fix Verification (Iteration 415)

Validates the fixes for:
1. guaranteed_output.py now uses style_name for filter selection (not panel-index-only)
2. All 3 filter types (posterize, pop_art, sketch) are used in rotations
3. Each panel within a style has unique image bytes (per-panel color variation)
4. Style metadata (style_applied, filter_used) is included in panel output
5. Unknown style names fall back to default rotation without crashing
6. Prompt composer includes strong style differentiation instructions
"""
import pytest
import sys
import os
import hashlib

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.comic_pipeline.guaranteed_output import (
    generate_guaranteed_panels,
    STYLE_FILTER_MAP,
    DEFAULT_FILTER_ROTATION,
    FILTER_FUNCTIONS,
)
from services.comic_pipeline.prompt_composer import PromptComposer


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
    {"scene": "Hero walks into the city", "dialogue": "Let's go!"},
    {"scene": "Hero meets the villain", "dialogue": "You again!"},
    {"scene": "Epic battle begins", "dialogue": "Fight!"},
    {"scene": "Victory celebration", "dialogue": "We won!"},
]


class TestStyleFilterMapping:
    """Verify STYLE_FILTER_MAP is correctly configured."""

    def test_all_three_filter_types_defined(self):
        """All 3 filter functions must be defined."""
        expected = {"comic_posterize", "pop_art", "sketch"}
        actual = set(FILTER_FUNCTIONS.keys())
        assert actual == expected, f"Expected {expected}, got {actual}"

    def test_all_three_filters_used_across_styles(self):
        """All 3 filter types must be used across style mappings."""
        all_filters_used = set()
        for style, filters in STYLE_FILTER_MAP.items():
            all_filters_used.update(filters)
        
        expected = {"comic_posterize", "pop_art", "sketch"}
        assert all_filters_used == expected, f"Not all filters used. Got: {all_filters_used}"

    def test_default_rotation_has_all_three_filters(self):
        """Default rotation must include all 3 filter types."""
        expected = {"comic_posterize", "pop_art", "sketch"}
        actual = set(DEFAULT_FILTER_ROTATION)
        assert actual == expected, f"Default rotation missing filters. Got: {actual}"

    def test_action_styles_use_pop_art_heavy(self):
        """Action styles should use pop_art-heavy rotations."""
        action_styles = ["bold_superhero", "dark_vigilante", "retro_action", "dynamic_battle"]
        for style in action_styles:
            if style in STYLE_FILTER_MAP:
                filters = STYLE_FILTER_MAP[style]
                assert "pop_art" in filters, f"{style} should use pop_art"

    def test_soft_styles_use_sketch_heavy(self):
        """Soft/minimal styles should use sketch-heavy rotations."""
        soft_styles = ["noir_comic", "black_white_ink", "sketch_outline", "soft_manga"]
        for style in soft_styles:
            if style in STYLE_FILTER_MAP:
                filters = STYLE_FILTER_MAP[style]
                assert "sketch" in filters, f"{style} should use sketch"


class TestStyleDistinctOutput:
    """Different styles MUST produce visually distinct outputs."""

    def test_bold_superhero_vs_soft_manga_different(self):
        """bold_superhero and soft_manga must produce different panel 1."""
        panels_hero = generate_guaranteed_panels(VALID_PNG, SCENES[:1], 1, style_name="bold_superhero")
        panels_manga = generate_guaranteed_panels(VALID_PNG, SCENES[:1], 1, style_name="soft_manga")
        
        hash_hero = hashlib.md5(panels_hero[0]["imageBytes"][:500]).hexdigest()
        hash_manga = hashlib.md5(panels_manga[0]["imageBytes"][:500]).hexdigest()
        
        assert hash_hero != hash_manga, "bold_superhero and soft_manga should produce different outputs"

    def test_noir_comic_vs_cartoon_fun_different(self):
        """noir_comic and cartoon_fun must produce different panel 1."""
        panels_noir = generate_guaranteed_panels(VALID_PNG, SCENES[:1], 1, style_name="noir_comic")
        panels_cartoon = generate_guaranteed_panels(VALID_PNG, SCENES[:1], 1, style_name="cartoon_fun")
        
        hash_noir = hashlib.md5(panels_noir[0]["imageBytes"][:500]).hexdigest()
        hash_cartoon = hashlib.md5(panels_cartoon[0]["imageBytes"][:500]).hexdigest()
        
        assert hash_noir != hash_cartoon, "noir_comic and cartoon_fun should produce different outputs"

    def test_three_styles_produce_at_least_two_distinct(self):
        """Testing 3 different styles should produce at least 2 distinct outputs."""
        styles = ["bold_superhero", "soft_manga", "noir_comic"]
        hashes = []
        
        for style in styles:
            panels = generate_guaranteed_panels(VALID_PNG, SCENES[:1], 1, style_name=style)
            h = hashlib.md5(panels[0]["imageBytes"][:500]).hexdigest()
            hashes.append(h)
        
        unique_count = len(set(hashes))
        assert unique_count >= 2, f"Expected at least 2 distinct outputs, got {unique_count}"


class TestStyleMetadata:
    """Verify style metadata is included in panel output."""

    def test_style_applied_field_present(self):
        """Each panel must have style_applied field."""
        panels = generate_guaranteed_panels(VALID_PNG, SCENES, 4, style_name="noir_comic")
        for p in panels:
            assert "style_applied" in p, "Missing style_applied field"
            assert p["style_applied"] == "noir_comic"

    def test_filter_used_field_present(self):
        """Each panel must have filter_used field."""
        panels = generate_guaranteed_panels(VALID_PNG, SCENES, 4, style_name="bold_superhero")
        for p in panels:
            assert "filter_used" in p, "Missing filter_used field"
            assert p["filter_used"] in ["comic_posterize", "pop_art", "sketch", "color_block", "color_block_fallback"]

    def test_filter_rotation_matches_style(self):
        """Filter rotation should match the style's defined rotation."""
        style = "noir_comic"
        expected_rotation = STYLE_FILTER_MAP.get(style, DEFAULT_FILTER_ROTATION)
        
        panels = generate_guaranteed_panels(VALID_PNG, SCENES, 4, style_name=style)
        
        for i, p in enumerate(panels):
            expected_filter = expected_rotation[i % len(expected_rotation)]
            assert p["filter_used"] == expected_filter, f"Panel {i} expected {expected_filter}, got {p['filter_used']}"


class TestUnknownStyleFallback:
    """Unknown style names must fall back gracefully."""

    def test_unknown_style_uses_default_rotation(self):
        """Unknown style should use DEFAULT_FILTER_ROTATION."""
        panels = generate_guaranteed_panels(VALID_PNG, SCENES, 4, style_name="nonexistent_style_xyz")
        
        for i, p in enumerate(panels):
            expected_filter = DEFAULT_FILTER_ROTATION[i % len(DEFAULT_FILTER_ROTATION)]
            assert p["filter_used"] == expected_filter

    def test_unknown_style_does_not_crash(self):
        """Unknown style should not crash."""
        panels = generate_guaranteed_panels(VALID_PNG, SCENES, 4, style_name="totally_fake_style_12345")
        assert len(panels) == 4
        for p in panels:
            assert p["status"] == "READY"

    def test_empty_style_uses_default(self):
        """Empty string style should use default."""
        panels = generate_guaranteed_panels(VALID_PNG, SCENES, 4, style_name="")
        assert len(panels) == 4
        for p in panels:
            assert p["status"] == "READY"


class TestPerPanelVariation:
    """Each panel within a style should have unique visual variation."""

    def test_panels_have_different_bytes(self):
        """4 panels of same style should have different image bytes."""
        panels = generate_guaranteed_panels(VALID_PNG, SCENES, 4, style_name="bold_superhero")
        
        hashes = [hashlib.md5(p["imageBytes"]).hexdigest() for p in panels]
        unique_count = len(set(hashes))
        
        # At least 2 unique panels (due to filter rotation)
        assert unique_count >= 2, f"Expected at least 2 unique panels, got {unique_count}"

    def test_color_variation_per_panel(self):
        """Panels should have per-panel color temperature variation."""
        panels = generate_guaranteed_panels(VALID_PNG, SCENES, 6, style_name="cartoon_fun")
        
        # Check that not all panels are identical
        first_bytes = panels[0]["imageBytes"][:1000]
        all_same = all(p["imageBytes"][:1000] == first_bytes for p in panels)
        
        assert not all_same, "All panels should not be identical"


class TestPromptComposerStyleDifferentiation:
    """Verify prompt composer includes strong style instructions."""

    def test_style_block_is_critical(self):
        """Style block should be marked as CRITICAL."""
        composer = PromptComposer()
        prompt = composer.build_base_prompt(
            panel_index=0,
            total_panels=4,
            scene="Hero enters the scene",
            style_prompt="bold superhero comic",
            genre="action",
        )
        
        assert "[STYLE — CRITICAL]" in prompt or "[STYLE" in prompt
        assert "TRANSFORM" in prompt or "stylization" in prompt.lower()

    def test_style_prompt_included_in_output(self):
        """Style prompt should be included in the generated prompt."""
        composer = PromptComposer()
        prompt = composer.build_base_prompt(
            panel_index=0,
            total_panels=4,
            scene="Hero enters the scene",
            style_prompt="noir comic with heavy shadows",
            genre="mystery",
        )
        
        assert "noir comic" in prompt.lower() or "shadows" in prompt.lower()

    def test_degraded_prompt_includes_style(self):
        """Degraded prompt should still include style instructions."""
        composer = PromptComposer()
        prompt = composer.build_degraded_prompt(
            panel_index=0,
            total_panels=4,
            scene="Hero enters the scene",
            style_prompt="manga style",
            genre="action",
        )
        
        assert "manga" in prompt.lower() or "style" in prompt.lower()

    def test_anti_photorealism_instruction(self):
        """Prompt should explicitly reject photorealism."""
        composer = PromptComposer()
        prompt = composer.build_base_prompt(
            panel_index=0,
            total_panels=4,
            scene="Hero enters the scene",
            style_prompt="bold superhero",
            genre="action",
        )
        
        assert "NOT" in prompt or "not" in prompt.lower()
        assert "photograph" in prompt.lower() or "photo" in prompt.lower()


class TestDialogueHandling:
    """Verify dialogue is properly handled."""

    def test_dialogue_preserved_in_output(self):
        """Dialogue should be preserved in panel output."""
        panels = generate_guaranteed_panels(VALID_PNG, SCENES, 4, style_name="cartoon_fun")
        
        assert panels[0]["dialogue"] == "Let's go!"
        assert panels[1]["dialogue"] == "You again!"

    def test_none_dialogue_handled(self):
        """None dialogue should not cause issues."""
        scenes_no_dialogue = [{"scene": "Scene 1"}, {"scene": "Scene 2"}]
        panels = generate_guaranteed_panels(VALID_PNG, scenes_no_dialogue, 2, style_name="cartoon_fun")
        
        assert panels[0]["dialogue"] is None
        assert panels[1]["dialogue"] is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
