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
    "disney": "a whimsical animated kingdom",
    "pixar": "a vibrant CGI-animated world",
    "frozen": "a wintry tale of courage and magic",
    "lion king": "a young cub's journey to reclaim his homeland",
    "the lion king": "a young cub's journey to reclaim his homeland",
    "little mermaid": "a sea-dwelling girl who longs for the surface world",
    "the little mermaid": "a sea-dwelling girl who longs for the surface world",
    "finding nemo": "a parent's desperate ocean voyage to rescue a lost child",
    "toy story": "a secret world where playthings have lives of their own",
    "moana": "a bold islander who sails into the unknown",

    # ── Disney / Pixar Characters ──
    "mickey mouse": "a cheerful cartoon rodent mascot",
    "minnie mouse": "a polka-dotted cartoon rodent companion",
    "donald duck": "a short-tempered cartoon waterfowl",
    "goofy": "a clumsy, loveable cartoon hound",
    "elsa": "a regal maiden who commands winter storms",
    "anna": "a fearless younger sister on a rescue mission",
    "simba": "a lion cub destined to rule the savanna",
    "mufasa": "a noble lion patriarch",
    "nemo": "a small striped fish separated from his family",
    "dory": "a forgetful blue tang on a heartfelt journey",
    "woody": "a devoted cowboy figure and natural-born leader",
    "buzz lightyear": "a deluded space ranger action figure",
    "rapunzel": "a sheltered girl with impossibly long golden hair",
    "cinderella": "a mistreated maiden transformed for one magical night",
    "snow white": "a kind-hearted maiden sheltered by forest dwarves",
    "ariel": "a curious mer-girl fascinated by the world above the waves",
    "lightning mcqueen": "a brash racing vehicle learning humility",
    "ratatouille": "a culinary-obsessed rodent in a Parisian kitchen",
    "wall-e": "a solitary maintenance automaton on an abandoned planet",
    "baymax": "a rotund inflatable caregiving android",
    "stitch": "a chaotic alien experiment masquerading as a pet",
    "tinker bell": "a diminutive winged craftsperson",
    "mulan": "a young woman who disguises herself to fight in her father's place",
    "pocahontas": "a chieftain's daughter bridging two clashing worlds",
    "jasmine": "a restless royal longing for freedom beyond palace walls",
    "belle": "an avid reader who befriends a cursed recluse",
    "aurora": "a princess cursed to endless slumber",
    "tiana": "a determined cook chasing her dream restaurant",
    "merida": "a headstrong highland archer defying tradition",

    # ── Marvel ──
    "marvel": "a sprawling universe of costumed champions",
    "avengers": "an elite alliance of extraordinary defenders",
    "the avengers": "an elite alliance of extraordinary defenders",
    "spider-man": "a nimble acrobatic vigilante who patrols city rooftops",
    "spiderman": "a nimble acrobatic vigilante who patrols city rooftops",
    "iron man": "a tech-genius billionaire in self-built power armor",
    "ironman": "a tech-genius billionaire in self-built power armor",
    "captain america": "a super-soldier champion carrying a legendary shield",
    "thor": "a boisterous god of storms wielding an enchanted hammer",
    "hulk": "a mild scientist who transforms into a colossal green brute",
    "the hulk": "a mild scientist who transforms into a colossal green brute",
    "black widow": "a reformed espionage agent turned hero",
    "hawkeye": "a peerless marksman and tactical operative",
    "black panther": "a king empowered by a rare mystical metal",
    "thanos": "a fanatical cosmic warlord obsessed with balance",
    "wolverine": "a gruff, near-immortal fighter with retractable metal claws",
    "deadpool": "a wisecracking, self-healing rogue operative",
    "doctor strange": "a former surgeon turned master of arcane dimensions",
    "scarlet witch": "a tormented sorceress who reshapes reality",
    "vision": "a sentient android striving to understand humanity",
    "ant-man": "an unlikely hero who manipulates his own size",
    "wasp": "a winged partner who shrinks and strikes with precision",
    "shang-chi": "a martial artist heir breaking free of a shadowy dynasty",
    "moon knight": "a vigilante channeling a deity of the night sky",
    "groot": "a towering plant being of few words",
    "rocket raccoon": "a sharp-tongued, gadget-obsessed critter",
    "x-men": "a band of persecuted super-powered outcasts",

    # ── DC Comics ──
    "dc comics": "a storied universe of masked champions and villains",
    "batman": "a brooding billionaire who wages a one-man war on crime",
    "superman": "an alien raised on earth with near-limitless strength",
    "wonder woman": "an immortal warrior princess from a hidden island",
    "justice league": "an alliance of the world's mightiest protectors",
    "the flash": "a forensic scientist gifted with impossible speed",
    "flash": "a forensic scientist gifted with impossible speed",
    "aquaman": "a half-human monarch ruling the undersea realms",
    "green lantern": "a pilot granted a cosmic ring of limitless will",
    "harley quinn": "a former psychologist turned gleeful anarchist",
    "joker": "a deranged criminal mastermind with a painted grin",
    "catwoman": "a morally grey cat burglar prowling city rooftops",
    "robin": "a young acrobat apprenticed to a dark vigilante",
    "cyborg": "a college athlete rebuilt with experimental technology",
    "batgirl": "a resourceful hacker who fights crime in a cowl",

    # ── Anime / Manga ──
    "naruto": "a determined orphan ninja striving to earn his village's respect",
    "goku": "an ever-evolving martial artist who thrives on impossible challenges",
    "luffy": "a rubbery-limbed sea captain chasing the ultimate treasure",
    "pikachu": "a small, spark-charged creature and steadfast companion",
    "pokemon": "a world of collectible creatures trained for friendly combat",
    "sailor moon": "a schoolgirl who transforms into a cosmic guardian",
    "vegeta": "a prideful warrior prince forever chasing a rival's strength",
    "sasuke": "a brooding prodigy haunted by his clan's tragic fall",
    "kakashi": "a laid-back, one-eyed mentor hiding formidable skill",
    "sakura haruno": "a fierce healer who fights alongside her teammates",
    "itachi": "a mysterious genius carrying a burden of unspeakable sacrifice",
    "light yagami": "a brilliant student who acquires a supernatural instrument of judgment",
    "eren jaeger": "a rage-fueled youth who can transform into a towering giant",
    "mikasa": "a stoic, blade-wielding protector of unwavering loyalty",
    "levi ackerman": "a compact, lethal soldier feared as humanity's finest",
    "saitama": "a bald hero so powerful he defeats every foe in a single blow",
    "deku": "a powerless boy who inherits a legendary strength",
    "todoroki": "a conflicted youth wielding opposing elemental forces",
    "bakugo": "an explosive-tempered prodigy driven by fierce ambition",
    "all might": "a towering symbol of hope concealing a fading secret",
    "ash ketchum": "a spirited young trainer roaming the land with creature companions",
    "totoro": "a gentle, rotund forest guardian visible only to children",
    "spirited away": "a girl's surreal passage through a hidden spirit realm",
    "attack on titan": "humanity sheltering behind walls from colossal predators",
    "demon slayer": "a compassionate swordsman hunting fiends to save his cursed sibling",

    # ── Other Major IP ──
    "harry potter": "a determined young mage discovering his powers in a hidden academy",
    "hogwarts": "a secretive mountaintop school of arcane disciplines",
    "hermione": "a relentlessly studious young sorceress",
    "dumbledore": "a venerable, eccentric headmaster with deep secrets",
    "voldemort": "a dreaded dark sorcerer whose name inspires terror",
    "gandalf": "a tall, wandering conjurer who guides unlikely heroes",
    "frodo": "a reluctant halfling carrying a world-threatening burden",
    "aragorn": "a ranger of noble blood destined for a forgotten throne",
    "legolas": "a keen-eyed woodland archer of immortal grace",
    "sauron": "a disembodied overlord seeking dominion through a cursed artifact",
    "lord of the rings": "a desperate journey to unmake a corrupted relic of power",
    "star wars": "an intergalactic conflict between tyranny and rebellion",
    "darth vader": "a once-noble warrior consumed by a dark cosmic force",
    "luke skywalker": "a farm boy drawn into an ancient cosmic struggle",
    "yoda": "a diminutive elder of cryptic wisdom and immense power",
    "obi-wan": "a seasoned mentor and guardian of an ancient warrior code",
    "obi-wan kenobi": "a seasoned mentor and guardian of an ancient warrior code",
    "palpatine": "a scheming tyrant masquerading as a benevolent ruler",
    "shrek": "a grumpy swamp-dwelling ogre with a hidden heart of gold",
    "spongebob": "an irrepressibly cheerful undersea creature",
    "bugs bunny": "a wisecracking, carrot-loving cartoon trickster",
    "paw patrol": "a squad of resourceful rescue puppies",
    "peppa pig": "a curious little piglet exploring everyday adventures",
    "bluey": "an imaginative young pup and her patient family",
    "cocomelon": "a colorful nursery-rhyme animated series",
    "mario": "a stout, cap-wearing adventurer leaping through fantastical kingdoms",
    "luigi": "a taller, timid sidekick braving haunted mansions",
    "link": "a courageous, green-clad swordsman on a quest to rescue a kingdom",
    "zelda": "a wise ruler wielding sacred power against darkness",
    "sonic": "a blazingly fast blue critter racing to stop an evil inventor",
    "mega man": "a small combat android fighting a rogue scientist's robot army",
    "winnie the pooh": "a plump, honey-obsessed stuffed bear in a tranquil wood",
    "thomas the tank engine": "a plucky blue locomotive eager to prove himself",
    "hello kitty": "an iconic bow-wearing feline mascot",
    "doraemon": "a round, blue robot cat dispensing futuristic gadgets",

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
