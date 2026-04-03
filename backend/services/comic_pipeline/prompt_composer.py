"""
Prompt Composer — Deterministic, config-driven, patch-based prompt builder.
NOT an AI playground. Composable, testable prompt blocks with failure-specific repair patches.

Layers: identity_block + style_block + story_block + composition_block + continuity_block + negative_block
Repair patches: face_drift, style_drift, low_source_similarity, story_mismatch, continuity_break, composition_clutter
"""
import logging
from typing import List, Optional, Dict

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from enums.pipeline_enums import FailureType, RepairMode

logger = logging.getLogger("creatorstudio.comic_pipeline.prompt_composer")


# ══════════════════════════════════════════════════════════════════════════════
# REPAIR PATCHES — Deterministic text blocks, not LLM-generated
# ══════════════════════════════════════════════════════════════════════════════

REPAIR_PATCHES = {
    FailureType.FACE_DRIFT: """
[REPAIR: FACE]
Critical: preserve exact facial identity from the uploaded reference and prior approved panels.
Use a clear frontal or near-frontal face angle.
Do not stylize the face so aggressively that identity is lost.
Prioritize likeness over artistic flourish.
The character's facial features, skin tone, and hairstyle must remain consistent.
""",

    FailureType.STYLE_DRIFT: """
[REPAIR: STYLE]
Match the exact comic rendering style, line quality, shading density, and color treatment of the approved panels.
Do not switch to a different illustration style.
Maintain uniform visual language across the entire sequence.
Keep consistent line weight, color saturation, and shading technique.
""",

    FailureType.LOW_SOURCE_SIMILARITY: """
[REPAIR: SOURCE_SIMILARITY]
The subject must strongly resemble the uploaded person.
Simplify background and reduce distractions.
Frame the character prominently in the center.
Preserve facial proportions and distinguishing features precisely.
Use medium shot or close-medium shot for maximum face readability.
""",

    FailureType.STORY_MISMATCH: """
[REPAIR: STORY]
This panel must depict exactly the specified story beat.
The visible action must clearly communicate the intended scene.
The emotion must read immediately and unmistakably.
Do not invent unrelated actions, settings, or characters.
Keep the narrative focus tight and unambiguous.
""",

    FailureType.CONTINUITY_BREAK: """
[REPAIR: CONTINUITY]
Match the previously approved character appearance, clothing, environment, and scene logic.
This panel must feel like part of the same comic sequence, not a new universe.
Maintain the same time of day, weather, and visual environment from prior panels.
""",

    FailureType.COMPOSITION_CLUTTER: """
[REPAIR: COMPOSITION]
Use a cleaner composition with one dominant subject.
Reduce background clutter and secondary objects.
Keep subject centered or clearly emphasized.
Ensure face and body are fully readable.
Leave clean space appropriate for comic panel layout.
""",
}

DEGRADED_MODE_PATCH = """
[DEGRADED MODE]
Prefer clear readable comic storytelling over detail complexity.
Use simplified background, stable character rendering, and strong continuity.
Prioritize character identity and story clarity above visual richness.
Use straightforward camera angle (medium shot, front or three-quarter view).
"""

NEGATIVE_BLOCK = """
[NEGATIVE]
Do not change gender, age, ethnicity, face structure, hairstyle, or outfit unexpectedly.
Do not add extra fingers, duplicate people, warped anatomy, blurred face, heavy background clutter, or unreadable composition.
No copyrighted characters, logos, or trademarked designs.
No NSFW content.
"""


