"""
Hook System — Core Engine
═════════════════════════
Generates, validates, rewrites, and evolves hooks for maximum addiction.

HOOK RULES:
- Max 12 words
- Must create curiosity gap
- Must feel incomplete
- Must NOT be a summary
- Must NOT start with "Once upon a time"
- Backend ONLY controls hook quality

A/B TESTING:
- 3 variants per story
- 80% best hook / 20% exploration (when not locked)
- Lock: ≥300 total impressions + ≥15% margin
- Evolution: every 100 impressions, drop worst, rewrite from best

HOOK SCORE:
  (0.6 × continue_rate) + (0.3 × share_rate) + (0.1 × completion_rate)

CONFIDENCE WEIGHTING:
  adjusted_score = raw_score × log(impressions + 1)
"""
import os
import math
import random
import logging
from datetime import datetime, timezone

logger = logging.getLogger("hook_service")

EMERGENT_KEY = os.environ.get("EMERGENT_LLM_KEY", "")

# ═══════════════════════════════════════════════════════════════
# CATEGORY-AWARE VIRAL TEMPLATES
# ═══════════════════════════════════════════════════════════════

HOOK_TEMPLATES = {
    "kids": [
        "Everyone laughed at him... until magic happened.",
        "The tiny dragon couldn't fly... until today.",
        "She found a secret friend... no one else could see.",
        "The toy soldier blinked... when nobody was watching.",
        "Something in the garden started glowing at midnight.",
    ],
    "horror": [
        "The mirror moved... but he didn't.",
        "Something was under the bed... breathing.",
        "The voice knew his name... but no one was there.",
        "The door opened by itself... again.",
        "She smiled... but her reflection didn't.",
    ],
    "mystery": [
        "The letter arrived... ten years too late.",
        "Everyone in the photo was dead... except one.",
        "The detective noticed what nobody else could see.",
        "The last message said only three words.",
        "Someone was watching... from the inside.",
    ],
    "reels": [
        "Wait till you see what happens next...",
        "This changed everything in five seconds.",
        "No one expected this ending...",
        "The last frame will break your brain.",
        "You'll want to watch this twice.",
    ],
    "emotional": [
        "He waited... but she never came.",
        "The letter arrived... ten years too late.",
        "They met again... but nothing was the same.",
        "She whispered goodbye... but he couldn't hear.",
        "The empty chair at dinner said everything.",
    ],
    "default": [
        "Everything changed... in one heartbeat.",
        "They told him it was impossible...",
        "She opened the box... and time stopped.",
        "The truth was hiding in plain sight.",
        "Nobody noticed... until it was too late.",
    ],
}

# ═══════════════════════════════════════════════════════════════
# WEAK HOOK DETECTION (RULE-BASED)
# ═══════════════════════════════════════════════════════════════

GENERIC_OPENERS = {
    "once upon a time", "in a world where", "there was a",
    "a young boy", "a young girl", "long ago", "one fine day",
    "it was a dark", "in a land far", "this is the story",
}

CURIOSITY_TRIGGERS = {
    "but", "until", "except", "never", "nobody", "suddenly",
    "secret", "hidden", "impossible", "vanished", "whispered",
    "...", "—", "?",
}


def is_weak_hook(text: str) -> bool:
    """Return True if hook fails quality bar."""
    if not text or not text.strip():
        return True
    text = text.strip()
    words = text.split()

    # Too long
    if len(words) > 12:
        return True

    # Contains full explanation (multiple sentences)
    sentences = [s.strip() for s in text.replace("...", "|||").split(".") if s.strip()]
    if len(sentences) > 2:
        return True

    # Generic opener
    text_lower = text.lower()
    for phrase in GENERIC_OPENERS:
        if text_lower.startswith(phrase):
            return True

    # No curiosity trigger
    has_trigger = any(t in text_lower for t in CURIOSITY_TRIGGERS)
    if not has_trigger:
        return True

    return False


