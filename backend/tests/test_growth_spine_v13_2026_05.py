"""
P0 2026-05 V13 — Growth-intervention spine regression.

Validates:
  1. Startup sync forces hero_headline traffic_weights to
     {headline_b:1, headline_a:0, headline_c:0} and tags
     frozen_variants=['headline_a'].
  2. Variant assignment honors the new weights — 100/100 calls go to
     headline_b. (Smoke check; deterministic hash means weight=0
     variants are never selected.)
  3. New canonical funnel events accept and persist the extended
     context fields (anonymous_id, latency_ms, generation_id,
     abandonment_step, abandonment_reason, share_channel).
  4. /activation-funnel response now contains red_alerts +
     abandonment_breakdown + p95_to_next_ms on each stage.
"""
import os
import re
import time
import uuid

import requests


def _read_env():
    with open("/app/frontend/.env") as f:
        m = re.search(r"^REACT_APP_BACKEND_URL=(.*)$", f.read(), flags=re.M)
    return m.group(1).strip()


API = _read_env()


def _login(email, password):
    r = requests.post(f"{API}/api/auth/login",
                      json={"email": email, "password": password},
                      timeout=30)
    r.raise_for_status()
    d = r.json()
    return d.get("access_token") or d.get("token")


def test_hero_headline_killed_in_db():
    """Mongo doc reflects the kill-switch + freeze lock."""
    from pymongo import MongoClient
    with open("/app/backend/.env") as f:
        env = f.read()
    mongo = re.search(r"^MONGO_URL=(.*)$", env, flags=re.M).group(1).strip().strip('"')
    dbn = re.search(r"^DB_NAME=(.*)$", env, flags=re.M).group(1).strip().strip('"')
    db = MongoClient(mongo)[dbn]
    doc = db.ab_experiments.find_one({"experiment_id": "hero_headline"})
    assert doc is not None
    tw = doc.get("traffic_weights") or {}
    assert tw.get("headline_a") == 0
    assert tw.get("headline_b") == 1.0
    assert tw.get("headline_c") == 0
    assert "headline_a" in (doc.get("frozen_variants") or [])
    assert "Lost A/B test" in (doc.get("frozen_reason") or "")


def test_smart_route_always_returns_headline_b():
    """Deterministic assignment: weights {a:0,b:1,c:0} ⇒ every session → b."""
    variants_seen = set()
    for i in range(40):
        r = requests.get(
            f"{API}/api/ab/smart-route",
            params={"experiment_id": "hero_headline", "traffic_source": "organic"},
            headers={"X-Session-Id": f"reg-{uuid.uuid4().hex[:8]}-{i}"},
            timeout=15,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        variants_seen.add(data.get("variant_id"))
    assert variants_seen == {"headline_b"}, f"leak: {variants_seen}"


def test_activation_funnel_response_shape():
    """Endpoint emits the new red_alerts + abandonment_breakdown +
    p95_to_next_ms + auth_sessions/anon_sessions per stage."""
    token = _login("admin@creatorstudio.ai", "Cr3@t0rStud!o#2026")
    r = requests.get(
        f"{API}/api/funnel/activation-funnel?days=7",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    assert r.status_code == 200, r.text
    d = r.json()
    assert d.get("success") is True
    assert "red_alerts" in d
    assert "abandonment_breakdown" in d
    stages = d.get("stages") or []
    # Stages match the canonical 7-step chain.
    expected = [
        "landing_view", "hero_cta_clicked", "story_prompt_started",
        "story_prompt_submitted", "story_generation_started",
        "story_generation_completed", "story_published",
    ]
    assert [s["step"] for s in stages] == expected
    for s in stages:
        assert "p95_to_next_ms" in s
        assert "auth_sessions" in s
        assert "anon_sessions" in s


def test_funnel_track_accepts_new_event_names_and_context():
    """Ingest a hero_cta_clicked event with all the new context fields
    and verify it persists with the same shape."""
    from pymongo import MongoClient
    with open("/app/backend/.env") as f:
        env = f.read()
    mongo = re.search(r"^MONGO_URL=(.*)$", env, flags=re.M).group(1).strip().strip('"')
    dbn = re.search(r"^DB_NAME=(.*)$", env, flags=re.M).group(1).strip().strip('"')
    db = MongoClient(mongo)[dbn]

    sid = f"reg-{uuid.uuid4().hex[:10]}"
    aid = f"anon-{uuid.uuid4().hex[:10]}"
    gid = f"gen-{uuid.uuid4().hex[:10]}"
    payload = {
        "step": "hero_cta_clicked",
        "session_id": sid,
        "anonymous_id": aid,
        "context": {
            "source_page": "landing",
            "page": "/",
            "device_type": "desktop",
            "browser": "chrome",
            "anonymous_id": aid,
            "latency_ms": 312,
            "generation_id": gid,
            "abandonment_step": None,
            "abandonment_reason": None,
            "share_channel": None,
            "meta": {"test": True},
        },
    }
    r = requests.post(f"{API}/api/funnel/track", json=payload, timeout=15)
    assert r.status_code == 200, r.text

    # Verify the doc was written with our explicit fields.
    doc = db.funnel_events.find_one({"session_id": sid, "step": "hero_cta_clicked"},
                                    sort=[("timestamp", -1)])
    assert doc is not None
    assert doc.get("anonymous_id") == aid
    assert doc.get("auth_state") == "anonymous"
    assert doc.get("latency_ms") == 312
    assert doc.get("generation_id") == gid
    db.funnel_events.delete_many({"session_id": sid})


def test_funnel_track_accepts_share_loop_events():
    """share_sheet_opened + share_channel_selected + share_link_copied."""
    from pymongo import MongoClient
    with open("/app/backend/.env") as f:
        env = f.read()
    mongo = re.search(r"^MONGO_URL=(.*)$", env, flags=re.M).group(1).strip().strip('"')
    dbn = re.search(r"^DB_NAME=(.*)$", env, flags=re.M).group(1).strip().strip('"')
    db = MongoClient(mongo)[dbn]

    sid = f"reg-share-{uuid.uuid4().hex[:10]}"
    for step, channel in [
        ("share_sheet_opened", None),
        ("share_channel_selected", "whatsapp"),
        ("share_link_copied", "copy_link"),
    ]:
        r = requests.post(
            f"{API}/api/funnel/track",
            json={"step": step, "session_id": sid, "context": {
                "device_type": "mobile",
                "share_channel": channel,
                "share_story_id": "story_demo",
            }},
            timeout=15,
        )
        assert r.status_code == 200, r.text

    docs = list(db.funnel_events.find({"session_id": sid}))
    steps = sorted(d["step"] for d in docs)
    assert steps == ["share_channel_selected", "share_link_copied", "share_sheet_opened"]
    by_step = {d["step"]: d for d in docs}
    assert by_step["share_channel_selected"].get("share_channel") == "whatsapp"
    assert by_step["share_link_copied"].get("share_channel") == "copy_link"
    db.funnel_events.delete_many({"session_id": sid})
