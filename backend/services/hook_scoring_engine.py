"""
Hybrid Hook Scoring Engine
Stage 1: Rule-based filter (fast, free) → Score 0-100, Tag LOW/MEDIUM/HIGH
Stage 2: GPT scoring (only top 30%) → Detailed curiosity/emotion/viral/continuation scores
Stage 3: Final decision → Only score >= 70 goes to video generation
"""

import re
import logging
import os
from typing import Optional

logger = logging.getLogger("hook_scoring")

# ═══════════════════════════════════════════════════════════════
# STAGE 1: RULE-BASED FILTER (Fast + Free)
# ═══════════════════════════════════════════════════════════════

TENSION_WORDS = {
    "but", "however", "suddenly", "then", "except", "until",
    "yet", "although", "despite", "unfortunately", "instead",
    "never", "always", "impossible", "secret", "hidden",
    "forbidden", "dangerous", "mysterious", "vanished",
    "whispered", "screamed", "shattered", "betrayed",
}

CURIOSITY_TRIGGERS = {
    "?",  # questions
    "what if", "imagine", "nobody knew", "no one expected",
    "the truth", "little did", "they didn't know",
    "everything changed", "one day", "the last",
    "the only", "for the first time", "never before",
}

CLIFFHANGER_SIGNALS = {
    "...", "—", "but then", "and then", "to be continued",
    "what happened next", "she never saw", "he didn't know",
    "the door opened", "a voice said", "darkness fell",
    "everything went", "the ground shook", "eyes widened",
    "heart stopped", "too late", "no turning back",
}

GENERIC_PHRASES = {
    "once upon a time", "in a world where", "a young boy",
    "a young girl", "one fine day", "it was a dark and stormy",
    "happily ever after", "the end", "and they lived",
    "in a land far away", "long ago", "there was a",
}

EMOTIONAL_POWER_WORDS = {
    "love", "death", "fear", "lost", "alone", "broken",
    "heart", "tears", "scream", "hope", "dream", "desperate",
    "sacrifice", "betrayal", "forgive", "redemption",
    "courage", "destroyed", "haunted", "regret", "miracle",
}


def _count_matches(text: str, word_set: set) -> int:
    text_lower = text.lower()
    count = 0
    for word in word_set:
        if word in text_lower:
            count += 1
    return count