class PromptComposer:
    """
    Builds layered prompts for comic panel generation.
    Config-driven, patch-based, deterministic.
    """

    def build_base_prompt(
        self,
        panel_index: int,
        total_panels: int,
        scene: str,
        style_prompt: str,
        genre: str,
        character_lock: Optional[Dict] = None,
        negative_prompt: str = "",
    ) -> str:
        """Compose the full base prompt from 6 blocks."""
        parts = []

        # Block 1: Identity
        identity = """[IDENTITY]
Main character reference: person from uploaded photo.
Preserve facial identity, skin tone, hairstyle, jawline, nose shape, and overall likeness.
Keep outfit consistent unless the story explicitly changes it."""

        if character_lock:
            traits = character_lock.get("visual_traits", {})
            if traits:
                trait_lines = [f"- {k}: {v}" for k, v in traits.items() if v]
                if trait_lines:
                    identity += "\nCharacter traits to preserve:\n" + "\n".join(trait_lines)
        parts.append(identity)

        # Block 2: Style (PRIORITY — must be the strongest instruction)
        parts.append(f"""[STYLE — CRITICAL]
TRANSFORM this into a {style_prompt} illustration.
This MUST NOT look like a photograph. Apply heavy stylization.
The output must be unmistakably a comic/illustration, not a photo filter.
Maintain consistent rendering style across all panels.
Avoid photorealism entirely. Every pixel should read as drawn/illustrated art.""")

        # Block 3: Story
        parts.append(f"""[STORY]
This is panel {panel_index + 1} of {total_panels}.
Scene: {scene}
Genre: {genre}""")

        # Block 4: Composition
        parts.append("""[COMPOSITION]
Medium shot, subject clearly visible, face readable, uncluttered framing.
Leave clean space for comic layout.
Avoid cropped forehead, cropped chin, or missing hands unless intentional.""")

        # Block 5: Continuity
        if panel_index > 0:
            parts.append(f"""[CONTINUITY]
Match character identity and outfit with prior approved panels.
Preserve environment logic and visual continuity.
This is panel {panel_index + 1} in a {total_panels}-panel sequence.""")

        # Block 6: Negative
        if negative_prompt:
            parts.append(f"[NEGATIVE]\n{negative_prompt}")
        else:
            parts.append(NEGATIVE_BLOCK)

        return "\n\n".join(parts)

    def build_repair_prompt(
        self,
        base_prompt: str,
        failure_types: List[FailureType],
        repair_mode: RepairMode,
        panel_index: int = 0,
        scene: str = "",
        emotion: str = "",
        action: str = "",
    ) -> str:
        """
        Build a repaired prompt by appending failure-specific patches.
        Does NOT use LLM to rewrite — purely deterministic patch composition.
        """
        parts = [base_prompt]

        # Add failure-specific patches
        for ft in failure_types:
            patch = REPAIR_PATCHES.get(ft)
            if patch:
                parts.append(patch)

        # For story mismatch, inject specific story details
        if FailureType.STORY_MISMATCH in failure_types and scene:
            parts.append(f"Exact story beat: {scene}")
            if emotion:
                parts.append(f"Required emotion: {emotion}")
            if action:
                parts.append(f"Required action: {action}")

        # In degraded mode, add simplification patch
        if repair_mode in (RepairMode.R3_STRUCTURAL_REPAIR, RepairMode.R4_DEGRADED_FALLBACK):
            parts.append(DEGRADED_MODE_PATCH)

        return "\n\n".join(parts)

    def build_degraded_prompt(
        self,
        panel_index: int,
        total_panels: int,
        scene: str,
        style_prompt: str,
        genre: str,
        negative_prompt: str = "",
    ) -> str:
        """
        Build a simplified, failure-resistant prompt for Tier 4 fallback.
        Reduced visual ambition, maximum clarity and identity preservation.
        """
        return f"""Create a comic panel illustration. This MUST look like drawn comic art, NOT a photograph.

Panel {panel_index + 1} of {total_panels}.
Scene: {scene}
Style: {style_prompt} — apply this style strongly. Heavy stylization required.
Genre: {genre}

IMPORTANT:
- TRANSFORM the reference photo into comic art — DO NOT return anything resembling a photograph
- The character must look like a stylized comic version of the person in the reference photo
- Use bold lines, comic shading, and illustrated textures
- Use a clear, readable medium shot
- Keep the background simple and uncluttered
- Prioritize character identity and story clarity
- Maintain consistency with other panels in the sequence

{DEGRADED_MODE_PATCH}

{negative_prompt or NEGATIVE_BLOCK}"""
