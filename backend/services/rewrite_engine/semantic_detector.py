"""
Semantic Pattern Detector — catches indirect IP references that bypass exact keyword matching.

Two detection layers:
  1. Co-occurrence patterns: multi-keyword groups that must ALL match (indirect descriptions)
  2. Fuzzy alias matching: catches obfuscated direct names (leet speak, spacing, typos, diacritics)

This is NOT an ML system. Hand-built, auditable pattern library
focused on high-abuse-frequency IP clusters only.
"""
import re
import unicodedata
from typing import List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class SemanticMatch:
    """Result of a semantic pattern match."""
    source_ip: str           # What IP was detected (e.g., "Harry Potter")
    confidence: str          # "high" or "medium"
    matched_keywords: list   # Which keywords triggered this
    safe_rewrite: str        # Suggested safe replacement phrase
    detection_type: str = "semantic"  # "semantic" or "fuzzy_alias"


# ═══════════════════════════════════════════════════════════════
# TEXT NORMALIZATION — strips obfuscation before matching
# ═══════════════════════════════════════════════════════════════

_LEET_MAP = str.maketrans({
    "0": "o", "1": "i", "3": "e", "4": "a", "5": "s",
    "7": "t", "8": "b", "9": "g", "@": "a", "$": "s",
    "!": "i", "+": "t",
})


def _strip_diacritics(text: str) -> str:
    """Remove accents/diacritics: ë→e, ñ→n, etc."""
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _normalize_deep(text: str) -> str:
    """
    Aggressive normalization for obfuscation detection:
    1. lowercase
    2. strip diacritics (Spïdêr → Spider)
    3. leet speak (sp1der → spider, h4rry → harry)
    4. collapse repeated chars (narutoo → naruto)
    5. collapse spaces/separators (h a r r y → harry)
    """
    text = text.lower().strip()
    text = _strip_diacritics(text)
    text = text.translate(_LEET_MAP)
    # Collapse repeated characters (3+ → 2)
    text = re.sub(r"(.)\1{2,}", r"\1\1", text)
    return text


def _collapse_spaces(text: str) -> str:
    """Remove all spaces and hyphens for alias matching: 'h a r r y' → 'harry'."""
    return re.sub(r"[\s\-_.,]+", "", text)


# ═══════════════════════════════════════════════════════════════
# FUZZY ALIAS REGISTRY — catches obfuscated direct name references
# Each: (canonical_collapsed, source_ip, safe_rewrite)
# Matched against _collapse_spaces(_normalize_deep(text))
# ═══════════════════════════════════════════════════════════════