def rule_based_score(story_text: str, title: str = "") -> dict:
    """
    Fast rule-based scoring. Returns score 0-100 and detailed breakdown.
    """
    lines = [line.strip() for line in story_text.strip().split("\n") if line.strip()]
    words = story_text.split()
    word_count = len(words)

    score = 0
    breakdown = {}
    rejection_reasons = []

    # ── Length Check (0-15 points) ──
    # Ideal: 50-200 words (3-4 lines equivalent in story text)
    if 50 <= word_count <= 200:
        length_score = 15
    elif 30 <= word_count <= 300:
        length_score = 10
    elif word_count > 300:
        length_score = 5
    else:
        length_score = 0
        rejection_reasons.append("Too short (< 30 words)")
    breakdown["length"] = length_score
    score += length_score

    # ── First Line Hook (0-25 points) ──
    first_line = lines[0] if lines else ""
    first_line_lower = first_line.lower()
    hook_score = 0

    # Check for curiosity trigger in first line
    has_question = "?" in first_line
    has_curiosity = any(t in first_line_lower for t in CURIOSITY_TRIGGERS)
    has_tension_start = any(t in first_line_lower for t in TENSION_WORDS)
    has_emotion_start = any(w in first_line_lower for w in EMOTIONAL_POWER_WORDS)

    if has_question:
        hook_score += 10
    if has_curiosity:
        hook_score += 8
    if has_tension_start:
        hook_score += 5
    if has_emotion_start:
        hook_score += 5
    # First line should be punchy (< 20 words)
    first_words = len(first_line.split())
    if 3 <= first_words <= 15:
        hook_score += 5

    hook_score = min(hook_score, 25)
    if hook_score < 5:
        rejection_reasons.append("Weak opening — no hook in first line")
    breakdown["first_line_hook"] = hook_score
    score += hook_score

    # ── Tension & Conflict (0-20 points) ──
    tension_count = _count_matches(story_text, TENSION_WORDS)
    tension_score = min(tension_count * 4, 20)
    if tension_count == 0:
        rejection_reasons.append("No tension/conflict words found")
    breakdown["tension"] = tension_score
    score += tension_score

    # ── Cliffhanger Ending (0-25 points) ──
    last_two = " ".join(lines[-2:]) if len(lines) >= 2 else (lines[-1] if lines else "")
    cliff_count = _count_matches(last_two, CLIFFHANGER_SIGNALS)
    ends_with_ellipsis = story_text.rstrip().endswith("...")
    ends_with_dash = story_text.rstrip().endswith("—") or story_text.rstrip().endswith("--")
    ends_incomplete = not story_text.rstrip().endswith(".")

    cliff_score = 0
    if cliff_count > 0:
        cliff_score += min(cliff_count * 6, 15)
    if ends_with_ellipsis or ends_with_dash:
        cliff_score += 10
    elif ends_incomplete:
        cliff_score += 5

    cliff_score = min(cliff_score, 25)
    if cliff_score < 5:
        rejection_reasons.append("No cliffhanger — story resolves or ends flat")
    breakdown["cliffhanger"] = cliff_score
    score += cliff_score

    # ── Emotional Power (0-10 points) ──
    emotion_count = _count_matches(story_text, EMOTIONAL_POWER_WORDS)
    emotion_score = min(emotion_count * 3, 10)
    breakdown["emotional_power"] = emotion_score
    score += emotion_score

    # ── Generic Penalty (-15 points) ──
    generic_count = _count_matches(story_text, GENERIC_PHRASES)
    generic_penalty = min(generic_count * 5, 15)
    if generic_count > 0:
        rejection_reasons.append(f"Generic phrasing detected ({generic_count} instances)")
    breakdown["generic_penalty"] = -generic_penalty
    score -= generic_penalty

    # ── Title Quality (0-5 points) ──
    title_score = 0
    if title:
        title_words = len(title.split())
        if 2 <= title_words <= 8:
            title_score += 3
        title_tension = _count_matches(title, TENSION_WORDS | EMOTIONAL_POWER_WORDS)
        if title_tension > 0:
            title_score += 2
    breakdown["title_quality"] = title_score
    score += title_score

    # Clamp score
    score = max(0, min(100, score))

    # Determine tag
    if score >= 70:
        tag = "HIGH"
    elif score >= 40:
        tag = "MEDIUM"
    else:
        tag = "LOW"

    # Auto-reject conditions
    auto_reject = False
    if hook_score < 5 and cliff_score < 5:
        auto_reject = True
        rejection_reasons.insert(0, "AUTO-REJECT: No hook AND no cliffhanger")
    if word_count < 15:
        auto_reject = True
        rejection_reasons.insert(0, "AUTO-REJECT: Too short to be a story")

    return {
        "score": score,
        "tag": tag,
        "auto_reject": auto_reject,
        "breakdown": breakdown,
        "rejection_reasons": rejection_reasons,
        "word_count": word_count,
        "passes_rule_filter": score >= 40 and not auto_reject,
    }


# ═══════════════════════════════════════════════════════════════
# STAGE 2: GPT SCORING (Only for top candidates)
# ═══════════════════════════════════════════════════════════════

