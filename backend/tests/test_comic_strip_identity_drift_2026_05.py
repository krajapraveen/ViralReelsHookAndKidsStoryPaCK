"""Regression test for Comic Strip identity drift fix (2026-05).

Founder spec:
  - 3/4/6 panel strips were sometimes returning unrelated people
  - Verify source photo is passed to every panel call (architecture invariant)
  - Verify prompt structure prioritizes IDENTITY over STYLE
  - Verify no panel call is text-only when source photo exists

These tests don't hit the actual image generation API. They verify:
  1. Prompt composition (anti-drift instructions present)
  2. Architecture invariant (source bytes flow through all panels)
  3. No regressions to the validator pipeline
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_identity_block_is_highest_priority():
    """IDENTITY block must come FIRST and be marked CRITICAL/HIGHEST PRIORITY."""
    from services.comic_pipeline.prompt_composer import PromptComposer
    pc = PromptComposer()
    prompt = pc.build_base_prompt(
        panel_index=0,
        total_panels=3,
        scene="Hero finds magic book",
        style_prompt="vibrant cartoon",
        genre="fantasy",
    )
    # Identity must be first block
    assert prompt.index("[IDENTITY — CRITICAL, HIGHEST PRIORITY]") < prompt.index("[STYLE]"), (
        "IDENTITY must appear before STYLE in the prompt"
    )
    # No more competing "STYLE — CRITICAL"
    assert "[STYLE — CRITICAL]" not in prompt, (
        "Removing the [STYLE — CRITICAL] tag was the core anti-drift fix — "
        "do not reintroduce it"
    )
    # Identity language must reference FIRST attached image
    assert "FIRST attached image" in prompt
    assert "protagonist" in prompt.lower()
    assert "do NOT invent a different character" in prompt or "do NOT substitute" in prompt


def test_anti_drift_negative_block():
    """Negative block must explicitly forbid the failure mode."""
    from services.comic_pipeline.prompt_composer import PromptComposer
    pc = PromptComposer()
    prompt = pc.build_base_prompt(
        panel_index=0, total_panels=3, scene="x", style_prompt="x", genre="x",
    )
    assert "[NEGATIVE]" in prompt
    assert "Do NOT replace the protagonist" in prompt
    assert "stock character" in prompt
    assert "different person" in prompt


def test_continuity_block_for_later_panels():
    """Panels 2+ must include continuity instructions referencing prior panels + source."""
    from services.comic_pipeline.prompt_composer import PromptComposer
    pc = PromptComposer()
    p2 = pc.build_base_prompt(panel_index=1, total_panels=3, scene="x", style_prompt="x", genre="x")
    p3 = pc.build_base_prompt(panel_index=2, total_panels=3, scene="x", style_prompt="x", genre="x")
    for p in (p2, p3):
        assert "[CONTINUITY]" in p
        assert "source photo" in p.lower() or "image #1" in p
        assert "SAME person" in p


def test_panel_orchestrator_signature_requires_source_bytes():
    """The architecture invariant: process_panel MUST accept source_image_bytes
    so the photo flows to every panel. If this signature changes, drift may
    return — guarded here as a structural test."""
    import inspect
    from services.comic_pipeline.panel_orchestrator import PanelOrchestrator
    sig = inspect.signature(PanelOrchestrator.process_panel)
    params = list(sig.parameters.keys())
    assert "photo_b64" in params, "process_panel must accept photo_b64 per-panel"
    assert "source_image_bytes" in params, (
        "process_panel must accept source_image_bytes for the validator's "
        "face_consistency check"
    )
    assert "panel_index" in params, "process_panel must know its panel index"
    assert "panel_count" in params, "process_panel must know total panel count"


def test_no_create_original_characters_phrase():
    """Regression guard: the old system message said 'Create original characters'
    which contradicted using the source photo as the protagonist. Confirm it's
    fully gone from the orchestrator."""
    import inspect
    from services.comic_pipeline import panel_orchestrator
    src = inspect.getsource(panel_orchestrator)
    assert "Create original characters" not in src, (
        "The 'Create original characters' phrase caused identity drift — "
        "do not reintroduce"
    )


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
