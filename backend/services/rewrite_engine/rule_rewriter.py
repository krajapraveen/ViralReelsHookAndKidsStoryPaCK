"""
Rule-based rewriter — instant dictionary replacements.
Case-insensitive, whole-word matching with hyphen/spacing variant handling.
"""
import re
from typing import Dict, List, Tuple

# ═══════════════════════════════════════════════════════════════
# REPLACEMENT DICTIONARY — risky term -> safe generic equivalent
# ═══════════════════════════════════════════════════════════════

REPLACEMENTS: Dict[str, str] = {
    # ── Platforms ──
    "youtube": "global video platform",
    "instagram": "social sharing platform",
    "tiktok": "short video platform",
    "facebook": "social media network",
    "whatsapp": "messaging platform",
    "twitter": "microblogging platform",
    "snapchat": "ephemeral media app",
    "reddit": "online discussion forum",
    "twitch": "live streaming platform",
    "linkedin": "professional networking platform",
    "pinterest": "visual discovery platform",
    "spotify": "music streaming service",
    "netflix": "streaming entertainment platform",
    "amazon prime": "premium streaming service",
    "hulu": "on-demand streaming service",
    "discord": "community chat platform",
    "telegram": "secure messaging app",
    "uber": "ride-hailing service",
    "airbnb": "home-sharing travel platform",

    # ── Tech Brands ──
    "google": "leading search engine",
    "amazon": "global e-commerce giant",
    "apple": "premium tech company",
    "microsoft": "enterprise software leader",
    "samsung": "electronics manufacturer",
    "sony": "consumer electronics brand",
    "nvidia": "graphics technology company",
    "intel": "processor technology company",
    "tesla": "electric vehicle innovator",
    "spacex": "private space exploration company",

    # ── Fashion & Lifestyle Brands ──
    "nike": "athletic sportswear brand",
    "adidas": "sports lifestyle brand",
    "puma": "athletic fashion brand",
    "gucci": "luxury fashion house",
    "louis vuitton": "luxury designer label",
    "chanel": "haute couture fashion house",
    "prada": "Italian luxury brand",
    "rolex": "prestigious watchmaker",
    "zara": "fast fashion retailer",
    "h&m": "affordable fashion chain",

    # ── Food & Beverage ──
    "coca cola": "classic cola brand",
    "coca-cola": "classic cola brand",
    "pepsi": "popular cola brand",
    "mcdonalds": "global fast food chain",
    "mcdonald's": "global fast food chain",
    "starbucks": "premium coffee chain",
    "burger king": "fast food restaurant",
    "kfc": "fried chicken restaurant",
    "subway": "sandwich restaurant chain",
    "dominos": "pizza delivery chain",
    "domino's": "pizza delivery chain",

    # ── Automotive ──
    "ferrari": "luxury sports car maker",
    "lamborghini": "exotic supercar manufacturer",
    "porsche": "performance car brand",
    "bmw": "luxury automobile brand",
    "mercedes": "premium car manufacturer",
    "mercedes-benz": "premium car manufacturer",
    "audi": "luxury car brand",
    "toyota": "global auto manufacturer",
    "ford": "American auto manufacturer",

    # ── Disney / Pixar Franchise ──
    "disney": "magical animated world",
    "pixar": "colorful 3D animated style",
    "frozen": "ice princess adventure",
    "lion king": "savanna prince tale",
    "the lion king": "savanna prince tale",
    "little mermaid": "undersea princess story",
    "the little mermaid": "undersea princess story",
    "finding nemo": "ocean fish adventure",
    "toy story": "living toys adventure",
    "moana": "ocean voyager heroine",

    # ── Disney / Pixar Characters ──
    "mickey mouse": "classic cartoon mouse",
    "minnie mouse": "classic cartoon mouse friend",
    "donald duck": "cartoon duck character",
    "goofy": "clumsy cartoon dog",
    "elsa": "ice-powered princess",
    "anna": "brave adventurer princess",
    "simba": "young lion prince",
    "mufasa": "wise lion king",
    "nemo": "brave little clownfish",
    "dory": "forgetful blue fish friend",
    "woody": "loyal cowboy toy leader",
    "buzz lightyear": "space ranger action figure",
    "rapunzel": "long-haired tower princess",
    "cinderella": "glass slipper princess",
    "snow white": "fairest princess of all",
    "ariel": "undersea mermaid princess",
    "lightning mcqueen": "champion racing car",
    "ratatouille": "gourmet chef rat",
    "wall-e": "lonely cleanup robot",
    "baymax": "caring healthcare robot",
    "stitch": "mischievous alien creature",
    "tinker bell": "tiny fairy with sparkle dust",
    "mulan": "brave warrior maiden",
    "pocahontas": "nature-connected tribal princess",
    "jasmine": "desert kingdom princess",
    "belle": "book-loving beauty",
    "aurora": "sleeping enchanted princess",
    "tiana": "hardworking dreamer princess",
    "merida": "fearless archer princess",

    # ── Marvel ──
    "marvel": "cinematic action hero universe",
    "avengers": "elite superhero team",
    "the avengers": "elite superhero team",
    "spider-man": "web-slinging masked hero",
    "spiderman": "web-slinging masked hero",
    "iron man": "genius armored hero",
    "ironman": "genius armored hero",
    "captain america": "shield-wielding patriot hero",
    "thor": "thunder god warrior",
    "hulk": "gamma-powered green giant",
    "the hulk": "gamma-powered green giant",
    "black widow": "elite spy operative",
    "hawkeye": "master archer agent",
    "black panther": "vibranium-powered king",
    "thanos": "cosmic titan villain",
    "wolverine": "metal-clawed mutant fighter",
    "deadpool": "wisecracking mercenary anti-hero",
    "doctor strange": "mystical sorcerer supreme",
    "scarlet witch": "reality-warping sorceress",
    "vision": "synthetic android hero",
    "ant-man": "size-shifting micro hero",
    "wasp": "winged size-shifting heroine",
    "shang-chi": "legendary martial arts master",
    "moon knight": "moonlit vigilante warrior",
    "groot": "tree-like gentle giant",
    "rocket raccoon": "tech-savvy raccoon pilot",
    "x-men": "mutant hero squad",

    # ── DC Comics ──
    "dc comics": "legendary comic hero universe",
    "batman": "dark caped crusader",
    "superman": "invincible flying hero",
    "wonder woman": "Amazonian warrior princess",
    "justice league": "legendary hero alliance",
    "the flash": "lightning-fast speedster hero",
    "flash": "lightning-fast speedster hero",
    "aquaman": "ruler of the underwater kingdom",
    "green lantern": "ring-powered cosmic guardian",
    "harley quinn": "chaotic jester anti-heroine",
    "joker": "maniacal clown villain",
    "catwoman": "stealthy feline thief",
    "robin": "young masked sidekick",
    "cyborg": "half-human tech warrior",
    "batgirl": "masked vigilante heroine",

    # ── Anime / Manga ──
    "naruto": "ninja warrior with hidden power",
    "goku": "legendary martial arts warrior",
    "luffy": "stretchy pirate captain",
    "pikachu": "electric creature companion",
    "pokemon": "creature battle world",
    "sailor moon": "magical girl guardian",
    "vegeta": "proud warrior prince",
    "sasuke": "rival ninja prodigy",
    "kakashi": "masked ninja mentor",
    "sakura haruno": "powerful ninja healer",
    "itachi": "mysterious ninja genius",
    "light yagami": "genius with a dark notebook",
    "eren jaeger": "titan-shifting freedom fighter",
    "mikasa": "elite blade warrior",
    "levi ackerman": "humanity's strongest soldier",
    "saitama": "unbeatable bald hero",
    "deku": "underdog hero with growing power",
    "todoroki": "dual-element powered hero",
    "bakugo": "explosive temper young hero",
    "all might": "symbol of peace champion",
    "ash ketchum": "creature trainer adventurer",
    "totoro": "gentle forest spirit creature",
    "spirited away": "mystical spirit world journey",
    "attack on titan": "giant monster siege story",
    "demon slayer": "blade-wielding demon hunter",

    # ── Other Major IP ──
    "harry potter": "young wizard hero",
    "hogwarts": "legendary school of magic",
    "hermione": "brilliant witch prodigy",
    "dumbledore": "wise headmaster wizard",
    "voldemort": "dark lord sorcerer",
    "gandalf": "legendary wandering wizard",
    "frodo": "brave ring-bearing hobbit",
    "aragorn": "exiled king returning to throne",
    "legolas": "elven archer of the forest",
    "sauron": "dark overlord of shadow",
    "lord of the rings": "epic quest to destroy a dark artifact",
    "star wars": "galactic space saga",
    "darth vader": "dark armored space knight",
    "luke skywalker": "young galactic hero",
    "yoda": "ancient wise green master",
    "obi-wan": "noble space knight mentor",
    "obi-wan kenobi": "noble space knight mentor",
    "palpatine": "sinister galactic emperor",
    "shrek": "lovable green ogre",
    "spongebob": "cheerful sea sponge character",
    "bugs bunny": "wisecracking cartoon rabbit",
    "paw patrol": "heroic rescue pup team",
    "peppa pig": "cheerful cartoon piglet",
    "bluey": "playful cartoon puppy",
    "cocomelon": "children's nursery show",
    "mario": "mustached plumber adventurer",
    "luigi": "tall green plumber sidekick",
    "link": "courageous elven swordsman",
    "zelda": "wise kingdom princess",
    "sonic": "super-fast blue hedgehog hero",
    "mega man": "robotic action hero",
    "winnie the pooh": "honey-loving stuffed bear",
    "thomas the tank engine": "friendly blue locomotive",
    "hello kitty": "cute bow-wearing kitten",
    "doraemon": "gadget-carrying robot cat",

    # ── Celebrities ──
    "taylor swift": "chart-topping pop artist",
    "beyonce": "iconic R&B diva",
    "beyoncé": "iconic R&B diva",
    "drake": "hip-hop hitmaker",
    "kanye west": "controversial music mogul",
    "kim kardashian": "reality TV media mogul",
    "elon musk": "tech industry visionary",
    "donald trump": "prominent political figure",
    "joe biden": "senior political leader",
    "barack obama": "former national leader",
    "vladimir putin": "powerful national leader",
    "cristiano ronaldo": "legendary football striker",
    "lionel messi": "magical football genius",
    "lebron james": "dominant basketball legend",
    "oprah winfrey": "iconic talk show host",
    "jeff bezos": "e-commerce billionaire",
    "mark zuckerberg": "social media founder",
    "bill gates": "software industry pioneer",
}

