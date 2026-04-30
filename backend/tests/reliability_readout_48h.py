"""48h Photo Trailer reliability readout.

Founder directive: raw metrics only. No new endpoints. No dashboard work.
Queries MongoDB directly for the strict 48h window, prints the readout,
and closes with the mandatory bottleneck statement.

Run:  cd /app/backend && python -m tests.reliability_readout_48h
"""
import asyncio
import os
import statistics
from datetime import datetime, timedelta, timezone

from motor.motor_asyncio import AsyncIOMotorClient


async def main() -> None:
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = client[os.environ["DB_NAME"]]

    now = datetime.now(timezone.utc)
    cutoff = (now - timedelta(hours=48)).isoformat()
    job_match = {"created_at": {"$gte": cutoff}}

    # ── Starts attempted (every job doc created, regardless of outcome) ────
    starts_attempted = await db.photo_trailer_jobs.count_documents(job_match)
    # Starts "succeeded" = jobs that cleared VALIDATING and entered the real pipeline.
    # Anything FAILED with a start-side error_code never began rendering.
    start_side_error_codes = {
        "LOW_CREDITS",
        "UPGRADE_REQUIRED",
        "FREE_QUOTA_EXCEEDED",
        "CREDIT_DEDUCT_FAIL",
        "HERO_LOAD_FAIL",
        "SESSION_NOT_FOUND",
        "ASSET_NOT_IN_SESSION",
        "CONSENT_REQUIRED",
        "TEMPLATE_NOT_FOUND",
    }
    start_failed_breakdown = {}
    async for d in db.photo_trailer_jobs.aggregate([
        {"$match": {**job_match, "status": "FAILED",
                    "error_code": {"$in": list(start_side_error_codes)}}},
        {"$group": {"_id": "$error_code", "n": {"$sum": 1}}},
    ]):
        start_failed_breakdown[d["_id"]] = int(d["n"])
    start_failed_total = sum(start_failed_breakdown.values())

    # Start_failed also captured via funnel event (covers 402/422 that never
    # create a job doc at all).
    sf_events = await db.funnel_events.count_documents({
        "step": "photo_trailer_start_failed",
        "timestamp": {"$gte": cutoff},
    })
    sf_event_codes = {}
    async for d in db.funnel_events.aggregate([
        {"$match": {"step": "photo_trailer_start_failed",
                    "timestamp": {"$gte": cutoff}}},
        {"$group": {"_id": "$meta.code", "n": {"$sum": 1}}},
    ]):
        sf_event_codes[d["_id"] or "UNKNOWN"] = int(d["n"])

    starts_succeeded = starts_attempted - start_failed_total

    # ── Outcomes ──────────────────────────────────────────────────────────
    completed = await db.photo_trailer_jobs.count_documents(
        {**job_match, "status": "COMPLETED"}
    )
    failed_total = await db.photo_trailer_jobs.count_documents(
        {**job_match, "status": "FAILED"}
    )
    still_running = await db.photo_trailer_jobs.count_documents(
        {**job_match, "status": {"$in": ["QUEUED", "PROCESSING"]}}
    )
    # Pipeline-side failures = failures that happened AFTER start (rendering etc.)
    pipeline_failed = failed_total - start_failed_total

    completion_rate_of_starts = (
        round(completed / starts_succeeded * 100, 1) if starts_succeeded else 0.0
    )
    completion_rate_of_attempts = (
        round(completed / starts_attempted * 100, 1) if starts_attempted else 0.0
    )

    # ── Render time (COMPLETED jobs only) ─────────────────────────────────
    render_seconds = []
    async for j in db.photo_trailer_jobs.find(
        {**job_match, "status": "COMPLETED",
         "started_at": {"$ne": None}, "completed_at": {"$ne": None}},
        {"_id": 0, "started_at": 1, "completed_at": 1,
         "duration_target_seconds": 1},
    ):
        try:
            s = datetime.fromisoformat(j["started_at"])
            c = datetime.fromisoformat(j["completed_at"])
            render_seconds.append((c - s).total_seconds())
        except Exception:
            continue
    median_render = round(statistics.median(render_seconds), 1) if render_seconds else None
    p95_render = (
        round(statistics.quantiles(render_seconds, n=20)[-1], 1)
        if len(render_seconds) >= 20 else None
    )
    max_render = round(max(render_seconds), 1) if render_seconds else None

    # ── Pipeline failure breakdown by error code ──────────────────────────
    pipeline_codes = {}
    async for d in db.photo_trailer_jobs.aggregate([
        {"$match": {**job_match, "status": "FAILED",
                    "error_code": {"$nin": list(start_side_error_codes)}}},
        {"$group": {"_id": "$error_code", "n": {"$sum": 1}}},
        {"$sort": {"n": -1}},
    ]):
        pipeline_codes[d["_id"] or "UNKNOWN"] = int(d["n"])

    timeout_kills = pipeline_codes.get("RENDER_TIMEOUT", 0)
    stale_janitor = pipeline_codes.get("STALE_PIPELINE", 0)

    # ── Retries ───────────────────────────────────────────────────────────
    retry_events = await db.funnel_events.count_documents({
        "step": "photo_trailer_auto_requeued",
        "timestamp": {"$gte": cutoff},
    })
    manual_retries = await db.photo_trailer_jobs.count_documents({
        **job_match, "retry_count": {"$gte": 1},
    })

    # ── Downloads + shares ────────────────────────────────────────────────
    downloads_click = await db.funnel_events.count_documents({
        "step": "photo_trailer_download_clicked",
        "timestamp": {"$gte": cutoff},
    })
    wa_shares = await db.funnel_events.count_documents({
        "step": "whatsapp_share_clicked",
        "timestamp": {"$gte": cutoff},
    })
    native_shares = await db.funnel_events.count_documents({
        "step": "native_share_clicked",
        "timestamp": {"$gte": cutoff},
    })

    # ── Render-time by duration bucket ────────────────────────────────────
    by_bucket = {}
    async for d in db.photo_trailer_jobs.aggregate([
        {"$match": {**job_match, "status": "COMPLETED"}},
        {"$group": {"_id": "$duration_target_seconds", "n": {"$sum": 1}}},
    ]):
        if d["_id"] is None:
            continue
        by_bucket[int(d["_id"])] = int(d["n"])

    # ── Print the readout ─────────────────────────────────────────────────
    line = "═" * 72
    print(line)
    print(f"  PHOTO TRAILER — 48h RELIABILITY READOUT")
    print(f"  Window: {cutoff}  →  {now.isoformat()}")
    print(line)
    print()
    print("┌─ STARTS ─────────────────────────────────────────────────────┐")
    print(f"│ starts_attempted              {starts_attempted:>6}")
    print(f"│ starts_succeeded              {starts_succeeded:>6}   (reached pipeline)")
    print(f"│ start_failed (job doc)        {start_failed_total:>6}")
    for code, n in sorted(start_failed_breakdown.items(), key=lambda x: -x[1]):
        print(f"│    - {code:<28} {n:>6}")
    print(f"│ start_failed (funnel events)  {sf_events:>6}   (includes 402/422 that never created a job)")
    for code, n in sorted(sf_event_codes.items(), key=lambda x: -x[1]):
        print(f"│    - {code:<28} {n:>6}")
    print("└──────────────────────────────────────────────────────────────┘")
    print()
    print("┌─ OUTCOMES ───────────────────────────────────────────────────┐")
    print(f"│ completed                     {completed:>6}")
    print(f"│ pipeline_failed               {pipeline_failed:>6}")
    print(f"│ still_running                 {still_running:>6}")
    print(f"│ completion_rate_of_starts     {completion_rate_of_starts:>5}%")
    print(f"│ completion_rate_of_attempts   {completion_rate_of_attempts:>5}%")
    print("└──────────────────────────────────────────────────────────────┘")
    print()
    print("┌─ PIPELINE FAILURES BY CODE ──────────────────────────────────┐")
    if pipeline_codes:
        for code, n in pipeline_codes.items():
            pct = round(n / pipeline_failed * 100, 1) if pipeline_failed else 0.0
            print(f"│ {code:<28} {n:>4}  ({pct}%)")
    else:
        print("│ (none — zero post-start failures in window)                  │")
    print(f"│ timeout_kills (RENDER_TIMEOUT){timeout_kills:>6}")
    print(f"│ stale_janitor (STALE_PIPELINE){stale_janitor:>6}")
    print("└──────────────────────────────────────────────────────────────┘")
    print()
    print("┌─ RENDER TIME (completed only) ───────────────────────────────┐")
    print(f"│ samples                       {len(render_seconds):>6}")
    print(f"│ median_render_seconds         {median_render}")
    print(f"│ p95_render_seconds            {p95_render}")
    print(f"│ max_render_seconds            {max_render}")
    if by_bucket:
        print(f"│ by_duration_bucket            {by_bucket}")
    print("└──────────────────────────────────────────────────────────────┘")
    print()
    print("┌─ USER ACTIONS ───────────────────────────────────────────────┐")
    print(f"│ downloads_clicked             {downloads_click:>6}")
    print(f"│ whatsapp_shares               {wa_shares:>6}")
    print(f"│ native_shares                 {native_shares:>6}")
    print(f"│ auto_requeued                 {retry_events:>6}")
    print(f"│ jobs_with_manual_retry        {manual_retries:>6}")
    print("└──────────────────────────────────────────────────────────────┘")
    print()

    # ── Bottleneck statement (mandatory) ──────────────────────────────────
    print("┌─ BOTTLENECK STATEMENT (founder-mandatory closer) ────────────┐")

    # Simple decision tree:
    #  1. If starts_attempted is 0 → distribution bottleneck
    #  2. If start_failed_total / starts_attempted > 0.20 → start-side bottleneck
    #  3. If pipeline_failed / starts_succeeded > 0.10 → pipeline-side
    #  4. If completed but downloads_clicked == 0 → result-page bottleneck
    #  5. Else → distribution
    largest = "unknown"
    lift = "unknown"
    confidence = "Low"

    if starts_attempted == 0:
        largest = "Distribution — no starts in window."
        lift = "+N/A (no traffic to optimize)"
        confidence = "High"
    elif starts_attempted and (start_failed_total / starts_attempted) > 0.20:
        top_start_code = max(start_failed_breakdown.items(), key=lambda x: x[1])[0] \
            if start_failed_breakdown else "UNKNOWN"
        largest = f"Start-side failures ({top_start_code})"
        rec_fails_prevented = start_failed_breakdown.get(top_start_code, 0)
        lift = f"+{round(rec_fails_prevented / starts_attempted * 100, 1)} pts on start success"
        confidence = "High" if starts_attempted >= 20 else "Medium"
    elif starts_succeeded and (pipeline_failed / starts_succeeded) > 0.10:
        top_pipe = max(pipeline_codes.items(), key=lambda x: x[1])[0] if pipeline_codes else "UNKNOWN"
        largest = f"Pipeline failures ({top_pipe})"
        potential_recovered = int(pipeline_codes.get(top_pipe, 0) * 0.65)
        lift = f"+{round(potential_recovered / starts_succeeded * 100, 1)} pts on completion rate (65% retry success assumed)"
        confidence = "High" if pipeline_failed >= 10 else "Medium"
    elif completed and downloads_click == 0:
        largest = "Result-page: zero downloads despite completed trailers."
        lift = "Cannot be quantified without knowing what users expected"
        confidence = "Medium"
    elif completed:
        dl_rate = round(downloads_click / completed * 100, 1)
        share_rate = round((wa_shares + native_shares) / completed * 100, 1)
        if share_rate < 5:
            largest = "Distribution — completed trailers don't get shared."
            lift = "+10-30 pts view-to-share with better share-surface UX (projection, not verified)"
            confidence = "Medium"
        elif dl_rate < 20:
            largest = "Result-page friction: low download-click rate."
            lift = f"+{20 - dl_rate} pts on download conversion"
            confidence = "Medium"
        else:
            largest = "No single bottleneck in 48h window — all stages healthy."
            lift = "N/A — keep shipping distribution."
            confidence = "Medium"
    else:
        largest = "No completed trailers in 48h window."
        lift = "Cannot compute — need completions first"
        confidence = "Low"

    print(f"│ Single largest bottleneck now is: {largest}")
    print(f"│ Expected lift if fixed first:     {lift}")
    print(f"│ Confidence:                       {confidence}")
    print("└──────────────────────────────────────────────────────────────┘")
    print()

    client.close()


if __name__ == "__main__":
    asyncio.run(main())
