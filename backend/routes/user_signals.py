"""
User Signals Endpoint — The 4 core signals for first 50 users.
No dashboard. One endpoint. Real numbers with denominators and sample IDs.

Signals:
1. TTFV (Time-to-First-Value)
2. Intent → Action Funnel
3. Second Action Rate
4. Return Behavior
"""
import os
import sys
import logging
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, Query, HTTPException
import statistics

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared import db, get_current_user

logger = logging.getLogger("user_signals")
router = APIRouter(prefix="/admin", tags=["User Signals"])

# Event name mapping: covers both old and new event names
LANDING_EVENTS = {"landing_view", "demo_viewed", "first_action_click"}
TYPING_EVENTS = {"typing_started"}
GENERATE_EVENTS = {"generate_clicked", "generation_started", "story_generation_started"}
COMPLETED_EVENTS = {"generation_completed", "story_generated_success"}
POSTGEN_EVENTS = {"postgen_cta_clicked", "second_action", "continue_clicked"}
BATTLE_EVENTS = {"battle_enter_clicked", "entered_battle"}
SHARE_EVENTS = {"win_share_triggered", "cta_share_clicked", "share_revisit"}
SESSION_EVENTS = {"session_started"}
VALUE_EVENTS = COMPLETED_EVENTS  # "First value" = completed generation


