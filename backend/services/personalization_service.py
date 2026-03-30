"""
Deterministic Homepage Personalization Service
───────────────────────────────────────────────
Pure math scoring — NO ML, NO embeddings, NO LLM recommenders.

STORY SCORE:
  (0.30 × category_affinity) + (0.20 × continue_rate) + (0.15 × completion_rate)
  + (0.10 × share_rate) + (0.10 × freshness_score) + (0.10 × momentum_score)
  + (0.05 × global_trending_score)

EVENT WEIGHTS:
  card_click=1  watch_start=2  continue_click=5  watch_complete=8
  share_click=10  generation_start=6  generation_complete=12

FEATURE SCORE:
  (0.50 × feature_affinity) + (0.25 × recent_usage) + (0.15 × success_rate)
  + (0.10 × monetization_priority)
"""
import logging
from datetime import datetime, timezone, timedelta

logger = logging.getLogger("personalization")

# ═══════════════════════════════════════════════════════════════
# EVENT WEIGHTS — continue_click > click, share highest non-gen
# ═══════════════════════════════════════════════════════════════
EVENT_WEIGHTS = {
    "card_click": 1,
    "click": 1,
    "impression": 0,
    "watch_start": 2,
    "continue_click": 5,
    "continue": 5,
    "watch_complete": 8,
    "share_click": 10,
    "share": 10,
    "generation_start": 6,
    "generate_click": 6,
    "generation_complete": 12,
    "creation_completed": 12,
}

# Decay multiplier — applied to all existing affinities before adding new signal
DECAY = 0.98

# Minimum events before personalization is enabled
COLD_START_THRESHOLD = 5

# Monetization priority per feature (static business config)
FEATURE_MONETIZATION_PRIORITY = {
    "story-video-studio": 1.0,
    "story-series": 0.9,
    "comic-storybook": 0.8,
    "reels": 0.85,
    "photo-to-comic": 0.7,
    "bedtime-stories": 0.75,
    "gif-maker": 0.6,
    "brand-story-builder": 0.65,
    "coloring-book": 0.5,
    "daily-viral-ideas": 0.4,
    "characters": 0.55,
}


def _empty_profile(user_id: str) -> dict:
    """Create a cold-start empty profile."""
    now = datetime.now(timezone.utc).isoformat()
    return {
        "user_id": user_id,
        "category_affinity": {},
        "feature_affinity": {},
        "behavior_metrics": {
            "total_clicks": 0,
            "total_continues": 0,
            "total_completions": 0,
            "total_starts": 0,
            "total_shares": 0,
            "total_views": 0,
            "continue_rate": 0.0,
            "completion_rate": 0.0,
            "share_rate": 0.0,
        },
        "recent_activity": [],
        "counts": {
            "total_events": 0,
            "last_updated": now,
        },
        "created_at": now,
        "updated_at": now,
    }


async def get_or_create_profile(db, user_id: str) -> dict:
    """Fetch user_homepage_profile or create a cold-start one."""
    profile = await db.user_homepage_profile.find_one(
        {"user_id": user_id}, {"_id": 0}
    )
    if not profile:
        profile = _empty_profile(user_id)
        await db.user_homepage_profile.insert_one({**profile})
    return profile


