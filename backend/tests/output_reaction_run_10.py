"""
Output Reaction Run — 10 public stories across categories.
Goal: push real outputs into the world, watch humans react.
Does NOT modify backend code. Just queues jobs via the existing pipeline.

Usage (from /app/backend):
    SMOKE_LOCAL=1 python tests/output_reaction_run_10.py
Report lands at:
    /app/test_reports/output_reaction_run_10_<ts>.json
"""
import os
import sys
import json
import time
import urllib.request
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
load_dotenv("/app/backend/.env")
from pymongo import MongoClient
_db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]

FRONTEND_ENV = Path("/app/frontend/.env")
API_BASE = None
for line in FRONTEND_ENV.read_text().splitlines():
    if line.startswith("REACT_APP_BACKEND_URL="):
        API_BASE = line.split("=", 1)[1].strip()
        break
if os.environ.get("SMOKE_LOCAL") == "1":
    API_BASE = "http://localhost:8001"
if not API_BASE:
    print("Missing REACT_APP_BACKEND_URL"); sys.exit(1)

ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "Cr3@t0rStud!o#2026"

# 10 categories the founder specified. Prompts are tuned to trigger pacing detection
# and produce emotionally-shaped outputs within existing content policy.
STORIES = [
    {
        "category": "kids_bedtime",
        "pacing_mode": "kids",
        "animation_style": "watercolor",
        "age_group": "toddler",
        "voice_preset": "narrator_warm",
        "title": "Moon Bunny's Tickle Lullaby",
        "story_text": (
            "When the sky turned soft and purple, a sleepy little bunny with silver fur crept out of his tiny burrow. "
            "The moon giggled down at him and tickled his whiskers with a beam of magical light. "
            "Mommy rabbit brought a warm blanket stitched with tiny stars, and daddy rabbit hummed a quiet bedtime tune. "
            "The little bunny yawned, snuggled close, and whispered goodnight to every sleepy cricket in the meadow. "
            "He closed his eyes as the moon hugged him softly, and he drifted into a rainbow dream. "
            "In the magical dream, every silly cloud was a pillow and every giggle was a lullaby."
        ),
    },
    {
        "category": "funny_cat",
        "pacing_mode": "kids",
        "animation_style": "cartoon_2d",
        "age_group": "kids_5_8",
        "voice_preset": "narrator_energetic",
        "title": "Biscuit the Cat Steals the Spotlight",
        "story_text": (
            "Biscuit the orange cat decided today was the day he would become famous. "
            "He hopped onto the breakfast table and knocked over the toast with a dramatic silly paw flop. "
            "Then he tried to tickle the dog's nose, which made the dog sneeze pancakes across the kitchen. "
            "Biscuit sprinted onto the rainbow rug, spun in a magical wiggle, and posed like a fluffy king. "
            "The whole family giggled so hard they forgot about the ruined breakfast and took a hundred photos. "
            "By bedtime Biscuit had crowned himself the silliest, most magical internet cat in the world."
        ),
    },
    {
        "category": "emotional_mother",
        "pacing_mode": "emotional",
        "animation_style": "watercolor",
        "age_group": "all_ages",
        "voice_preset": "narrator_calm",
        "title": "The Last Song My Mother Sang",
        "story_text": (
            "On a quiet gray morning, a tear fell on the old piano keys as I remembered my mother's soft whisper. "
            "She used to sing to me every night, promising that love would always find its way home. "
            "I walked through the empty house and could almost feel her embrace in the warmth of the hallway. "
            "In the garden, I found the handkerchief she had given me, worn by wind and time and my quiet hope. "
            "At sunset I sat by her favorite window and hummed the lullaby she taught me when I was a child. "
            "For the first time since the goodbye, I forgave the silence — and her love filled the whole room."
        ),
    },
    {
        "category": "horror_short",
        "pacing_mode": "cinematic",
        "animation_style": "comic_book",
        "age_group": "teen",
        "voice_preset": "narrator_dramatic",
        "title": "Footsteps in Apartment 14",
        "story_text": (
            "Every night at three seventeen, soft footsteps passed the door of apartment fourteen and stopped. "
            "On the first night I told myself it was the old pipes. On the second night I started to listen harder. "
            "On the third night I opened the door and found nothing but a hallway holding its breath. "
            "The fourth night I noticed the footsteps were not walking away — they were waiting. "
            "When I finally gathered the courage to look through the peephole, a pale eye was looking back at me. "
            "The hallway light flickered, and a voice I knew too well whispered my name through the door."
        ),
    },
    {
        "category": "motivational_comeback",
        "pacing_mode": "cinematic",
        "animation_style": "3d_pixar",
        "age_group": "teen",
        "voice_preset": "narrator_dramatic",
        "title": "The Day I Stopped Quitting",
        "story_text": (
            "For years I collected failures like other people collect achievements — silent, heavy, and unseen. "
            "I watched others stand on stages I had given up reaching and I told myself their luck was different. "
            "Then one morning I woke up and refused the comfortable lie of not trying anymore. "
            "I built a small plan, showed up on the hardest day, and kept showing up on the harder days that followed. "
            "The breakthrough did not arrive like thunder — it arrived like a slow sunrise I almost missed. "
            "Today I am living the comeback I once stopped believing was possible."
        ),
    },
    {
        "category": "fantasy_magic",
        "pacing_mode": "cinematic",
        "animation_style": "3d_pixar",
        "age_group": "kids_9_12",
        "voice_preset": "narrator_dramatic",
        "title": "The Last Keeper of the Ember Stars",
        "story_text": (
            "In a valley older than all kingdoms, a young keeper guarded a grove of ember stars that whispered secrets. "
            "When the black wind came, the stars dimmed one by one and the valley began to forget its own magic. "
            "The keeper lifted her lantern, crossed the singing river, and climbed the mountain of forgotten names. "
            "At the summit she cupped the dying ember in her palms and sang the melody her grandmother had taught her. "
            "The stars flared awake, the valley remembered itself, and the black wind fled into the silent dawn. "
            "From that night on, every child born in the valley carried a tiny ember star hidden inside their heart."
        ),
    },
    {
        "category": "breakup_revenge",
        "pacing_mode": "emotional",
        "animation_style": "watercolor",
        "age_group": "teen",
        "voice_preset": "narrator_calm",
        "title": "She Became the Life He Lost",
        "story_text": (
            "The night he chose to leave, she cried just once and then closed a door she would never open again. "
            "She poured the love she had tried to give him into her own life, her craft, her mornings, her promises. "
            "One by one she built the rooms of a future that had no space for his half-hearted excuses. "
            "Months later she saw her name on a stage he had always dreamed of and never dared to climb. "
            "He reached out with a nostalgic whisper, but her heart was already full of its own quiet thunder. "
            "She did not seek revenge — she became a life so bright that his absence looked exactly like a mistake."
        ),
    },
    {
        "category": "school_nostalgia",
        "pacing_mode": "emotional",
        "animation_style": "cartoon_2d",
        "age_group": "all_ages",
        "voice_preset": "narrator_warm",
        "title": "The Last Recess of Class 10B",
        "story_text": (
            "On the final afternoon of Class 10B, the school bell rang louder than it ever had before. "
            "Friends who had once fought over pencils now embraced in the corridor without saying a word. "
            "Someone opened the dusty windows, and laughter from every year we had lived there seemed to rush back in. "
            "We signed each other's shirts with promises no ink could truly hold, but we signed them anyway. "
            "The teachers stood at the gate and pretended not to cry, the way they had pretended not to notice our jokes. "
            "We walked out of the gate as strangers to the future, carrying a childhood we would spend forever missing."
        ),
    },
    {
        "category": "baby_animal_rescue",
        "pacing_mode": "emotional",
        "animation_style": "watercolor",
        "age_group": "kids_5_8",
        "voice_preset": "narrator_warm",
        "title": "The Tiny Puppy in the Rain",
        "story_text": (
            "On a cold gray evening, a tiny brown puppy shivered under a bench with a tear frozen on his nose. "
            "A little girl on her way home stopped, took off her own jacket, and wrapped the puppy in its warmth. "
            "She whispered a small promise into his floppy ear and carried him home through the endless rain. "
            "At home her family made a soft bed, warmed a bowl of milk, and gave the puppy a name full of hope. "
            "The puppy slept and slept, and in the morning he wagged his tail for the first time in many days. "
            "From that day forward, the little girl and the tiny puppy were never alone in any kind of weather."
        ),
    },
    {
        "category": "billionaire_success_fantasy",
        "pacing_mode": "cinematic",
        "animation_style": "3d_pixar",
        "age_group": "teen",
        "voice_preset": "narrator_dramatic",
        "title": "The Boy Who Outworked Silicon Valley",
        "story_text": (
            "In a two-room apartment above a noisy street, a sleepless boy sketched impossible empires on napkins. "
            "The city laughed at his ambition, the banks laughed at his pitch, and his friends slowly drifted away. "
            "He built his first prototype in a closet, shipped it before it was ready, and learned in public. "
            "Years passed in a blur of hard climbs, smart bets, late-night demos, and the slow grind of winning. "
            "One morning he stood at the top of a skyline and realized the little napkin sketches had come true. "
            "The same city that had laughed now whispered his name — and he smiled because he remembered it all."
        ),
    },
]


