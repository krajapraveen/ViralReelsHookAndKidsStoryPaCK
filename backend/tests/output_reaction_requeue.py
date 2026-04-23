"""Re-queue missing stories from the reaction run — with retry on timeout."""
import os, sys, json, time, urllib.request
from pathlib import Path
from dotenv import load_dotenv
load_dotenv('/app/backend/.env')

API_BASE = "http://localhost:8001"

STORIES = [
    ("kids_bedtime", "kids", "watercolor", "toddler", "narrator_warm",
     "Moon Bunny's Tickle Lullaby",
     "When the sky turned soft and purple, a sleepy little bunny with silver fur crept out of his tiny burrow. "
     "The moon giggled down at him and tickled his whiskers with a beam of magical light. "
     "Mommy rabbit brought a warm blanket stitched with tiny stars, and daddy rabbit hummed a quiet bedtime tune. "
     "The little bunny yawned, snuggled close, and whispered goodnight to every sleepy cricket in the meadow. "
     "He closed his eyes as the moon hugged him softly, and he drifted into a rainbow dream. "
     "In the magical dream, every silly cloud was a pillow and every giggle was a lullaby."),
    ("funny_cat", "kids", "cartoon_2d", "kids_5_8", "narrator_energetic",
     "Biscuit the Cat Steals the Spotlight",
     "Biscuit the orange cat decided today was the day he would become famous. "
     "He hopped onto the breakfast table and knocked over the toast with a dramatic silly paw flop. "
     "Then he tried to tickle the dog's nose, which made the dog sneeze pancakes across the kitchen. "
     "Biscuit sprinted onto the rainbow rug, spun in a magical wiggle, and posed like a fluffy king. "
     "The whole family giggled so hard they forgot about the ruined breakfast and took a hundred photos. "
     "By bedtime Biscuit had crowned himself the silliest, most magical internet cat in the world."),
    ("emotional_mother", "emotional", "watercolor", "all_ages", "narrator_calm",
     "The Last Song My Mother Sang",
     "On a quiet gray morning, a tear fell on the old piano keys as I remembered my mother's soft whisper. "
     "She used to sing to me every night, promising that love would always find its way home. "
     "I walked through the empty house and could almost feel her embrace in the warmth of the hallway. "
     "In the garden, I found the handkerchief she had given me, worn by wind and time and my quiet hope. "
     "At sunset I sat by her favorite window and hummed the lullaby she taught me when I was a child. "
     "For the first time since the goodbye, I forgave the silence — and her love filled the whole room."),
    ("school_nostalgia", "emotional", "cartoon_2d", "all_ages", "narrator_warm",
     "The Last Recess of Class 10B",
     "On the final afternoon of Class 10B, the school bell rang louder than it ever had before. "
     "Friends who had once fought over pencils now embraced in the corridor without saying a word. "
     "Someone opened the dusty windows, and laughter from every year we had lived there seemed to rush back in. "
     "We signed each other's shirts with promises no ink could truly hold, but we signed them anyway. "
     "The teachers stood at the gate and pretended not to cry, the way they had pretended not to notice our jokes. "
     "We walked out of the gate as strangers to the future, carrying a childhood we would spend forever missing."),
    ("motivational_comeback", "cinematic", "3d_pixar", "teen", "narrator_dramatic",
     "The Day I Stopped Quitting",
     "For years I collected failures like other people collect achievements — silent, heavy, and unseen. "
     "I watched others stand on stages I had given up reaching and I told myself their luck was different. "
     "Then one morning I woke up and refused the comfortable lie of not trying anymore. "
     "I built a small plan, showed up on the hardest day, and kept showing up on the harder days that followed. "
     "The breakthrough did not arrive like thunder — it arrived like a slow sunrise I almost missed. "
     "Today I am living the comeback I once stopped believing was possible."),
    ("breakup_revenge", "emotional", "watercolor", "teen", "narrator_calm",
     "She Became the Life He Lost",
     "The night he chose to leave, she cried just once and then closed a door she would never open again. "
     "She poured the love she had tried to give him into her own life, her craft, her mornings, her promises. "
     "One by one she built the rooms of a future that had no space for his half-hearted excuses. "
     "Months later she saw her name on a stage he had always dreamed of and never dared to climb. "
     "He reached out with a nostalgic whisper, but her heart was already full of its own quiet thunder. "
     "She did not seek revenge — she became a life so bright that his absence looked exactly like a mistake."),
    ("baby_animal_rescue", "emotional", "watercolor", "kids_5_8", "narrator_warm",
     "The Tiny Puppy in the Rain",
     "On a cold gray evening, a tiny brown puppy shivered under a bench with a tear frozen on his nose. "
     "A little girl on her way home stopped, took off her own jacket, and wrapped the puppy in its warmth. "
     "She whispered a small promise into his floppy ear and carried him home through the endless rain. "
     "At home her family made a soft bed, warmed a bowl of milk, and gave the puppy a name full of hope. "
     "The puppy slept and slept, and in the morning he wagged his tail for the first time in many days. "
     "From that day forward, the little girl and the tiny puppy were never alone in any kind of weather."),
    ("billionaire_success_fantasy", "cinematic", "3d_pixar", "teen", "narrator_dramatic",
     "The Boy Who Outworked Silicon Valley",
     "In a two-room apartment above a noisy street, a sleepless boy sketched impossible empires on napkins. "
     "The city laughed at his ambition, the banks laughed at his pitch, and his friends slowly drifted away. "
     "He built his first prototype in a closet, shipped it before it was ready, and learned in public. "
     "Years passed in a blur of hard climbs, smart bets, late-night demos, and the slow grind of winning. "
     "One morning he stood at the top of a skyline and realized the little napkin sketches had come true. "
     "The same city that had laughed now whispered his name — and he smiled because he remembered it all."),
]