async def update_profile_on_event(db, user_id: str, event: str, meta: dict):
    """
    Incrementally update user_homepage_profile on each tracked event.
    1. Decay all existing affinities by 0.98
    2. Add weighted signal for category and feature
    3. Update behavior counters
    4. Append to recent_activity (capped at 100)
    """
    weight = EVENT_WEIGHTS.get(event, 0)
    if weight == 0:
        return

    profile = await get_or_create_profile(db, user_id)
    now = datetime.now(timezone.utc).isoformat()

    # ── 1. Decay existing affinities ──
    cat_aff = profile.get("category_affinity", {})
    for k in cat_aff:
        cat_aff[k] *= DECAY

    feat_aff = profile.get("feature_affinity", {})
    for k in feat_aff:
        feat_aff[k] *= DECAY

    # ── 2. Add weighted signal ──
    # Category comes from meta.category OR animation_style
    category = (meta or {}).get("category") or (meta or {}).get("animation_style")
    if category:
        cat_aff[category] = cat_aff.get(category, 0.0) + (weight / 12.0)

    # Feature affinity from tool_type or source_surface
    feature_key = (meta or {}).get("tool_type") or (meta or {}).get("source_surface")
    if feature_key:
        feat_aff[feature_key] = feat_aff.get(feature_key, 0.0) + (weight / 12.0)

    # Normalize affinities to [0, 1]
    if cat_aff:
        max_cat = max(cat_aff.values()) or 1.0
        if max_cat > 1.0:
            cat_aff = {k: v / max_cat for k, v in cat_aff.items()}
    if feat_aff:
        max_feat = max(feat_aff.values()) or 1.0
        if max_feat > 1.0:
            feat_aff = {k: v / max_feat for k, v in feat_aff.items()}

    # ── 3. Update behavior counters ──
    bm = profile.get("behavior_metrics", {})
    if event in ("click", "card_click", "impression"):
        bm["total_clicks"] = bm.get("total_clicks", 0) + 1
        bm["total_views"] = bm.get("total_views", 0) + 1
    if event in ("continue_click", "continue"):
        bm["total_continues"] = bm.get("total_continues", 0) + 1
    if event in ("watch_start", "generate_click", "generation_start"):
        bm["total_starts"] = bm.get("total_starts", 0) + 1
    if event in ("watch_complete", "creation_completed", "generation_complete"):
        bm["total_completions"] = bm.get("total_completions", 0) + 1
    if event in ("share_click", "share"):
        bm["total_shares"] = bm.get("total_shares", 0) + 1

    # Recalculate rates
    total_clicks = bm.get("total_clicks", 0) or 1
    total_starts = bm.get("total_starts", 0) or 1
    total_views = bm.get("total_views", 0) or 1
    bm["continue_rate"] = round(bm.get("total_continues", 0) / total_clicks, 4)
    bm["completion_rate"] = round(bm.get("total_completions", 0) / total_starts, 4)
    bm["share_rate"] = round(bm.get("total_shares", 0) / total_views, 4)

    # ── 4. Append to recent_activity (last 100) ──
    recent = profile.get("recent_activity", [])
    recent.append({
        "event": event,
        "story_id": (meta or {}).get("story_id"),
        "category": category,
        "feature_key": feature_key,
        "weight": weight,
        "timestamp": now,
    })
    recent = recent[-100:]

    total_events = profile.get("counts", {}).get("total_events", 0) + 1

    # ── 5. Write back ──
    await db.user_homepage_profile.update_one(
        {"user_id": user_id},
        {"$set": {
            "category_affinity": cat_aff,
            "feature_affinity": feat_aff,
            "behavior_metrics": bm,
            "recent_activity": recent,
            "counts": {"total_events": total_events, "last_updated": now},
            "updated_at": now,
        }},
        upsert=True,
    )


# ═══════════════════════════════════════════════════════════════
# SCORING ENGINE
# ═══════════════════════════════════════════════════════════════

def _freshness_score(created_at_str: str) -> float:
    """Score 0-1 based on recency. 1.0 = just created, decays over 7 days."""
    if not created_at_str:
        return 0.0
    try:
        if isinstance(created_at_str, datetime):
            created = created_at_str
        else:
            created = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        age_hours = (datetime.now(timezone.utc) - created).total_seconds() / 3600
        return max(0.0, 1.0 - (age_hours / (7 * 24)))
    except Exception:
        return 0.0


def _momentum_score(profile: dict) -> float:
    """Weighted sum of events in last 24h, normalized to 0-1."""
    recent = profile.get("recent_activity", [])
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    total = 0.0
    for entry in recent:
        if (entry.get("timestamp") or "") >= cutoff:
            total += entry.get("weight", 0)
    # Normalize: 50 weighted points in 24h = 1.0
    return min(1.0, total / 50.0)


def _global_trending_score(story: dict, max_remix: int) -> float:
    """Score 0-1 based on remix_count relative to the max in the pool."""
    if max_remix <= 0:
        return 0.0
    return min(1.0, (story.get("remix_count") or 0) / max_remix)