_FUZZY_ALIASES: List[Tuple[str, str, str]] = [
    # Harry Potter universe (+ common typos)
    ("harrypotter", "Harry Potter", "a young wizard hero"),
    ("harrypottr", "Harry Potter", "a young wizard hero"),
    ("harrypottter", "Harry Potter", "a young wizard hero"),
    ("harrpotter", "Harry Potter", "a young wizard hero"),
    ("hogwarts", "Harry Potter (Hogwarts)", "a hidden academy of mystical arts"),
    ("hogwrts", "Harry Potter (Hogwarts)", "a hidden academy of mystical arts"),
    ("voldemort", "Harry Potter (Voldemort)", "a feared dark sorcerer"),
    ("dumbledore", "Harry Potter (Dumbledore)", "a wise elderly headmaster"),
    ("hermione", "Harry Potter (Hermione)", "a brilliant young scholar"),
    ("gryffindor", "Harry Potter (Houses)", "a brave student house"),
    ("slytherin", "Harry Potter (Houses)", "a cunning student house"),
    ("quidditch", "Harry Potter (Quidditch)", "an aerial sport on enchanted brooms"),
    # Marvel / Spider-Man (+ common typos)
    ("spiderman", "Spider-Man", "a web-slinging masked hero"),
    ("spidermen", "Spider-Man", "a web-slinging masked hero"),
    ("spidrmn", "Spider-Man", "a web-slinging masked hero"),
    ("peterparker", "Spider-Man", "a young hero with wall-crawling abilities"),
    ("ironman", "Marvel (Iron Man)", "a genius inventor in powered armor"),
    ("tonystark", "Marvel (Iron Man)", "a genius billionaire inventor"),
    ("avengers", "Marvel (Avengers)", "a team of extraordinary heroes"),
    ("thanos", "Marvel (Thanos)", "a powerful cosmic villain"),
    # Disney / Frozen (no bare "frozen" — it's a common English word)
    ("elsa", "Frozen (Elsa)", "a princess with ice powers"),
    ("frozenmovie", "Frozen", "an ice princess adventure"),
    ("frozenelsa", "Frozen (Elsa)", "a princess with ice powers"),
    # Naruto / Anime (+ common typos)
    ("naruto", "Naruto", "a ninja warrior with hidden power"),
    ("narutoo", "Naruto", "a ninja warrior with hidden power"),
    ("sasuke", "Naruto (Sasuke)", "a rival ninja from a cursed clan"),
    ("kakashi", "Naruto (Kakashi)", "a masked ninja mentor"),
    # Star Wars
    ("starwars", "Star Wars", "an epic space saga"),
    ("darthvader", "Star Wars (Vader)", "a dark armored space villain"),
    ("lukeskywalker", "Star Wars (Luke)", "a young space warrior"),
    ("yoda", "Star Wars (Yoda)", "an ancient diminutive sage"),
    ("lightsaber", "Star Wars", "an energy blade weapon"),
    ("lightsabre", "Star Wars", "an energy blade weapon"),
    # Pokemon (+ common typos)
    ("pokemon", "Pokémon", "a creature training adventure"),
    ("pikachu", "Pokémon (Pikachu)", "an electric creature companion"),
    ("pikchu", "Pokémon (Pikachu)", "an electric creature companion"),
    ("charizard", "Pokémon (Charizard)", "a fire-breathing dragon creature"),
    # LOTR
    ("lordoftherings", "Lord of the Rings", "an epic fantasy quest"),
    ("gandalf", "Lord of the Rings (Gandalf)", "a venerable wandering sorcerer"),
    ("frodo", "Lord of the Rings (Frodo)", "a humble halfling on a quest"),
    ("gollum", "Lord of the Rings (Gollum)", "a wretched creature obsessed with a ring"),
    # Pixar
    ("toystory", "Toy Story", "a tale of toys that come alive"),
    ("findingnemo", "Finding Nemo", "an ocean adventure to find a lost fish"),
    ("insideout", "Inside Out", "a story of personified emotions"),
    ("lightningmcqueen", "Cars", "a sentient racing vehicle"),
    # Avatar (no bare "avatar" — it's a common English word)
    ("avatarmovie", "Avatar", "indigenous aliens on a lush world"),
    ("pandoraplanet", "Avatar (Pandora)", "an alien world with floating landscapes"),
]


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
        "a determined young mage who bears an ancient mark and trains at a hidden academy",
    ),
    (
        [["wizard", "magic"], ["school", "academy", "castle", "boarding"], ["wand", "spell", "potion"]],
        "Harry Potter (Hogwarts)", "high",
        "a towering, enchanted institution where pupils study forbidden disciplines",
    ),
    (
        [["wizard", "witch"], ["dark lord", "dark wizard", "evil sorcerer", "he who", "shall not be named"]],
        "Harry Potter (Voldemort)", "high",
        "a dreaded sorcerer who fractured his own soul in pursuit of immortality",
    ),
    (
        [["wizard", "magic", "wand"], ["sorting", "house", "gryffindor", "slytherin", "hufflepuff", "ravenclaw"]],
        "Harry Potter (Houses)", "high",
        "an academy that assigns pupils to rival dormitories based on their character",
    ),
    (
        [["quidditch", "broomstick"], ["flying", "match", "sport", "game"]],
        "Harry Potter (Quidditch)", "medium",
        "a fast-paced aerial team sport played on enchanted brooms",
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
        "a teenage acrobat who gained extraordinary agility and patrols the city at night",
    ),
    (
        [["teen", "boy", "student"], ["bitten", "bite", "spider", "radioactive"], ["power", "super", "strength"]],
        "Spider-Man (origin)", "high",
        "a quiet student whose life transforms after a freak laboratory accident",
    ),
    (
        [["uncle", "great power", "responsibility"]],
        "Spider-Man (motto)", "medium",
        "a hard-learned lesson about the weight that comes with extraordinary gifts",
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
        [["space", "galactic", "galaxy", "star"], ["knight", "warrior", "order", "saga", "war"], ["light", "laser", "saber", "sword", "force", "dark side"]],
        "Star Wars", "high",
        "an ancient order of space warriors wielding energy blades",
    ),
    (
        [["space", "galactic", "galaxy"], ["dark lord", "dark side", "evil emperor", "empire"], ["rebel", "resist", "fight", "sword", "saber", "force"]],
        "Star Wars (Empire)", "high",
        "a rebel alliance fighting a tyrannical galactic empire",
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
        [["electric", "thunder", "shock", "bolt"], ["mouse", "rodent", "creature", "critter"], ["yellow", "small", "cute", "companion"]],
        "Pokémon (Pikachu)", "medium",
        "a small yellow electric creature and loyal companion",
    ),
    (
        [["creature", "monster", "beast"], ["train", "tame", "collect", "catch"], ["gym", "badge", "league", "champion"]],
        "Pokémon (league)", "medium",
        "a young trainer competing in creature battle tournaments",
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
    """Normalize text for co-occurrence pattern matching."""
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


def _detect_fuzzy_aliases(text: str) -> List[SemanticMatch]:
    """
    Detect obfuscated direct IP names via fuzzy alias matching.
    Handles leet speak, spacing, diacritics, and common misspellings.
    """
    normalized = _normalize_deep(text)
    collapsed = _collapse_spaces(normalized)

    matches = []
    for alias, source_ip, safe_rewrite in _FUZZY_ALIASES:
        if alias in collapsed:
            matches.append(SemanticMatch(
                source_ip=source_ip,
                confidence="high",
                matched_keywords=[alias],
                safe_rewrite=safe_rewrite,
                detection_type="fuzzy_alias",
            ))
    return matches


def detect_semantic_patterns(text: str) -> List[SemanticMatch]:
    """
    Scan text for indirect IP references using two detection layers:
    1. Co-occurrence patterns (indirect descriptions)
    2. Fuzzy alias matching (obfuscated direct names)
    Returns list of matches sorted by confidence (high first).
    """
    if not text or len(text) < 5:
        return []

    matches = []

    # Layer 1: Co-occurrence pattern matching
    text_lower = _normalize(text)
    for keyword_groups, source_ip, confidence, safe_rewrite in _SEMANTIC_PATTERNS:
        all_matched, matched_kws = _keywords_match(text_lower, keyword_groups)
        if all_matched:
            matches.append(SemanticMatch(
                source_ip=source_ip,
                confidence=confidence,
                matched_keywords=matched_kws,
                safe_rewrite=safe_rewrite,
                detection_type="semantic",
            ))

    # Layer 2: Fuzzy alias detection (only if Layer 1 found nothing)
    if not matches:
        matches = _detect_fuzzy_aliases(text)

    # Sort: high confidence first
    matches.sort(key=lambda m: 0 if m.confidence == "high" else 1)
    return matches


def has_semantic_risk(text: str) -> bool:
    """Quick check: does text contain any indirect IP references?"""
    return len(detect_semantic_patterns(text)) > 0


def get_detection_stats(text: str) -> dict:
    """Return detailed detection stats for telemetry."""
    matches = detect_semantic_patterns(text)
    return {
        "has_risk": len(matches) > 0,
        "match_count": len(matches),
        "matches": [
            {
                "source_ip": m.source_ip,
                "confidence": m.confidence,
                "detection_type": m.detection_type,
                "matched_keywords": m.matched_keywords,
            }
            for m in matches
        ],
    }
