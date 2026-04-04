"""
Deterministic Fallback Service
Guaranteed output when all AI providers fail.
No AI calls — pure template logic.
"""
import random
import logging

logger = logging.getLogger("viral.fallback")

HOOK_TEMPLATES = [
    "You won't believe what happens when you try {topic}",
    "I tried {topic} for 30 days — here's what changed",
    "Nobody talks about this {niche} secret",
    "The {niche} hack that changed everything for me",
    "Stop scrolling — this {topic} tip will save you hours",
    "Why everyone is wrong about {topic}",
    "I spent $0 on {topic} and got insane results",
    "The truth about {topic} nobody wants to hear",
]

SCRIPT_TEMPLATE = """# {hook}

## Opening (0-3s)
{hook}

## Problem (3-10s)
Most people struggle with {topic} because they're doing it wrong.
Here's what actually works...

## Solution (10-25s)
The key is to focus on what matters:
1. Start with the basics — don't overcomplicate {topic}
2. Be consistent — results come from daily effort
3. Track your progress — what gets measured gets improved

## Payoff (25-40s)
When I applied this to {topic}, everything changed.
The results speak for themselves.

## Call to Action (40-45s)
Follow for more {niche} content that actually works.
Drop a comment if this helped you!
"""

CAPTION_TEMPLATES = {
    "instagram": "The {niche} hack nobody talks about 👀 Save this for later!\n\n#viral #trending #{niche_tag} #fyp #contentcreator",
    "tiktok": "{hook} 🔥 Full breakdown in the video!\n\n#{niche_tag} #viral #trending #fyp #foryou",
    "twitter": "{hook}\n\nThread 🧵👇",
    "youtube_short": "{hook} | {niche} Tips That Actually Work",
    "linkedin": "I discovered something about {topic} that changed my perspective.\n\nHere's what I learned:\n\n{hook}\n\n#professional #{niche_tag}",
}


def generate_fallback_hooks(idea: str, niche: str, count: int = 3) -> list[str]:
    topic = idea.lower().rstrip(".")
    hooks = []
    templates = random.sample(HOOK_TEMPLATES, min(count, len(HOOK_TEMPLATES)))
    for tpl in templates:
        hooks.append(tpl.format(topic=topic, niche=niche.lower()))
    logger.info(f"[FALLBACK] Generated {len(hooks)} fallback hooks")
    return hooks


def generate_fallback_script(idea: str, niche: str, hook: str = None) -> str:
    topic = idea.lower().rstrip(".")
    if not hook:
        hook = HOOK_TEMPLATES[0].format(topic=topic, niche=niche.lower())
    script = SCRIPT_TEMPLATE.format(hook=hook, topic=topic, niche=niche.lower())
    logger.info("[FALLBACK] Generated fallback script")
    return script


def generate_fallback_captions(idea: str, niche: str, hook: str = None) -> dict:
    topic = idea.lower().rstrip(".")
    niche_tag = niche.lower().replace(" ", "")
    if not hook:
        hook = HOOK_TEMPLATES[0].format(topic=topic, niche=niche.lower())
    captions = {}
    for platform, tpl in CAPTION_TEMPLATES.items():
        captions[platform] = tpl.format(
            hook=hook, topic=topic, niche=niche, niche_tag=niche_tag
        )
    logger.info("[FALLBACK] Generated fallback captions")
    return captions


def generate_fallback_thumbnail_html(idea: str, niche: str) -> str:
    """Returns HTML that can be rendered to a PNG via a headless browser or used as-is."""
    colors = {
        "Tech": ("#0f172a", "#38bdf8"), "Finance": ("#0f172a", "#4ade80"),
        "Fitness": ("#1a0a0a", "#f87171"), "Food": ("#1a1400", "#fbbf24"),
        "Travel": ("#0f0720", "#c084fc"), "Fashion": ("#1a0a14", "#fb7185"),
        "Gaming": ("#0a0a1f", "#818cf8"), "Education": ("#051414", "#2dd4bf"),
        "Business": ("#111111", "#94a3b8"), "Lifestyle": ("#1a1400", "#fbbf24"),
        "Health": ("#051a0a", "#4ade80"), "Entertainment": ("#1a0a1a", "#e879f9"),
    }
    bg, accent = colors.get(niche, ("#0f172a", "#f97316"))
    title = idea[:60] + ("..." if len(idea) > 60 else "")
    return f"""<div style="width:1080px;height:1080px;background:{bg};display:flex;flex-direction:column;justify-content:center;align-items:center;padding:80px;font-family:sans-serif;">
  <div style="color:{accent};font-size:24px;text-transform:uppercase;letter-spacing:4px;margin-bottom:40px;">{niche}</div>
  <div style="color:white;font-size:56px;font-weight:bold;text-align:center;line-height:1.2;">{title}</div>
  <div style="color:{accent};font-size:20px;margin-top:40px;">Swipe to learn more →</div>
</div>"""