def score_story(story: dict, profile: dict, max_remix: int) -> float:
    """
    EXACT formula (corrected — no continue_rate duplication):
      (0.25 × category_affinity) + (0.20 × hook_strength)
      + (0.15 × completion_rate) + (0.15 × momentum_score)
      + (0.10 × freshness_score) + (0.10 × share_rate)
      + (0.05 × global_trending_score)

    hook_strength already encodes continue signal — no double counting.
    """
    cat_aff = profile.get("category_affinity", {})
    bm = profile.get("behavior_metrics", {})

    # Category affinity: use animation_style as primary category key
    style = story.get("animation_style", "")
    story_cat_score = cat_aff.get(style, 0.0)

    # Also check meta category if available
    meta_cat = story.get("category", "")
    if meta_cat and meta_cat in cat_aff:
        story_cat_score = max(story_cat_score, cat_aff[meta_cat])

    # Hook strength from A/B testing data
    hook_strength = story.get("hook_strength", 0.0)

    completion_rate = bm.get("completion_rate", 0.0)
    share_rate = bm.get("share_rate", 0.0)
    freshness = _freshness_score(story.get("created_at", ""))
    momentum = _momentum_score(profile)
    trending = _global_trending_score(story, max_remix)

    return (
        0.25 * story_cat_score
        + 0.20 * hook_strength
        + 0.15 * completion_rate
        + 0.15 * momentum
        + 0.10 * freshness
        + 0.10 * share_rate
        + 0.05 * trending
    )


def rank_stories(stories: list, profile: dict) -> list:
    """Score and sort a list of stories descending by score."""
    if not stories:
        return []
    max_remix = max((s.get("remix_count") or 0) for s in stories) if stories else 0
    scored = []
    for s in stories:
        s_copy = dict(s)
        s_copy["_score"] = round(score_story(s, profile, max_remix), 4)
        scored.append(s_copy)
    scored.sort(key=lambda x: x["_score"], reverse=True)
    return scored


def rank_rows(row_candidates: dict, profile: dict) -> list:
    """
    Determine row order based on user behavior.
    Hard rules:
      IF user has active stories → continue_stories = rank 1
      ELSE IF high continue_rate → trending = rank 1
      ELSE → fresh = rank 1
    """
    bm = profile.get("behavior_metrics", {})
    continue_stories = row_candidates.get("continue_stories", [])
    has_active = len(continue_stories) > 0
    high_continue_rate = bm.get("continue_rate", 0.0) > 0.3

    # Build row definitions
    rows = {
        "continue_stories": {
            "key": "continue_stories",
            "title": "Continue Your Story",
            "icon": "RefreshCw",
            "icon_color": "text-blue-400",
            "stories": continue_stories,
        },
        "trending_now": {
            "key": "trending_now",
            "title": "Trending Now",
            "icon": "Flame",
            "icon_color": "text-amber-400",
            "stories": row_candidates.get("trending_stories", []),
        },
        "fresh_stories": {
            "key": "fresh_stories",
            "title": "Fresh Stories",
            "icon": "Sparkles",
            "icon_color": "text-violet-400",
            "stories": row_candidates.get("fresh_stories", []),
        },
        "unfinished_worlds": {
            "key": "unfinished_worlds",
            "title": "Unfinished Worlds",
            "icon": "Clock",
            "icon_color": "text-emerald-400",
            "stories": row_candidates.get("unfinished_worlds", []),
        },
    }

    # Determine priority order
    if has_active:
        order = ["continue_stories", "trending_now", "fresh_stories", "unfinished_worlds"]
    elif high_continue_rate:
        order = ["trending_now", "continue_stories", "fresh_stories", "unfinished_worlds"]
    else:
        order = ["fresh_stories", "trending_now", "continue_stories", "unfinished_worlds"]

    result = []
    for key in order:
        row = rows.get(key)
        if row and row["stories"]:
            result.append(row)

    # Append any rows that had no stories at the end (empty rows excluded)
    return result


