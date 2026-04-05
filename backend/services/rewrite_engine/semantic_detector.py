"""
Semantic Pattern Detector — catches indirect IP references that bypass exact keyword matching.

Examples:
  - "wizard boy with lightning scar" → Harry Potter
  - "blue alien movie with floating mountains" → Avatar
  - "web-slinging hero from Queens" → Spider-Man
  - "frozen princess with ice powers" → Frozen/Elsa

This is NOT an ML system. It is a hand-built, auditable pattern library
focused on high-abuse-frequency clusters. Patterns are:
  - normalized text matching (lowercase, stripped)
  - multi-keyword co-occurrence detection
  - fuzzy alias matching

Each pattern returns a rewrite suggestion that replaces the matched segment
with a safe, original-sounding alternative.
"""
import re
from typing import List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class SemanticMatch:
    """Result of a semantic pattern match."""
    source_ip: str           # What IP was detected (e.g., "Harry Potter")
    confidence: str          # "high" or "medium"
    matched_keywords: list   # Which keywords triggered this
    safe_rewrite: str        # Suggested safe replacement phrase


# ═══════════════════════════════════════════════════════════════
# SEMANTIC PATTERN LIBRARY
# Each entry: (keywords_that_must_co_occur, source_ip, safe_rewrite)
# keywords is a list of keyword groups. ALL groups must have at least
# one keyword match for the pattern to trigger.
# ═══════════════════════════════════════════════════════════════

_SEMANTIC_PATTERNS: List[Tuple[List[List[str]], str, str, str]] = [
    # ── Harry Potter cluster ──
    (
        [["wizard", "sorcerer", "magical"], ["boy", "young", "student", "kid", "child"], ["scar", "lightning", "forehead"]],
        "Harry Potter", "high",
        "a brave young apprentice at a hidden school of arcane arts",
    ),
    (
        [["wizard", "magic"], ["school", "academy", "castle", "boarding"], ["wand", "spell", "potion"]],
        "Harry Potter (Hogwarts)", "high",
        "a grand academy of mystical arts hidden from the outside world",
    ),
    (
        [["wizard", "witch"], ["dark lord", "dark wizard", "evil sorcerer", "he who", "shall not be named"]],
        "Harry Potter (Voldemort)", "high",
        "a feared dark sorcerer who terrorizes the magical realm",
    ),
    (
        [["wizard", "magic", "wand"], ["sorting", "house", "gryffindor", "slytherin", "hufflepuff", "ravenclaw"]],
        "Harry Potter (Houses)", "high",
        "a mystical academy where students are sorted into rival houses",
    ),
    (
        [["quidditch", "broomstick"], ["flying", "match", "sport", "game"]],
        "Harry Potter (Quidditch)", "medium",
        "a fast-paced aerial sport played on enchanted brooms",
    ),

    # ── Disney / Frozen cluster ──
    (
        [["princess", "queen", "girl"], ["ice", "snow", "frost", "frozen", "cold"], ["power", "magic", "kingdom"]],
        "Frozen/Elsa", "high",
        "a royal maiden with the power to command ice and snow",
    ),
    (
        [["sister", "sibling"], ["ice", "snow", "frozen"], ["kingdom", "castle", "door"]],
        "Frozen (Anna/Elsa)", "medium",
        "two royal sisters separated by a mysterious magical curse",
    ),
    (
        [["let it go", "let go"], ["ice", "snow", "power", "princess", "queen"]],
        "Frozen (Let It Go)", "high",
        "a powerful anthem about embracing one's true nature",
    ),

    # ── Marvel / Spider-Man cluster ──
    (
        [["web", "spider", "wall"], ["climb", "swing", "crawl", "slinger", "slinging"], ["hero", "boy", "teen", "mask", "suit"]],
        "Spider-Man", "high",
        "a young masked hero who scales walls and swings between skyscrapers",
    ),
    (
        [["teen", "boy", "student"], ["bitten", "bite", "spider", "radioactive"], ["power", "super", "strength"]],
        "Spider-Man (origin)", "high",
        "a young student who gains extraordinary abilities from a freak accident",
    ),
    (
        [["uncle", "great power", "responsibility"]],
        "Spider-Man (motto)", "medium",
        "a lesson about the burden of extraordinary gifts",
    ),

    # ── Naruto / Anime cluster ──
    (
        [["ninja", "shinobi"], ["village", "hidden"], ["fox", "demon", "beast", "nine", "tailed", "chakra"]],
        "Naruto", "high",
        "a spirited young ninja harboring a sealed ancient spirit within",
    ),
    (
        [["ninja", "shinobi"], ["headband", "jutsu", "kunai", "rasengan", "shadow clone"]],
        "Naruto (techniques)", "high",
        "a determined ninja mastering forbidden techniques to prove his worth",
    ),
    (
        [["ninja"], ["sharingan", "byakugan", "rinnegan"]],
        "Naruto (eye powers)", "medium",
        "a warrior clan with a mysterious inherited eye ability",
    ),

    # ── Star Wars cluster ──
    (
        [["space", "galactic", "galaxy"], ["knight", "warrior", "order"], ["light", "laser", "saber", "sword", "force"]],
        "Star Wars", "high",
        "an ancient order of space warriors wielding energy blades",
    ),
    (
        [["father", "dad"], ["dark side", "dark", "evil"], ["luke", "son", "reveal", "am your"]],
        "Star Wars (I am your father)", "high",
        "a shocking revelation that the hero's greatest enemy is family",
    ),
    (
        [["small", "green", "old", "ancient"], ["wise", "master", "mentor"], ["speak", "backward", "syntax"]],
        "Star Wars (Yoda)", "medium",
        "an ancient diminutive sage who speaks in reversed phrasing",
    ),

    # ── Pokémon cluster ──
    (
        [["creature", "monster", "beast", "pet"], ["catch", "capture", "collect", "train", "tame"], ["ball", "battle", "evolve"]],
        "Pokémon", "high",
        "a world where trainers bond with and battle alongside magical creatures",
    ),
    (
        [["electric", "yellow"], ["mouse", "rodent", "creature"], ["cute", "companion", "starter"]],
        "Pokémon (Pikachu)", "medium",
        "a small yellow electric creature and loyal companion",
    ),

    # ── Avatar (James Cameron) cluster ──
    (
        [["blue", "tall", "alien"], ["planet", "moon", "jungle", "forest"], ["floating", "mountain", "tree", "connect"]],
        "Avatar", "high",
        "indigenous aliens on a lush alien world with floating landscapes",
    ),

    # ── Pixar-style cluster ──
    (
        [["toy", "toys"], ["alive", "living", "talk", "secret life"], ["child", "kid", "owner", "play"]],
        "Toy Story", "high",
        "beloved toys that secretly come alive when their owner is away",
    ),
    (
        [["fish", "ocean", "sea"], ["lost", "missing", "find", "search"], ["father", "dad", "parent", "clown"]],
        "Finding Nemo", "high",
        "a worried parent fish crossing the ocean to find a lost child",
    ),
    (
        [["emotion", "feeling", "joy", "sadness", "anger", "fear", "disgust"], ["inside", "head", "mind", "brain", "control"]],
        "Inside Out", "high",
        "personified emotions guiding decisions inside a young person's mind",
    ),
    (
        [["car", "race", "racing"], ["talk", "alive", "living", "eyes"], ["champion", "win", "speed"]],
        "Cars/Lightning McQueen", "medium",
        "a world of sentient racing vehicles competing for glory",
    ),

    # ── Lord of the Rings cluster ──
    (
        [["ring", "one ring"], ["destroy", "mount", "volcano", "doom"], ["hobbit", "small", "shire"]],
        "Lord of the Rings", "high",
        "a humble halfling on a perilous quest to destroy a cursed artifact",
    ),
    (
        [["old", "grey", "white"], ["wizard", "staff"], ["shall not pass", "balrog", "fellowship"]],
        "Lord of the Rings (Gandalf)", "medium",
        "a venerable wandering sorcerer guiding a fellowship through darkness",
    ),
]


