"""
Brand Kit — Prompt templates for all artifact types.
Each prompt returns structured JSON from the LLM.
"""

SYSTEM_PROMPT = """You are a world-class brand strategist, copywriter, and positioning expert.
Your job is to create original, commercially useful, high-quality brand assets based on the provided brand brief.
Rules:
- Be specific, vivid, and modern.
- Avoid generic corporate filler.
- Do not copy slogans or phrasing from known brands.
- Match the requested tone, audience, and industry.
- Keep outputs globally appealing unless a local market is specified.
- Prefer clarity, memorability, and conversion.
- Return output strictly as valid JSON with no markdown fences."""


def brief_context(brief: dict) -> str:
    parts = [f"Business: {brief.get('business_name', 'Unknown')}"]
    if brief.get("industry"):
        parts.append(f"Industry: {brief['industry']}")
    if brief.get("mission"):
        parts.append(f"Mission: {brief['mission']}")
    if brief.get("founder_story"):
        parts.append(f"Founder Story: {brief['founder_story']}")
    if brief.get("audience"):
        parts.append(f"Target Audience: {brief['audience']}")
    if brief.get("market"):
        parts.append(f"Market/Geography: {brief['market']}")
    if brief.get("tone"):
        parts.append(f"Tone: {brief['tone']}")
    if brief.get("personality"):
        parts.append(f"Brand Personality: {brief['personality']}")
    if brief.get("competitors"):
        parts.append(f"Competitors: {brief['competitors']}")
    if brief.get("problem_solved"):
        parts.append(f"Core Problem Solved: {brief['problem_solved']}")
    return "\n".join(parts)


PROMPTS = {
    "short_brand_story": {
        "template": """Write a short brand story (80-120 words). Emotionally engaging, easy to understand, suitable for a homepage.

{context}

Return JSON: {{"short_brand_story": "..."}}""",
    },
    "long_brand_story": {
        "template": """Write a premium long-form brand story (250-400 words). Include founder journey, mission, and customer impact. Persuasive but authentic.

{context}

Return JSON: {{"long_brand_story": "..."}}""",
    },
    "mission_vision_values": {
        "template": """Create mission statement, vision statement, and 5 brand values. Concise, memorable, not generic.

{context}

Return JSON: {{"mission": "...", "vision": "...", "values": ["...", "...", "...", "...", "..."]}}""",
    },
    "taglines": {
        "template": """Generate 15 original tagline options (3-8 words each). Mix of premium, emotional, direct, and modern styles. Make them commercially usable.

{context}

Return JSON: {{"taglines": [{{"text": "...", "style": "premium"}}, ...]}}""",
    },
    "elevator_pitch": {
        "template": """Write 3 elevator pitch versions: one sentence, 30 seconds, and 60 seconds.

{context}

Return JSON: {{"one_line": "...", "thirty_sec": "...", "sixty_sec": "..."}}""",
    },
    "website_hero": {
        "template": """Generate website hero copy: headline, subheadline, CTA button text, and 3 trust bullets.

{context}

Return JSON: {{"headline": "...", "subheadline": "...", "cta": "...", "trust_bullets": ["...", "...", "..."]}}""",
    },
    "social_ad_copy": {
        "template": """Generate social ad copy: 5 Instagram captions, 3 Facebook ad variants, 3 Google ad headline sets, 5 CTA lines.

{context}

Return JSON: {{"instagram": ["..."], "facebook": ["..."], "google_ads": ["..."], "cta_lines": ["..."]}}""",
    },
    "color_palettes": {
        "template": """Recommend 3 brand color palette directions. For each: palette name, primary hex, secondary hex, accent hex, background hex, emotional meaning.

{context}

Return JSON: {{"palettes": [{{"name": "...", "primary": "#...", "secondary": "#...", "accent": "#...", "background": "#...", "meaning": "..."}}, ...]}}""",
    },
    "typography": {
        "template": """Suggest 3 typography pairings. For each: heading font style, body font style, personality fit, where to use. Use generic font family descriptions.

{context}

Return JSON: {{"pairings": [{{"name": "...", "heading": "...", "body": "...", "personality": "...", "use_case": "..."}}, ...]}}""",
    },
    "logo_concepts": {
        "template": """Create 6 logo concept directions. For each: concept name, symbol idea, layout idea, color logic, emotional feel, why it fits the brand.

{context}

Return JSON: {{"concepts": [{{"name": "...", "symbol": "...", "layout": "...", "color_logic": "...", "feel": "...", "rationale": "..."}}, ...]}}""",
    },
}

# Which artifacts belong to which mode
MODE_ARTIFACTS = {
    "fast": ["short_brand_story", "mission_vision_values", "taglines", "elevator_pitch"],
    "pro": ["short_brand_story", "long_brand_story", "mission_vision_values", "taglines",
            "elevator_pitch", "website_hero", "social_ad_copy", "color_palettes",
            "typography", "logo_concepts"],
}