def http_post(url, body, token=None, timeout=120):
    req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"),
                                 headers={"Content-Type": "application/json"}, method="POST")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def login():
    return http_post(f"{API_BASE}/api/auth/login",
                     {"email": "admin@creatorstudio.ai", "password": "Cr3@t0rStud!o#2026"})["token"]


def queue_with_retry(token, cat, pacing, style, age, voice, title, text, retries=5):
    payload = {"title": title, "story_text": text, "animation_style": style,
               "age_group": age, "voice_preset": voice, "include_watermark": False,
               "pacing_mode": pacing}
    for attempt in range(retries):
        try:
            r = http_post(f"{API_BASE}/api/pipeline/create", payload, token=token, timeout=90)
            return r.get("job_id")
        except Exception as e:
            print(f"  retry {attempt+1}/{retries} [{cat}]: {e}")
            time.sleep(20)
    return None


def main():
    token = login()
    print(f"✓ Logged in")
    from pymongo import MongoClient
    db = MongoClient(os.environ['MONGO_URL'])[os.environ['DB_NAME']]

    # Check which categories already have a COMPLETED or PROCESSING or QUEUED job from today
    from datetime import datetime, timezone, timedelta
    since = datetime.now(timezone.utc) - timedelta(hours=3)
    existing = {}
    for j in db.pipeline_jobs.find({"user_id":"ddd17dff-5015-4d55-90f8-e376da5b35cf","created_at":{"$gt":since}}, {"job_id":1,"title":1,"status":1}):
        # Match by title prefix
        existing.setdefault(j["title"], []).append((j["job_id"], j["status"]))

    queued = {}
    for cat, pacing, style, age, voice, title, text in STORIES:
        good = [(jid, st) for (jid, st) in existing.get(title, []) if st in ("COMPLETED","PROCESSING","QUEUED")]
        if good:
            print(f"  skip [{cat}] — already have {good[0][1]} {good[0][0][:12]}")
            queued[cat] = good[0][0]
            continue
        jid = queue_with_retry(token, cat, pacing, style, age, voice, title, text)
        if jid:
            print(f"  queued [{cat:<30}] pacing={pacing:<9} {jid[:12]}")
            queued[cat] = jid
        else:
            print(f"  FAILED [{cat}]")
        time.sleep(3)

    # Poll
    print(f"\nPolling {len(queued)} jobs...")
    deadline = time.time() + 1800
    done = set()
    while time.time() < deadline and len(done) < len(queued):
        time.sleep(15)
        for cat, jid in queued.items():
            if jid in done:
                continue
            j = db.pipeline_jobs.find_one({"job_id": jid}, {"_id":0,"status":1,"progress":1})
            if j and j["status"] in ("COMPLETED", "FAILED"):
                done.add(jid)
                print(f"  done [{cat:<28}] {j['status']} @ {j.get('progress')}%")

    # Final report
    print("\n" + "="*100)
    print(f"{'CATEGORY':<28} {'STATUS':<10} {'DUR':<8} {'SIZE':<7} {'R2 URL'}")
    print("="*100)
    results = []
    import subprocess, re
    for cat, jid in queued.items():
        j = db.pipeline_jobs.find_one({"job_id": jid}, {"_id":0})
        rp = j.get("render_path")
        dur, sz = "?", "?"
        if rp and os.path.exists(rp):
            pr = subprocess.run(["ffmpeg","-i",rp], capture_output=True, text=True, timeout=15)
            m = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", pr.stderr)
            if m:
                dur = f"{int(m.group(1))*3600 + int(m.group(2))*60 + float(m.group(3)):.1f}s"
            sz = f"{round(os.path.getsize(rp)/1024/1024, 1)}MB"
        url = j.get("output_url","") or ""
        print(f"{cat:<28} {j.get('status'):<10} {dur:<8} {sz:<7} {url[:80]}")
        results.append({"category":cat, "job_id":jid, "title":j.get("title"), "pacing_mode":j.get("pacing_mode"),
                        "animation_style":j.get("animation_style"), "status":j.get("status"),
                        "output_url":url, "duration":dur, "size":sz})
    print("="*100)

    out_path = Path(f"/app/test_reports/output_reaction_10_final_{int(time.time())}.json")
    out_path.write_text(json.dumps({"jobs": results}, indent=2, default=str))
    print(f"\nReport: {out_path}")


if __name__ == "__main__":
    main()