# ── Precompiled patterns for efficient matching ──
# Sort by length descending so longer terms match first (e.g., "spider-man" before "man")
_SORTED_TERMS: List[Tuple[str, str, re.Pattern]] = []


def _build_patterns():
    """Build precompiled regex patterns sorted by term length (longest first)."""
    global _SORTED_TERMS
    _SORTED_TERMS = []
    for term, replacement in sorted(REPLACEMENTS.items(), key=lambda x: -len(x[0])):
        # Build pattern that handles hyphens and spaces interchangeably
        # e.g., "spider-man" matches "spider man", "spider-man", "spiderman"
        escaped = re.escape(term)
        # Allow optional hyphens/spaces between word parts
        flexible = escaped.replace(r"\-", r"[-\s]?").replace(r"\ ", r"[-\s]+")
        # Whole-word boundary matching
        pattern = re.compile(r"(?<![a-zA-Z])" + flexible + r"(?![a-zA-Z])", re.IGNORECASE)
        _SORTED_TERMS.append((term, replacement, pattern))


_build_patterns()


def rewrite_text(text: str) -> Tuple[str, List[Dict]]:
    """
    Rewrite risky terms in text with safe generic equivalents.
    Returns (rewritten_text, list_of_changes).
    Each change: {"original": str, "replacement": str, "position": int}
    """
    if not text:
        return text, []

    changes = []
    result = text

    for term, replacement, pattern in _SORTED_TERMS:
        match = pattern.search(result)
        if match:
            original_match = match.group(0)
            result = pattern.sub(replacement, result)
            changes.append({
                "original": original_match,
                "replacement": replacement,
            })

    return result, changes


def has_risky_terms(text: str) -> bool:
    """Quick check if text contains any risky terms (without rewriting)."""
    if not text:
        return False
    for _, _, pattern in _SORTED_TERMS:
        if pattern.search(text):
            return True
    return False