def predict_hook_score(text: str) -> int:
    """Rule-based pre-screen. Score 0-5. Reject if < 2."""
    if not text:
        return 0
    text_lower = text.lower().strip()
    words = text_lower.split()
    score = 0

    # Length sweet spot (5-10 words)
    if 5 <= len(words) <= 10:
        score += 1
    elif len(words) <= 12:
        score += 0  # acceptable but not ideal

    # Curiosity gap present
    if any(t in text_lower for t in CURIOSITY_TRIGGERS):
        score += 2

    # Emotional/mystery words
    emotion_words = {"fear", "love", "death", "secret", "dark", "lost", "alone", "silence", "scream", "heart", "shadow", "blood", "dream", "broken"}
    if any(w in text_lower for w in emotion_words):
        score += 1

    # Ends with incompleteness
    if text.rstrip().endswith("...") or text.rstrip().endswith("—"):
        score += 1

    # Penalty for generic
    for phrase in GENERIC_OPENERS:
        if phrase in text_lower:
            score -= 2

    return max(0, min(5, score))


# ═══════════════════════════════════════════════════════════════
# HOOK GENERATION (LLM)
# ═══════════════════════════════════════════════════════════════

def _get_category(style_id: str, age_group: str = "") -> str:
    """Map style_id / age_group to hook template category."""
    style_lower = (style_id or "").lower()
    age_lower = (age_group or "").lower()

    if age_lower in ("kids", "children", "toddlers"):
        return "kids"
    if "horror" in style_lower or "dark" in style_lower:
        return "horror"
    if "mystery" in style_lower or "detective" in style_lower:
        return "mystery"
    if "reel" in style_lower or "viral" in style_lower or "short" in style_lower:
        return "reels"
    if "emotion" in style_lower or "drama" in style_lower or "romance" in style_lower:
        return "emotional"
    return "default"


async def generate_hook_variants(
    story_prompt: str,
    title: str = "",
    style_id: str = "default",
    age_group: str = "",
    n: int = 3,
) -> list:
    """
    Generate N hook variants for a story. Uses LLM with category-aware templates.
    Each hook is validated and weak ones are auto-rewritten.
    Returns list of hook dicts: [{"id": "A", "text": "...", "impressions": 0, "continues": 0, "shares": 0, "completions": 0}]
    """
    category = _get_category(style_id, age_group)
    templates = HOOK_TEMPLATES.get(category, HOOK_TEMPLATES["default"])
    example_hooks = "\n".join(f"- {t}" for t in templates[:3])

    hooks = []

    if EMERGENT_KEY:
        try:
            from emergentintegrations.llm.chat import LlmChat, UserMessage

            llm = LlmChat(
                api_key=EMERGENT_KEY,
                session_id=f"hooks_{random.randint(1000,9999)}",
                system_message=(
                    "You are a viral hook generator. You create ultra-addictive, curiosity-gap hooks for stories. "
                    "Each hook must be max 12 words, create an irresistible need to know more, feel incomplete, "
                    "and NEVER summarize or explain the story. Return ONLY the hooks, one per line, nothing else."
                ),
            )
            llm = llm.with_model("openai", "gpt-4o-mini")
            llm = llm.with_params(temperature=0.95, max_tokens=200)

            prompt = (
                f"Generate {n} different ultra-addictive hooks for this story.\n\n"
                f"Title: {title}\n"
                f"Story: {story_prompt[:500]}\n"
                f"Category: {category}\n\n"
                f"Style examples:\n{example_hooks}\n\n"
                f"Rules:\n"
                f"- Max 12 words each\n"
                f"- Create curiosity gap\n"
                f"- Feel incomplete\n"
                f"- NO summaries\n"
                f"- Each hook must be DIFFERENT style (question, ellipsis, contrast)\n"
                f"- Return ONLY {n} hooks, one per line"
            )

            response = await llm.send_message(UserMessage(text=prompt))
            raw_lines = [line.strip().lstrip("-•*123456789. ").strip('"').strip("'") for line in response.strip().split("\n") if line.strip()]
            hooks = [item for item in raw_lines if 3 <= len(item.split()) <= 15 and len(item) > 5][:n]

        except Exception as e:
            logger.error(f"[HOOK] LLM generation failed: {e}")

    # Fallback: use category templates if LLM failed or insufficient
    while len(hooks) < n:
        remaining = [t for t in templates if t not in hooks]
        if remaining:
            hooks.append(random.choice(remaining))
        else:
            hooks.append(random.choice(HOOK_TEMPLATES["default"]))

    # Validate and rewrite weak hooks
    validated = []
    for i, text in enumerate(hooks[:n]):
        if is_weak_hook(text):
            rewritten = await rewrite_hook(text, story_prompt, title)
            text = rewritten if rewritten and not is_weak_hook(rewritten) else text
            # If still weak after rewrite, use template
            if is_weak_hook(text):
                text = random.choice(templates)

        hook_id = chr(65 + i)  # A, B, C
        validated.append({
            "id": hook_id,
            "text": text,
            "impressions": 0,
            "continues": 0,
            "shares": 0,
            "completions": 0,
        })

    return validated