async def gpt_score(story_text: str, title: str = "") -> Optional[dict]:
    """
    GPT-based deep scoring. Only call for stories that passed rule filter.
    Returns detailed scoring on curiosity, emotion, viral potential, continuation probability.
    """
    try:
        from emergentintegrations.llm.chat import LlmChat, ChatMessage

        api_key = os.environ.get("EMERGENT_LLM_KEY")
        if not api_key:
            logger.warning("[HOOK_SCORING] No EMERGENT_LLM_KEY — skipping GPT scoring")
            return None

        chat = LlmChat(
            api_key=api_key,
            model="gpt-4o-mini",
            system_prompt="""You are a viral content scoring engine. You evaluate story hooks for their potential to go viral on social media and drive user engagement.

Score each dimension from 0-10. Be brutally honest. Most content is mediocre (4-6). Only truly exceptional hooks get 8+.

Respond ONLY with valid JSON, no other text.""",
        )

        prompt = f"""Score this story hook:

TITLE: {title}
STORY: {story_text}

Evaluate and respond with ONLY this JSON:
{{
  "hook_score": <0-100 overall>,
  "curiosity": <0-10 how much does it make you want to know more>,
  "emotion": <0-10 emotional impact strength>,
  "viral_potential": <0-10 would people share this>,
  "continuation_probability": <0-10 would someone click Continue>,
  "strengths": ["<strength 1>", "<strength 2>"],
  "weaknesses": ["<weakness 1>"],
  "one_line_verdict": "<brutal one-line assessment>"
}}"""

        response = await chat.send_message(ChatMessage(role="user", content=prompt))
        text = response.content.strip()

        # Parse JSON from response
        import json
        # Try to extract JSON from markdown code blocks
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()

        result = json.loads(text)

        # Validate fields
        required = ["hook_score", "curiosity", "emotion", "viral_potential", "continuation_probability"]
        for field in required:
            if field not in result:
                result[field] = 5

        # Clamp values
        for field in required:
            if field == "hook_score":
                result[field] = max(0, min(100, int(result[field])))
            else:
                result[field] = max(0, min(10, int(result[field])))

        return result

    except Exception as e:
        logger.error(f"[HOOK_SCORING] GPT scoring failed: {e}")
        return None


# ═══════════════════════════════════════════════════════════════
# STAGE 3: HYBRID ORCHESTRATOR
# ═══════════════════════════════════════════════════════════════

PUBLISH_THRESHOLD = 70  # Only stories scoring >= 70 go to video generation


async def score_story(story_text: str, title: str = "", skip_gpt: bool = False) -> dict:
    """
    Full hybrid scoring pipeline:
    1. Rule-based filter (instant, free)
    2. GPT scoring (only if rules pass, costs money)
    3. Final decision (combined score)
    """
    # Stage 1: Rule-based
    rules = rule_based_score(story_text, title)

    result = {
        "rule_score": rules["score"],
        "rule_tag": rules["tag"],
        "rule_breakdown": rules["breakdown"],
        "rejection_reasons": rules["rejection_reasons"],
        "auto_reject": rules["auto_reject"],
        "word_count": rules["word_count"],
        "gpt_score": None,
        "final_score": rules["score"],
        "final_tag": rules["tag"],
        "ready_for_video": False,
        "scoring_stages": ["rules"],
    }

    # Stage 2: GPT scoring (only for top candidates that passed rules)
    if rules["passes_rule_filter"] and not skip_gpt:
        gpt = await gpt_score(story_text, title)
        if gpt:
            result["gpt_score"] = gpt
            result["scoring_stages"].append("gpt")

            # Combine scores: 40% rule + 60% GPT (GPT is more reliable for quality)
            combined = int(rules["score"] * 0.4 + gpt["hook_score"] * 0.6)
            result["final_score"] = combined

            if combined >= 70:
                result["final_tag"] = "HIGH"
            elif combined >= 40:
                result["final_tag"] = "MEDIUM"
            else:
                result["final_tag"] = "LOW"

    # Stage 3: Final decision
    result["ready_for_video"] = (
        result["final_score"] >= PUBLISH_THRESHOLD
        and not result["auto_reject"]
    )

    return result
