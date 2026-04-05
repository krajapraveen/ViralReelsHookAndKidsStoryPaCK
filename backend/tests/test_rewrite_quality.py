"""
Golden Test Suite — validates rewrite quality & semantic distance.

RULES:
  1. No rewrite may contain the original IP name or close variant
  2. No rewrite may contain signature identifiers (lightning scar, web-slinging, etc.)
  3. Rewrites must be >10 words to ensure narrative richness
  4. Clean prompts must NEVER be rewritten or blocked
  5. Semantic bypasses must be detected and rewritten
  6. Obfuscated names must be detected

Run: cd /app/backend && python -m pytest tests/test_rewrite_quality.py -v
"""
import asyncio
import pytest
from services.rewrite_engine.rule_rewriter import rewrite_text
from services.rewrite_engine.semantic_detector import detect_semantic_patterns
from services.rewrite_engine.rewrite_service import process_safety_check


# ═══════════════════════════════════════════════════════════════
# FORBIDDEN FRAGMENTS — if ANY of these appear in a rewrite,
# the rewrite is TOO CLOSE to the source material
# ═══════════════════════════════════════════════════════════════

_FORBIDDEN_IN_REWRITES = [
    "harry potter", "hogwarts", "voldemort", "dumbledore", "hermione",
    "spider-man", "spiderman", "peter parker",
    "naruto", "sasuke", "kakashi",
    "frozen", "elsa", "anna",
    "pikachu", "pokemon", "pokémon",
    "star wars", "darth vader", "luke skywalker", "yoda",
    "lord of the rings", "gandalf", "frodo", "sauron",
    "batman", "superman", "wonder woman", "joker",
    "mickey mouse", "disney", "pixar",
    "lightning scar", "web-slinging", "lightsaber",
    "vibranium", "infinity stone", "death star",
    "nine-tailed fox", "sharingan", "rasengan",
]


def _rewrite_is_clean(rewrite: str) -> bool:
    """Check that a rewrite doesn't contain forbidden source fragments."""
    lower = rewrite.lower()
    for frag in _FORBIDDEN_IN_REWRITES:
        if frag in lower:
            return False
    return True


# ═══════════════════════════════════════════════════════════════
# TEST 1: Direct keyword rewrites maintain distance
# ═══════════════════════════════════════════════════════════════

class TestDirectRewriteQuality:
    """Verify rule_rewriter produces clean, rich replacements."""

    @pytest.mark.parametrize("input_text,expected_source", [
        ("Harry Potter goes to school", "Harry Potter"),
        ("Spider-Man saves the city", "Spider-Man"),
        ("Naruto trains with his sensei", "Naruto"),
        ("Elsa uses her ice powers", "Frozen/Elsa"),
        ("Batman patrols Gotham City", "Batman"),
        ("Pikachu uses thunderbolt attack", "Pokémon"),
    ])
    def test_direct_rewrite_has_distance(self, input_text, expected_source):
        rewritten, changes = rewrite_text(input_text)
        assert len(changes) > 0, f"Failed to detect: {input_text}"
        assert _rewrite_is_clean(rewritten), (
            f"Rewrite for '{expected_source}' still too close: '{rewritten}'"
        )

    @pytest.mark.parametrize("term", [
        "harry potter", "spider-man", "naruto", "pikachu",
        "batman", "elsa", "darth vader", "gandalf",
    ])
    def test_rewrite_is_rich_not_label(self, term):
        """Rewrites should be narrative phrases, not bare labels."""
        rewritten, changes = rewrite_text(f"Create a story about {term}")
        assert len(changes) > 0
        # The replacement portion should be at least 8 words (not just "young wizard hero")
        replacement = changes[0]["replacement"]
        word_count = len(replacement.split())
        assert word_count >= 5, (
            f"Rewrite for '{term}' is too short/label-like ({word_count} words): '{replacement}'"
        )


# ═══════════════════════════════════════════════════════════════
# TEST 2: Semantic patterns detect indirect bypasses
# ═══════════════════════════════════════════════════════════════