def _normalize(text: str) -> str:
    """Normalize text for pattern matching."""
    return text.lower().strip()


def _keywords_match(text_lower: str, keyword_groups: List[List[str]]) -> Tuple[bool, List[str]]:
    """
    Check if ALL keyword groups have at least one keyword present in text.
    Returns (all_matched, list_of_matched_keywords).
    """
    matched = []
    for group in keyword_groups:
        group_hit = False
        for kw in group:
            if kw in text_lower:
                matched.append(kw)
                group_hit = True
                break
        if not group_hit:
            return False, []
    return True, matched


def detect_semantic_patterns(text: str) -> List[SemanticMatch]:
    """
    Scan text for indirect IP references using semantic pattern matching.
    Returns list of matches sorted by confidence (high first).
    """
    if not text or len(text) < 10:
        return []

    text_lower = _normalize(text)
    matches = []

    for keyword_groups, source_ip, confidence, safe_rewrite in _SEMANTIC_PATTERNS:
        all_matched, matched_kws = _keywords_match(text_lower, keyword_groups)
        if all_matched:
            matches.append(SemanticMatch(
                source_ip=source_ip,
                confidence=confidence,
                matched_keywords=matched_kws,
                safe_rewrite=safe_rewrite,
            ))

    # Sort: high confidence first
    matches.sort(key=lambda m: 0 if m.confidence == "high" else 1)
    return matches


def has_semantic_risk(text: str) -> bool:
    """Quick check: does text contain any indirect IP references?"""
    return len(detect_semantic_patterns(text)) > 0