@router.get("/user-signals")
async def get_user_signals(
    days: int = Query(default=7, ge=1, le=90),
    current_user: dict = Depends(get_current_user)
):
    """
    Returns the 4 core user signals computed directly from DB.
    Admin-only. Includes denominators, percentages, and sample IDs.
    """
    if current_user.get("role", "").upper() != "ADMIN":
        raise HTTPException(status_code=403, detail="Admin only")

    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    now = datetime.now(timezone.utc).isoformat()

    # ═══════════════════════════════════════════════════════════
    # Gather all events in period, grouped by session
    # ═══════════════════════════════════════════════════════════
    all_events = await db.funnel_events.find(
        {"timestamp": {"$gte": cutoff}},
        {"_id": 0, "step": 1, "session_id": 1, "user_id": 1, "timestamp": 1, "traffic_source": 1, "device_type": 1}
    ).to_list(50000)

    # Group by session_id
    sessions = {}
    for evt in all_events:
        sid = evt.get("session_id", "unknown")
        if sid not in sessions:
            sessions[sid] = {"events": [], "user_id": None, "source": "unknown", "device": "unknown"}
        sessions[sid]["events"].append(evt)
        if evt.get("user_id"):
            sessions[sid]["user_id"] = evt["user_id"]
        if evt.get("traffic_source") and evt["traffic_source"] != "unknown":
            sessions[sid]["source"] = evt["traffic_source"]
        if evt.get("device_type") and evt["device_type"] != "unknown":
            sessions[sid]["device"] = evt["device_type"]

    # Also use story_engine_jobs for more reliable completion data
    completed_jobs = await db.story_engine_jobs.find(
        {"state": {"$in": ["READY", "COMPLETED"]}, "created_at": {"$gte": cutoff}},
        {"_id": 0, "job_id": 1, "user_id": 1, "created_at": 1}
    ).to_list(5000)

    # Build user → first job time mapping
    user_first_job = {}
    user_job_count = {}
    for job in completed_jobs:
        uid = job.get("user_id", "")
        if uid:
            ts = job.get("created_at", "")
            if uid not in user_first_job or ts < user_first_job[uid]:
                user_first_job[uid] = ts
            user_job_count[uid] = user_job_count.get(uid, 0) + 1

    # ═══════════════════════════════════════════════════════════
    # SIGNAL 1: TTFV (Time-to-First-Value)
    # ═══════════════════════════════════════════════════════════
    ttfv_values = []  # seconds
    ttfv_reached = []  # user/session IDs that reached value
    ttfv_not_reached = []  # user/session IDs that didn't

    for sid, sdata in sessions.items():
        events = sorted(sdata["events"], key=lambda e: e.get("timestamp", ""))
        if not events:
            continue

        # Find first landing event timestamp
        first_touch = None
        for e in events:
            if e["step"] in LANDING_EVENTS or e["step"] in SESSION_EVENTS:
                first_touch = e["timestamp"]
                break
        if not first_touch:
            first_touch = events[0]["timestamp"]

        # Find first value event
        first_value = None
        for e in events:
            if e["step"] in VALUE_EVENTS:
                first_value = e["timestamp"]
                break

        identifier = sdata["user_id"] or sid[:12]

        if first_value and first_touch:
            try:
                ft = datetime.fromisoformat(first_touch.replace("Z", "+00:00"))
                fv = datetime.fromisoformat(first_value.replace("Z", "+00:00"))
                delta = (fv - ft).total_seconds()
                if 0 < delta < 86400:  # Sanity: within 24 hours
                    ttfv_values.append(delta)
                    ttfv_reached.append(identifier)
            except:
                pass
        else:
            # Check if user has completed jobs (value reached outside event tracking)
            uid = sdata.get("user_id", "")
            if uid and uid in user_first_job:
                ttfv_reached.append(identifier)
            else:
                ttfv_not_reached.append(identifier)

    ttfv_result = {
        "median_seconds": round(statistics.median(ttfv_values), 1) if ttfv_values else None,
        "p75_seconds": round(sorted(ttfv_values)[int(len(ttfv_values) * 0.75)] if ttfv_values else 0, 1) if ttfv_values else None,
        "p90_seconds": round(sorted(ttfv_values)[int(len(ttfv_values) * 0.90)] if ttfv_values else 0, 1) if ttfv_values else None,
        "reached_value_count": len(ttfv_reached),
        "never_reached_count": len(ttfv_not_reached),
        "sample_reached": ttfv_reached[:5],
        "sample_not_reached": ttfv_not_reached[:5],
        "total_sessions": len(sessions),
        "note": "TTFV = time from first landing/session event to first generation_completed"
    }

    # ═══════════════════════════════════════════════════════════
    # SIGNAL 2: Intent → Action Funnel
    # ═══════════════════════════════════════════════════════════
    def count_sessions_with(event_set):
        """Count unique sessions that have at least one event from the set."""
        return len([sid for sid, s in sessions.items()
                    if any(e["step"] in event_set for e in s["events"])])

    landing = count_sessions_with(LANDING_EVENTS | SESSION_EVENTS)
    typing = count_sessions_with(TYPING_EVENTS)
    generate = count_sessions_with(GENERATE_EVENTS)
    completed = count_sessions_with(COMPLETED_EVENTS)
    postgen = count_sessions_with(POSTGEN_EVENTS)

    def pct(num, denom):
        return round(num / denom * 100, 1) if denom > 0 else 0

    funnel_result = {
        "landing_sessions": landing,
        "typing_started_sessions": typing,
        "generate_clicked_sessions": generate,
        "generation_completed_sessions": completed,
        "postgen_action_sessions": postgen,
        "conversion_rates": {
            "landing_to_typing": pct(typing, landing),
            "typing_to_generate": pct(generate, typing),
            "generate_to_completed": pct(completed, generate),
            "completed_to_postgen": pct(postgen, completed),
            "landing_to_completed": pct(completed, landing),
        },
        "note": "Each count = unique sessions with at least one event of that type"
    }

    # ═══════════════════════════════════════════════════════════
    # SIGNAL 3: Second Action Rate
    # ═══════════════════════════════════════════════════════════
    users_with_first_gen = set()
    users_with_second_action = set()
    second_action_breakdown = {"second_generation": [], "battle_enter": [], "share": [], "postgen_cta": []}

    # From jobs data (most reliable)
    for uid, count in user_job_count.items():
        users_with_first_gen.add(uid)
        if count >= 2:
            users_with_second_action.add(uid)
            second_action_breakdown["second_generation"].append(uid)

    # From events (for battle/share/postgen)
    user_events = {}
    for sid, sdata in sessions.items():
        uid = sdata.get("user_id")
        if not uid:
            continue
        if uid not in user_events:
            user_events[uid] = set()
        for e in sdata["events"]:
            user_events[uid].add(e["step"])

    for uid, steps in user_events.items():
        has_completed = bool(steps & COMPLETED_EVENTS)
        if has_completed:
            users_with_first_gen.add(uid)
            if steps & BATTLE_EVENTS:
                users_with_second_action.add(uid)
                second_action_breakdown["battle_enter"].append(uid)
            if steps & SHARE_EVENTS:
                users_with_second_action.add(uid)
                second_action_breakdown["share"].append(uid)
            if steps & POSTGEN_EVENTS:
                users_with_second_action.add(uid)
                second_action_breakdown["postgen_cta"].append(uid)

    first_gen_count = len(users_with_first_gen)
    second_action_count = len(users_with_second_action)

    second_action_result = {
        "users_with_first_generation": first_gen_count,
        "users_with_second_action": second_action_count,
        "second_action_rate": pct(second_action_count, first_gen_count),
        "breakdown": {
            "second_generation": len(set(second_action_breakdown["second_generation"])),
            "battle_enter": len(set(second_action_breakdown["battle_enter"])),
            "share": len(set(second_action_breakdown["share"])),
            "postgen_cta": len(set(second_action_breakdown["postgen_cta"])),
        },
        "sample_second_action_users": list(users_with_second_action)[:5],
        "sample_single_action_users": list(users_with_first_gen - users_with_second_action)[:5],
        "note": "Second action = any of: second generation, battle entry, share, post-gen CTA click"
    }

    # ═══════════════════════════════════════════════════════════
    # SIGNAL 4: Return Behavior
    # ═══════════════════════════════════════════════════════════
    # Group sessions by user_id
    user_sessions = {}
    for sid, sdata in sessions.items():
        uid = sdata.get("user_id")
        if not uid:
            continue
        events = sorted(sdata["events"], key=lambda e: e.get("timestamp", ""))
        if events:
            first_ts = events[0].get("timestamp", "")
            if uid not in user_sessions:
                user_sessions[uid] = []
            user_sessions[uid].append({"session_id": sid, "first_event": first_ts})

    # Count users with 2+ sessions
    multi_session_users = {uid: sess for uid, sess in user_sessions.items() if len(sess) >= 2}

    # Calculate return delays
    return_delays = []
    same_day_returns = []
    for uid, sess_list in multi_session_users.items():
        sorted_sess = sorted(sess_list, key=lambda s: s["first_event"])
        if len(sorted_sess) >= 2:
            try:
                t1 = datetime.fromisoformat(sorted_sess[0]["first_event"].replace("Z", "+00:00"))
                t2 = datetime.fromisoformat(sorted_sess[1]["first_event"].replace("Z", "+00:00"))
                delay_hours = (t2 - t1).total_seconds() / 3600
                return_delays.append(delay_hours)
                if t1.date() == t2.date():
                    same_day_returns.append(uid)
            except:
                pass

    total_unique_users = len(user_sessions)

    return_result = {
        "total_unique_users": total_unique_users,
        "users_with_2plus_sessions": len(multi_session_users),
        "return_rate": pct(len(multi_session_users), total_unique_users),
        "same_day_return_count": len(same_day_returns),
        "same_day_return_rate": pct(len(same_day_returns), total_unique_users),
        "median_return_delay_hours": round(statistics.median(return_delays), 1) if return_delays else None,
        "sample_returning_users": list(multi_session_users.keys())[:5],
        "sample_single_session_users": list(set(user_sessions.keys()) - set(multi_session_users.keys()))[:5],
        "note": "Based on distinct session_ids per user_id with different first-event timestamps"
    }

    # ═══════════════════════════════════════════════════════════
    # TRACKING QUALITY CHECK
    # ═══════════════════════════════════════════════════════════
    quality = {
        "total_events_in_period": len(all_events),
        "total_sessions": len(sessions),
        "events_with_user_id": sum(1 for e in all_events if e.get("user_id")),
        "events_without_user_id": sum(1 for e in all_events if not e.get("user_id")),
        "user_id_coverage": pct(sum(1 for e in all_events if e.get("user_id")), len(all_events)),
        "completed_jobs_in_period": len(completed_jobs),
        "unique_users_in_jobs": len(user_first_job),
        "warning": "user_id is null for unauthenticated events (landing, demo). Session-level analysis is more reliable for top-of-funnel." if sum(1 for e in all_events if not e.get("user_id")) > len(all_events) * 0.5 else None
    }

    return {
        "computed_at": now,
        "period_days": days,
        "ttfv": ttfv_result,
        "funnel": funnel_result,
        "second_action": second_action_result,
        "return_behavior": return_result,
        "tracking_quality": quality,
    }