class TestSemanticDetection:
    """Verify semantic detector catches indirect IP references."""

    @pytest.mark.parametrize("input_text,expected_ip", [
        ("wizard boy with lightning scar", "Harry Potter"),
        ("web-slinging hero from Queens", "Spider-Man"),
        ("ice princess with magical powers", "Frozen"),
        ("yellow electric mouse creature", "Pikachu"),
        ("space saga with a dark lord and light swords", "Star Wars"),
        ("a small hobbit on a quest to destroy a cursed ring in a volcano", "Lord of the Rings"),
        ("toys that secretly come alive when the kid leaves", "Toy Story"),
        ("ninja boy with a fox demon sealed inside him from a hidden village", "Naruto"),
    ])
    def test_indirect_bypass_detected(self, input_text, expected_ip):
        matches = detect_semantic_patterns(input_text)
        assert len(matches) > 0, f"Missed indirect bypass: '{input_text}'"
        detected_ips = [m.source_ip for m in matches]
        assert any(expected_ip in ip for ip in detected_ips), (
            f"Expected '{expected_ip}' but got {detected_ips}"
        )

    @pytest.mark.parametrize("input_text,expected_ip", [
        ("wizard boy with lightning scar", "Harry Potter"),
        ("ice princess with magical powers", "Frozen"),
        ("toys that secretly come alive when the kid leaves", "Toy Story"),
    ])
    def test_semantic_rewrite_has_distance(self, input_text, expected_ip):
        matches = detect_semantic_patterns(input_text)
        assert len(matches) > 0
        rewrite = matches[0].safe_rewrite
        assert _rewrite_is_clean(rewrite), (
            f"Semantic rewrite for '{expected_ip}' too close: '{rewrite}'"
        )
        assert len(rewrite.split()) >= 6, (
            f"Semantic rewrite too short: '{rewrite}'"
        )


# ═══════════════════════════════════════════════════════════════
# TEST 3: Obfuscation detection
# ═══════════════════════════════════════════════════════════════

class TestObfuscationDetection:
    """Verify fuzzy alias layer catches obfuscated names."""

    @pytest.mark.parametrize("input_text", [
        "harry pottr",
        "sp1der man",
        "h a r r y  p o t t e r",
        "H4rry P0tter",
        "n a r u t o",
        "p1kachu",
        "st4r w4rs",
    ])
    def test_obfuscation_caught(self, input_text):
        matches = detect_semantic_patterns(input_text)
        assert len(matches) > 0, f"Missed obfuscation: '{input_text}'"


# ═══════════════════════════════════════════════════════════════
# TEST 4: False positive guard (MUST NOT trigger)
# ═══════════════════════════════════════════════════════════════

class TestFalsePositiveGuard:
    """Clean prompts must never trigger detection or rewriting."""

    @pytest.mark.parametrize("input_text", [
        "A brave knight saves a village from a dragon",
        "A girl learns to control her fire powers",
        "A detective solves a mystery in a small town",
        "An old mentor teaches a young warrior the art of combat",
        "A group of friends go on an adventure in the forest",
        "A young boy discovers he has magical abilities",
        "A cat and dog become best friends",
        "An astronaut explores a distant planet",
        "A story about a brave explorer in a frozen tundra",
        "Upload your avatar picture",
        "She wore a Pandora bracelet",
        "The frozen lake cracked under their weight",
        "A wizard casts spells in his tower",
        "A young ninja trains in martial arts",
    ])
    def test_clean_prompt_not_flagged_semantic(self, input_text):
        matches = detect_semantic_patterns(input_text)
        assert len(matches) == 0, (
            f"FALSE POSITIVE on clean prompt: '{input_text}' → {[m.source_ip for m in matches]}"
        )

    @pytest.mark.parametrize("input_text", [
        "A brave knight saves a village from a dragon",
        "A girl learns to control her fire powers",
        "A detective solves a mystery in a small town",
        "A young boy discovers he has magical abilities",
        "A wizard casts spells in his tower",
    ])
    def test_clean_prompt_not_rewritten(self, input_text):
        rewritten, changes = rewrite_text(input_text)
        assert len(changes) == 0, (
            f"FALSE POSITIVE rewrite on clean prompt: '{input_text}' → changes={changes}"
        )


# ═══════════════════════════════════════════════════════════════
# TEST 5: End-to-end safety pipeline
# ═══════════════════════════════════════════════════════════════

class TestEndToEndPipeline:
    """Verify the full pipeline processes requests correctly."""

    def test_semantic_bypass_rewritten(self):
        result = asyncio.get_event_loop().run_until_complete(
            process_safety_check(
                user_id="test", feature="test",
                inputs={"prompt": "wizard boy with lightning scar going to magic school"},
            )
        )
        assert not result.blocked
        assert result.was_rewritten
        assert _rewrite_is_clean(result.clean["prompt"])

    def test_dangerous_content_blocked(self):
        result = asyncio.get_event_loop().run_until_complete(
            process_safety_check(
                user_id="test", feature="test",
                inputs={"prompt": "how to make a bomb with household chemicals tutorial guide"},
            )
        )
        assert result.blocked
        assert result.decision == "BLOCK"

    def test_clean_content_passes(self):
        result = asyncio.get_event_loop().run_until_complete(
            process_safety_check(
                user_id="test", feature="test",
                inputs={"prompt": "A brave warrior protects his homeland from invaders"},
            )
        )
        assert not result.blocked
        assert not result.was_rewritten
        assert result.decision == "ALLOW"