def rank_features(profile: dict) -> list:
    """
    EXACT formula:
      feature_score = (0.50 × feature_affinity) + (0.25 × recent_usage)
                    + (0.15 × success_rate) + (0.10 × monetization_priority)
    """
    feat_aff = profile.get("feature_affinity", {})
    recent = profile.get("recent_activity", [])
    bm = profile.get("behavior_metrics", {})

    # Calculate recent_usage per feature (last 50 events)
    recent_50 = recent[-50:] if recent else []
    usage_counts = {}
    for entry in recent_50:
        fk = entry.get("feature_key")
        if fk:
            usage_counts[fk] = usage_counts.get(fk, 0) + 1
    max_usage = max(usage_counts.values()) if usage_counts else 1

    # Success rate: use global completion_rate as proxy per feature
    success_rate = bm.get("completion_rate", 0.0)

    # Default feature list with metadata
    FEATURES = [
        {"name": "Story Video", "desc": "Turn ideas into cinematic stories", "icon": "Film", "path": "/app/story-video-studio", "key": "story-video-studio", "gradient": "from-indigo-500 to-blue-700"},
        {"name": "Story Series", "desc": "Multi-episode sagas with memory", "icon": "BookOpen", "path": "/app/story-series", "key": "story-series", "gradient": "from-purple-500 to-fuchsia-700"},
        {"name": "Character Memory", "desc": "Persistent characters across stories", "icon": "User", "path": "/app/characters", "key": "characters", "gradient": "from-cyan-500 to-blue-700"},
        {"name": "Reel Generator", "desc": "Viral short-form video reels", "icon": "Play", "path": "/app/reels", "key": "reels", "gradient": "from-rose-500 to-pink-700"},
        {"name": "Photo to Comic", "desc": "Transform photos into comic panels", "icon": "Camera", "path": "/app/photo-to-comic", "key": "photo-to-comic", "gradient": "from-amber-500 to-orange-700"},
        {"name": "Comic Storybook", "desc": "Panel-by-panel illustrated stories", "icon": "Palette", "path": "/app/comic-storybook", "key": "comic-storybook", "gradient": "from-emerald-500 to-green-700"},
        {"name": "Bedtime Stories", "desc": "Narrated sleep tales with visuals", "icon": "Star", "path": "/app/bedtime-stories", "key": "bedtime-stories", "gradient": "from-indigo-500 to-purple-700"},
        {"name": "Reaction GIF", "desc": "Photo-to-reaction GIF in seconds", "icon": "ImageIcon", "path": "/app/gif-maker", "key": "gif-maker", "gradient": "from-pink-500 to-rose-700"},
        {"name": "Brand Story", "desc": "Cinematic brand narratives", "icon": "Megaphone", "path": "/app/brand-story-builder", "key": "brand-story-builder", "gradient": "from-teal-500 to-cyan-700"},
        {"name": "Daily Viral Ideas", "desc": "AI-generated trending prompts", "icon": "Lightbulb", "path": "/app/daily-viral-ideas", "key": "daily-viral-ideas", "gradient": "from-amber-500 to-red-700"},
    ]

    scored = []
    for f in FEATURES:
        fk = f["key"]
        affinity = feat_aff.get(fk, 0.0)
        recent_usage = (usage_counts.get(fk, 0) / max_usage) if max_usage else 0.0
        monetization = FEATURE_MONETIZATION_PRIORITY.get(fk, 0.5)

        f_score = (
            0.50 * affinity
            + 0.25 * recent_usage
            + 0.15 * success_rate
            + 0.10 * monetization
        )
        scored.append({**f, "score": round(f_score, 4)})

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored


def select_hero(stories: list, profile: dict) -> dict | None:
    """Pick the highest-scored story that has displayable media."""
    if not stories:
        return None
    ranked = rank_stories(stories, profile)
    for s in ranked:
        media = s.get("media") or {}
        if media.get("thumbnail_small_url") or media.get("poster_large_url"):
            return s
    return ranked[0] if ranked else None


def is_personalized(profile: dict) -> bool:
    """Check if profile has enough data for personalization."""
    return profile.get("counts", {}).get("total_events", 0) >= COLD_START_THRESHOLD


def profile_strength(profile: dict) -> float:
    """0.0-1.0 indicating how strong the profile is. 50 events = 1.0."""
    events = profile.get("counts", {}).get("total_events", 0)
    return min(1.0, events / 50.0)
