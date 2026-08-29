import sys
import types


shared_stub = types.ModuleType("shared")
shared_stub.db = None
shared_stub.get_current_user = lambda: None
shared_stub.get_admin_user = lambda: None
sys.modules.setdefault("shared", shared_stub)

from routes.story_series import PlanEpisodeRequest, _fallback_episode_plan


def test_fallback_episode_plan_has_required_contract_shape():
    plan = _fallback_episode_plan(
        {"title": "Clocktower Kids", "style": "cartoon_2d"},
        {"cliffhanger": "the fifth bell rang"},
        PlanEpisodeRequest(direction_type="twist", custom_prompt="Reveal the bell code"),
        2,
    )

    assert plan["_fallback"] is True
    assert plan["episode_title"]
    assert plan["summary"]
    assert plan["theme"] == "twist"
    assert isinstance(plan["character_arcs"], list) and plan["character_arcs"]
    assert len(plan["scene_breakdown"]) == 5
    assert plan["cliffhanger"]["description"]
    for index, scene in enumerate(plan["scene_breakdown"], start=1):
        assert scene["scene_number"] == index
        assert scene["visual_prompt"]
        assert "cartoon_2d" in scene["visual_prompt"]
        assert "low quality" in scene["visual_prompt"]
        assert scene["duration_seconds"] == 5