def http_post(url, body, token=None, timeout=60):
    req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"),
                                 headers={"Content-Type": "application/json"}, method="POST")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def login():
    return http_post(f"{API_BASE}/api/auth/login",
                     {"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})["token"]


def queue_story(token, case):
    payload = {
        "title": case["title"],
        "story_text": case["story_text"],
        "animation_style": case["animation_style"],
        "age_group": case["age_group"],
        "voice_preset": case["voice_preset"],
        "include_watermark": False,
        "pacing_mode": case["pacing_mode"],
    }
    r = http_post(f"{API_BASE}/api/pipeline/create", payload, token=token, timeout=60)
    return r.get("job_id")


def wait_for(job_ids, max_wall_sec=1800):
    """Wait for all job_ids to reach COMPLETED or FAILED. Yields status snapshots."""
    deadline = time.time() + max_wall_sec
    done = set()
    while time.time() < deadline and len(done) < len(job_ids):
        time.sleep(10)
        status_snapshot = {}
        for jid in job_ids:
            j = _db.pipeline_jobs.find_one({"job_id": jid},
                                           {"_id": 0, "status": 1, "progress": 1, "current_stage": 1})
            st = (j or {}).get("status")
            status_snapshot[jid] = {"status": st, "progress": (j or {}).get("progress")}
            if st in ("COMPLETED", "FAILED"):
                done.add(jid)
        # Print compact snapshot
        line = " | ".join(f"{jid[:8]}:{v['status'][:4] if v['status'] else '?'} {v['progress'] or 0}%"
                          for jid, v in status_snapshot.items())
        print(f"  [{int(time.time())}] {line}")
    return done


def collect_results(jobs_map):
    """jobs_map: {category: (job_id, case_meta)} -> full probe report"""
    results = []
    for cat, (jid, case) in jobs_map.items():
        j = _db.pipeline_jobs.find_one({"job_id": jid}, {"_id": 0})
        if not j:
            results.append({"category": cat, "job_id": jid, "error": "job_not_found"})
            continue
        rp = j.get("render_path")
        probe = {}
        if rp and os.path.exists(rp):
            import subprocess, re
            pr = subprocess.run(["ffmpeg", "-i", rp], capture_output=True, text=True, timeout=15)
            t = pr.stderr
            dur_m = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", t)
            aud_m = re.search(r"Audio:\s*(\w+)(?:\s*\(([\w\s]+)\))?.*?(\d+)\s*Hz,\s*(\w+)", t)
            probe = {
                "duration_sec": (int(dur_m.group(1))*3600 + int(dur_m.group(2))*60 +
                                 float(dur_m.group(3))) if dur_m else None,
                "audio": f"{aud_m.group(1)}/{aud_m.group(2) or '?'}/{aud_m.group(3)}Hz/{aud_m.group(4)}"
                         if aud_m else None,
                "size_mb": round(os.path.getsize(rp) / 1024 / 1024, 2),
            }
            # faststart check
            with open(rp, "rb") as f:
                head = f.read(1024 * 256)
            probe["faststart"] = head.find(b"moov") != -1 and (
                head.find(b"mdat") == -1 or head.find(b"moov") < head.find(b"mdat"))
        results.append({
            "category": cat,
            "title": case["title"],
            "pacing_mode": case["pacing_mode"],
            "animation_style": case["animation_style"],
            "job_id": jid,
            "slug": j.get("slug"),
            "status": j.get("status"),
            "error": j.get("error"),
            "output_url": j.get("output_url"),
            "render_path": rp,
            "probe": probe,
            "scenes": j.get("estimated_scenes"),
            "timing_ms": j.get("timing"),
        })
    return results


def main():
    print(f"API = {API_BASE}")
    token = login()
    print(f"✓ Logged in as {ADMIN_EMAIL}")

    jobs_map = {}  # category -> (job_id, case)
    for case in STORIES:
        try:
            jid = queue_story(token, case)
            jobs_map[case["category"]] = (jid, case)
            print(f"  queued [{case['category']:<30}] pacing={case['pacing_mode']:<9} job={jid[:12]}")
        except Exception as e:
            print(f"  FAILED queue [{case['category']}]: {e}")
        time.sleep(1)

    job_ids = [v[0] for v in jobs_map.values() if v[0]]
    print(f"\nWaiting for {len(job_ids)} jobs to complete (up to 30 min)...")
    wait_for(job_ids, max_wall_sec=1800)

    results = collect_results(jobs_map)

    out = {
        "started_at": datetime.utcnow().isoformat() + "Z",
        "api_base": API_BASE,
        "total_jobs": len(results),
        "jobs": results,
    }
    out_path = Path(f"/app/test_reports/output_reaction_run_10_{int(time.time())}.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2, default=str))

    # Console summary
    print("\n" + "=" * 100)
    print(f"{'CATEGORY':<28} {'STATUS':<10} {'DUR':<8} {'SIZE':<7} {'SCENES':<6} {'TITLE'}")
    print("=" * 100)
    for r in results:
        p = r.get("probe") or {}
        dur = f"{p.get('duration_sec', '?')}s" if p.get("duration_sec") else "?"
        sz = f"{p.get('size_mb', '?')}MB" if p.get("size_mb") else "?"
        print(f"{r['category']:<28} {r.get('status', '?'):<10} {dur:<8} {sz:<7} {r.get('scenes', '?'):<6} {r.get('title', '')[:44]}")
    print("=" * 100)
    print(f"\nR2 URLs:")
    for r in results:
        if r.get("output_url"):
            print(f"  [{r['category']:<28}] {r['output_url']}")
    print(f"\nFull report: {out_path}")


if __name__ == "__main__":
    main()