async def rewrite_hook(text: str, story_prompt: str = "", title: str = "") -> str:
    """Rewrite a weak hook using LLM. Uses best hook context when available."""
    if not EMERGENT_KEY:
        return text

    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage

        llm = LlmChat(
            api_key=EMERGENT_KEY,
            session_id=f"rewrite_{random.randint(1000,9999)}",
            system_message="You rewrite story hooks to be sharper, more mysterious, and more addictive. Max 12 words. Return ONLY the improved hook, nothing else.",
        )
        llm = llm.with_model("openai", "gpt-4o-mini")
        llm = llm.with_params(temperature=0.9, max_tokens=60)

        prompt = (
            f"Rewrite this into a stronger addictive hook.\n"
            f"Current hook: {text}\n"
            f"Story context: {story_prompt[:200]}\n"
            f"Title: {title}\n\n"
            f"Rules: Max 12 words. Increase curiosity. Make it sharper and more mysterious.\n"
            f"Return ONLY the improved hook."
        )

        response = await llm.send_message(UserMessage(text=prompt))
        result = response.strip().strip('"').strip("'").strip()
        return result if result and len(result.split()) <= 15 else text

    except Exception as e:
        logger.error(f"[HOOK] Rewrite failed: {e}")
        return text


async def evolve_hook_from_best(best_hook: str, story_prompt: str = "", title: str = "") -> str:
    """Generate a new hook variant evolved from the best-performing hook. Used during evolution cycles."""
    if not EMERGENT_KEY:
        return best_hook

    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage

        llm = LlmChat(
            api_key=EMERGENT_KEY,
            session_id=f"evolve_{random.randint(1000,9999)}",
            system_message="You evolve story hooks. Given a high-performing hook, create a new variant that keeps the same energy but explores a different angle. Max 12 words. Return ONLY the new hook.",
        )
        llm = llm.with_model("openai", "gpt-4o-mini")
        llm = llm.with_params(temperature=0.95, max_tokens=60)

        prompt = (
            f"This hook performed well: \"{best_hook}\"\n"
            f"Story: {story_prompt[:200]}\n"
            f"Title: {title}\n\n"
            f"Create a NEW hook variant that:\n"
            f"- Keeps the same addictive energy\n"
            f"- Explores a different angle or emotion\n"
            f"- Max 12 words\n"
            f"Return ONLY the new hook."
        )

        response = await llm.send_message(UserMessage(text=prompt))
        result = response.strip().strip('"').strip("'").strip()
        return result if result and len(result.split()) <= 15 else best_hook

    except Exception as e:
        logger.error(f"[HOOK] Evolution failed: {e}")
        return best_hook


# ═══════════════════════════════════════════════════════════════
# A/B TESTING ENGINE
# ═══════════════════════════════════════════════════════════════

MIN_IMPRESSIONS_TO_LOCK = 300
WINNER_MARGIN = 0.15
EVOLUTION_INTERVAL = 100
EXPLORATION_RATE = 0.20


def _hook_raw_score(hook: dict) -> float:
    """Raw hook quality score: (0.6 × continue_rate) + (0.3 × share_rate) + (0.1 × completion_rate)"""
    impressions = hook.get("impressions", 0)
    if impressions == 0:
        return 0.0
    continue_rate = hook.get("continues", 0) / impressions
    share_rate = hook.get("shares", 0) / impressions
    completion_rate = hook.get("completions", 0) / impressions
    return 0.6 * continue_rate + 0.3 * share_rate + 0.1 * completion_rate


def _hook_confidence_score(hook: dict) -> float:
    """Confidence-weighted score: raw_score × log(impressions + 1)"""
    raw = _hook_raw_score(hook)
    impressions = hook.get("impressions", 0)
    return raw * math.log(impressions + 1)


def select_hook_for_user(hooks: list, hook_locked: bool, winning_hook_id: str = None) -> dict:
    """
    Select which hook to serve to a user.
    - If locked: serve winner
    - If not locked: 80% best, 20% random exploration
    """
    if not hooks:
        return None

    # Locked: serve winner
    if hook_locked and winning_hook_id:
        for h in hooks:
            if h["id"] == winning_hook_id:
                return h

    # Not locked: exploration vs exploitation
    if random.random() < EXPLORATION_RATE:
        # Exploration: serve random
        return random.choice(hooks)
    else:
        # Exploitation: serve best by confidence score
        best = max(hooks, key=_hook_confidence_score)
        return best


def check_lock_condition(hooks: list) -> tuple:
    """
    Check if hooks should be locked.
    Lock conditions:
    1. Total impressions across all variants ≥ 300
    2. Minimum 3 variants tested (or all available)
    3. Best hook outperforms second best by ≥ 15%

    Returns (should_lock: bool, winner_id: str | None)
    """
    if not hooks or len(hooks) < 2:
        return False, None

    total_impressions = sum(h.get("impressions", 0) for h in hooks)
    if total_impressions < MIN_IMPRESSIONS_TO_LOCK:
        return False, None

    # Need at least 2 hooks with data
    hooks_with_data = [h for h in hooks if h.get("impressions", 0) > 0]
    if len(hooks_with_data) < 2:
        return False, None

    # Sort by confidence score
    scored = sorted(hooks_with_data, key=_hook_confidence_score, reverse=True)
    best = scored[0]
    second = scored[1]

    best_raw = _hook_raw_score(best)
    second_raw = _hook_raw_score(second)

    # Winner must outperform by ≥ 15%
    if second_raw > 0:
        margin = (best_raw - second_raw) / second_raw
    else:
        margin = 1.0 if best_raw > 0 else 0.0

    if margin >= WINNER_MARGIN:
        return True, best["id"]

    return False, None


def check_evolution_needed(hooks: list) -> bool:
    """Check if evolution cycle should run (every 100 impressions on any hook)."""
    for h in hooks:
        if h.get("impressions", 0) > 0 and h["impressions"] % EVOLUTION_INTERVAL == 0:
            return True
    return False


def get_evolution_targets(hooks: list) -> tuple:
    """Return (worst_hook, best_hook) for evolution cycle."""
    if len(hooks) < 2:
        return None, None

    hooks_with_data = [h for h in hooks if h.get("impressions", 0) > 10]
    if len(hooks_with_data) < 2:
        return None, None

    scored = sorted(hooks_with_data, key=_hook_confidence_score)
    return scored[0], scored[-1]  # worst, best


def compute_hook_strength(hooks: list, hook_locked: bool, winning_hook_id: str = None) -> float:
    """
    Compute the hook_strength_score for story ranking.
    Uses the winning hook if locked, otherwise best performing.
    Returns 0.0-1.0
    """
    if not hooks:
        return 0.0

    if hook_locked and winning_hook_id:
        target = next((h for h in hooks if h["id"] == winning_hook_id), None)
        if target and target.get("impressions", 0) > 0:
            return min(1.0, _hook_raw_score(target))

    # Use confidence-weighted best
    hooks_with_data = [h for h in hooks if h.get("impressions", 0) > 0]
    if not hooks_with_data:
        return 0.0

    best = max(hooks_with_data, key=_hook_confidence_score)
    return min(1.0, _hook_raw_score(best))
