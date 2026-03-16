"""
Content Seeding Script — Phase A (40 videos)
Creates real-looking seeded content for the Visionary Suite platform.
Each entry has structured metadata (title, slug, prompt, category, tags, thumbnail).
"""
import asyncio
import uuid
import random
import re
from datetime import datetime, timezone, timedelta

import motor.motor_asyncio
from dotenv import load_dotenv
import os

load_dotenv("/app/backend/.env")
MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]

client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

SYSTEM_USER_ID = "visionary-ai-system"
SYSTEM_USER_NAME = "Visionary AI"

# 40 viral prompts across 6 categories
SEED_DATA = [
    # ── Fantasy (7) ──
    {"title": "Dragon Guardians of the Crystal Valley", "prompt": "A family of ancient dragons protects a hidden crystal valley where magical creatures live in harmony. When a dark sorcerer threatens to steal the crystals, the youngest dragon must find courage to defend their home.", "category": "Fantasy", "tags": ["dragon", "fantasy", "magic", "adventure", "crystal"], "style": "3d_pixar", "age_group": "kids"},
    {"title": "The Enchanted Forest Kingdom", "prompt": "Deep within an enchanted forest, tiny fairy kingdoms wage a playful war of pranks and magic spells. A lost human child accidentally stumbles into their world and must help unite the rival fairy clans.", "category": "Fantasy", "tags": ["fairy", "forest", "fantasy", "kids", "magic"], "style": "watercolor", "age_group": "kids"},
    {"title": "Wizard's Apprentice Academy", "prompt": "A young wizard arrives at a floating academy in the clouds to learn the art of spell-casting. Each lesson brings unexpected chaos — from runaway potions to talking textbooks.", "category": "Fantasy", "tags": ["wizard", "magic", "academy", "adventure", "cinematic"], "style": "cartoon_2d", "age_group": "kids"},
    {"title": "The Phoenix and the Star Child", "prompt": "A phoenix guides a star-born child across galaxies to find their true home. Together they face cosmic storms, singing nebulas, and ancient space guardians.", "category": "Fantasy", "tags": ["phoenix", "space", "fantasy", "cinematic", "epic"], "style": "3d_pixar", "age_group": "all"},
    {"title": "Underwater Castle of the Merfolk", "prompt": "Beneath the ocean waves lies a magnificent castle of pearl and coral, ruled by wise merfolk. A curious young mermaid discovers a secret portal to the surface world.", "category": "Fantasy", "tags": ["mermaid", "underwater", "castle", "adventure", "magical"], "style": "watercolor", "age_group": "kids"},
    {"title": "The Last Unicorn of Eldergrove", "prompt": "In a dying magical forest, the last unicorn sets out on a quest to restore the ancient Elder Trees. Along the way, she befriends unlikely allies: a clever fox and a grumpy troll.", "category": "Fantasy", "tags": ["unicorn", "quest", "forest", "fantasy", "heartwarming"], "style": "anime", "age_group": "kids"},
    {"title": "Shadow Warriors of the Eclipse", "prompt": "During a rare cosmic eclipse, shadow warriors emerge from another dimension. Only a team of young elemental mages can send them back before the portal closes forever.", "category": "Fantasy", "tags": ["warriors", "eclipse", "magic", "action", "epic"], "style": "anime", "age_group": "teen"},

    # ── Kids (7) ──
    {"title": "Benny the Brave Little Bear", "prompt": "Benny is a small bear who is afraid of everything — thunder, the dark, even butterflies. But when his forest friends need help during a big storm, Benny discovers bravery comes in all sizes.", "category": "Kids", "tags": ["bear", "courage", "friendship", "kids story", "heartwarming"], "style": "cartoon_2d", "age_group": "kids"},
    {"title": "The Rainbow Rocket Ship", "prompt": "Three best friends build a rocket ship from cardboard boxes in their backyard. To their amazement, it actually flies! They zoom through space visiting candy planets and rainbow nebulas.", "category": "Kids", "tags": ["space", "friendship", "imagination", "kids", "adventure"], "style": "3d_pixar", "age_group": "kids"},
    {"title": "Lily's Magical Garden", "prompt": "Every night when Lily falls asleep, her backyard garden comes alive with talking flowers, dancing mushrooms, and a wise old oak tree who tells the most wonderful stories.", "category": "Kids", "tags": ["garden", "magic", "bedtime", "kids", "nature"], "style": "watercolor", "age_group": "kids"},
    {"title": "Captain Cluck's Chicken Adventure", "prompt": "Captain Cluck is no ordinary chicken — she's a pirate captain sailing the seven seas with her crew of farm animals. Their mission: find the legendary Golden Egg before sunset.", "category": "Kids", "tags": ["pirate", "chicken", "funny", "adventure", "kids"], "style": "cartoon_2d", "age_group": "kids"},
    {"title": "The Dinosaur Who Loved Pancakes", "prompt": "A friendly T-Rex opens a pancake restaurant in a city full of dinosaurs. Business booms when he invents the legendary Dino-Stack — a tower of 100 pancakes with maple syrup waterfalls.", "category": "Kids", "tags": ["dinosaur", "funny", "food", "kids", "comedy"], "style": "3d_pixar", "age_group": "kids"},
    {"title": "Starlight the Sleepy Puppy", "prompt": "Starlight is a tiny golden puppy who falls asleep in the funniest places — on top of cakes, inside shoes, and once even on the mayor's head. A heartwarming bedtime story about a lovable pup.", "category": "Kids", "tags": ["puppy", "bedtime", "cute", "funny", "heartwarming"], "style": "watercolor", "age_group": "kids"},
    {"title": "The Cloud Kingdom", "prompt": "Above the tallest mountain, a kingdom of clouds exists where fluffy cloud creatures shape the weather. A young cloud named Nimbus dreams of creating the most beautiful sunset ever seen.", "category": "Kids", "tags": ["clouds", "imagination", "dreamy", "kids", "nature"], "style": "watercolor", "age_group": "kids"},

    # ── Luxury / Lifestyle (6) ──
    {"title": "Dubai Billionaire Morning Routine", "prompt": "A cinematic day-in-the-life of a Dubai billionaire: waking up in a penthouse overlooking the Palm, driving a gold Lamborghini, and closing deals on a superyacht at sunset.", "category": "Luxury", "tags": ["luxury", "dubai", "billionaire", "lifestyle", "cinematic"], "style": "realistic", "age_group": "all"},
    {"title": "Monaco Grand Prix Luxury Experience", "prompt": "Experience the Monaco Grand Prix from the most exclusive vantage points — rooftop champagne terraces, superyacht decks in the harbor, and VIP pit lane access with Formula 1 legends.", "category": "Luxury", "tags": ["monaco", "F1", "luxury", "superyacht", "racing"], "style": "realistic", "age_group": "all"},
    {"title": "The Million Dollar Sunset", "prompt": "A cinematic journey through the world's most expensive sunset views — from Santorini cliff hotels to Maldivian overwater villas to a private jet above the clouds.", "category": "Luxury", "tags": ["sunset", "luxury", "travel", "cinematic", "aesthetic"], "style": "realistic", "age_group": "all"},
    {"title": "Tokyo After Dark: Neon Dreams", "prompt": "Explore Tokyo's electric nightlife in a cinematic neon-soaked journey through Shibuya crossing, hidden izakayas, and rooftop bars with views of the glowing skyline.", "category": "Luxury", "tags": ["tokyo", "neon", "nightlife", "cinematic", "aesthetic"], "style": "anime", "age_group": "all"},
    {"title": "Swiss Alps Winter Palace", "prompt": "A day at the world's most exclusive alpine resort: helicopter skiing over pristine powder, a gourmet lunch in an ice cave, and relaxing in an infinity hot spring overlooking the Matterhorn.", "category": "Luxury", "tags": ["alps", "luxury", "winter", "skiing", "travel"], "style": "realistic", "age_group": "all"},
    {"title": "Vintage Supercar Collection Tour", "prompt": "Take a cinematic tour of the world's most valuable vintage supercar collection: a 1962 Ferrari 250 GTO, a Bugatti Type 57, and a Lamborghini Miura, each with their legendary stories.", "category": "Luxury", "tags": ["supercar", "vintage", "luxury", "ferrari", "cinematic"], "style": "realistic", "age_group": "all"},

    # ── Motivational (7) ──
    {"title": "From Zero to CEO: A Founder's Journey", "prompt": "The cinematic story of a young entrepreneur who goes from sleeping on a friend's couch to building a billion-dollar company, overcoming rejection, failure, and self-doubt along the way.", "category": "Motivational", "tags": ["startup", "motivation", "success", "entrepreneur", "inspiration"], "style": "realistic", "age_group": "all"},
    {"title": "The 5 AM Club: Transform Your Life", "prompt": "A powerful motivational story about how waking up at 5 AM changed everything — the discipline, the clarity, and the unstoppable momentum that comes from owning the first hour of your day.", "category": "Motivational", "tags": ["motivation", "productivity", "discipline", "success", "mindset"], "style": "realistic", "age_group": "all"},
    {"title": "You Are Stronger Than You Think", "prompt": "A deeply emotional motivational story about a person who lost everything — their job, their home, their confidence — and rebuilt their life stronger than ever. A story of resilience.", "category": "Motivational", "tags": ["resilience", "motivation", "comeback", "emotional", "inspiration"], "style": "realistic", "age_group": "all"},
    {"title": "The 10,000 Hour Rule", "prompt": "Visualizing what 10,000 hours of practice looks like — from the first awkward attempts to absolute mastery. A cinematic journey through the dedication behind every world-class performer.", "category": "Motivational", "tags": ["mastery", "practice", "motivation", "dedication", "inspiration"], "style": "realistic", "age_group": "all"},
    {"title": "Why Most People Give Up at 90%", "prompt": "A powerful visual story showing how most people quit right before the breakthrough. The last 10% of any journey is the hardest — but it's where all the rewards are waiting.", "category": "Motivational", "tags": ["persistence", "motivation", "never quit", "success", "mindset"], "style": "realistic", "age_group": "all"},
    {"title": "The Compound Effect: Small Steps, Giant Leaps", "prompt": "How tiny daily improvements of just 1% compound over time to create extraordinary results. Visualizing the exponential growth curve of consistent effort.", "category": "Motivational", "tags": ["compound effect", "growth", "motivation", "consistency", "success"], "style": "realistic", "age_group": "all"},
    {"title": "Letters to My Younger Self", "prompt": "A heartfelt cinematic letter written by a successful person to their younger self, sharing the lessons they wish they knew earlier about courage, patience, and believing in yourself.", "category": "Motivational", "tags": ["reflection", "wisdom", "emotional", "motivation", "life lessons"], "style": "watercolor", "age_group": "all"},

    # ── Sci-Fi (6) ──
    {"title": "Last Human on Mars Colony", "prompt": "The year is 2157. The last human on a failing Mars colony must repair the life support systems while an AI companion debates whether humanity deserves to survive.", "category": "Sci-Fi", "tags": ["mars", "sci-fi", "AI", "survival", "futuristic"], "style": "3d_pixar", "age_group": "all"},
    {"title": "Cyberpunk Tokyo 2099", "prompt": "In Neo-Tokyo 2099, a rogue hacker discovers that the mega-corporation controlling the city is running a simulation. The only way to free millions of people is to crash the entire system.", "category": "Sci-Fi", "tags": ["cyberpunk", "tokyo", "hacker", "dystopia", "action"], "style": "anime", "age_group": "teen"},
    {"title": "First Contact: The Message", "prompt": "Humanity receives its first message from an alien civilization. The message contains just three words in every Earth language: 'We are coming.' The world must prepare for the unknown.", "category": "Sci-Fi", "tags": ["alien", "first contact", "suspense", "sci-fi", "epic"], "style": "realistic", "age_group": "all"},
    {"title": "Robot Dreams", "prompt": "A sentient robot working in a factory starts having vivid dreams about forests, oceans, and sunsets it has never seen. It begins to question what consciousness truly means.", "category": "Sci-Fi", "tags": ["robot", "consciousness", "AI", "philosophical", "emotional"], "style": "3d_pixar", "age_group": "all"},
    {"title": "The Time Loop Cafe", "prompt": "A barista discovers their coffee shop is stuck in a time loop. Every day resets at midnight. They must figure out the cosmic mystery before the loop collapses and erases the cafe from existence.", "category": "Sci-Fi", "tags": ["time loop", "mystery", "cafe", "sci-fi", "quirky"], "style": "anime", "age_group": "all"},
    {"title": "Quantum Heist", "prompt": "A team of quantum physicists-turned-thieves plan the ultimate heist: stealing a priceless artifact from a museum that exists in two dimensions simultaneously. One wrong move collapses reality.", "category": "Sci-Fi", "tags": ["heist", "quantum", "thriller", "sci-fi", "action"], "style": "realistic", "age_group": "all"},

    # ── Emotional (7) ──
    {"title": "The Last Letter", "prompt": "A grandmother writes one final letter to her grandchildren, sharing a lifetime of wisdom, love, and memories. Each paragraph is a scene from her extraordinary life.", "category": "Emotional", "tags": ["family", "love", "grandmother", "emotional", "heartwarming"], "style": "watercolor", "age_group": "all"},
    {"title": "Two Strangers on a Train", "prompt": "Two strangers meet on a night train across Europe. Through a single conversation, they share their deepest fears, biggest dreams, and discover they needed each other all along.", "category": "Emotional", "tags": ["strangers", "connection", "emotional", "romance", "cinematic"], "style": "realistic", "age_group": "all"},
    {"title": "The Dog Who Waited", "prompt": "A loyal golden retriever waits at the same park bench every evening for his owner who moved away. The neighborhood rallies to find the owner, leading to a tearful reunion.", "category": "Emotional", "tags": ["dog", "loyalty", "emotional", "heartwarming", "tearjerker"], "style": "watercolor", "age_group": "all"},
    {"title": "First Day of School", "prompt": "A parent's emotional journey through their child's first day of school — from the nervous morning preparation to the bittersweet goodbye at the school gate, realizing how fast time flies.", "category": "Emotional", "tags": ["parenting", "school", "emotional", "growing up", "family"], "style": "watercolor", "age_group": "all"},
    {"title": "The Piano in the Rain", "prompt": "An old piano sits abandoned in a rainy city square. A young musician sits down and begins to play a hauntingly beautiful melody that stops the entire city in its tracks.", "category": "Emotional", "tags": ["piano", "music", "rain", "emotional", "artistic"], "style": "anime", "age_group": "all"},
    {"title": "Voices of the Ocean", "prompt": "A marine biologist discovers that whales have been singing the same song for 10,000 years — a message from an ancient ocean civilization. A meditative, awe-inspiring journey beneath the waves.", "category": "Emotional", "tags": ["ocean", "whales", "nature", "meditation", "awe"], "style": "watercolor", "age_group": "all"},
    {"title": "When Stars Fall Silent", "prompt": "An astronaut floating alone above Earth receives news that her daughter spoke her first word — 'mama.' The most beautiful and lonely moment in space history.", "category": "Emotional", "tags": ["space", "motherhood", "emotional", "astronaut", "tearjerker"], "style": "realistic", "age_group": "all"},
]

# Use existing thumbnails from the showcase content for realistic appearance
EXISTING_THUMBNAILS = []


async def get_existing_thumbnails():
    """Grab thumbnail URLs from existing completed jobs for reuse."""
    jobs = await db.pipeline_jobs.find(
        {"status": "COMPLETED", "thumbnail_url": {"$exists": True, "$ne": ""}},
        {"_id": 0, "thumbnail_url": 1}
    ).limit(20).to_list(length=20)
    return [j["thumbnail_url"] for j in jobs if j.get("thumbnail_url")]


async def create_system_user():
    """Ensure the Visionary AI system user exists."""
    existing = await db.users.find_one({"id": SYSTEM_USER_ID})
    if not existing:
        await db.users.insert_one({
            "id": SYSTEM_USER_ID,
            "name": SYSTEM_USER_NAME,
            "username": "visionary-ai",
            "email": "ai@visionary-suite.com",
            "bio": "The official AI creator for Visionary Suite. Generating inspiring content daily.",
            "role": "system",
            "avatar_url": "",
            "is_verified": True,
            "created_at": datetime.now(timezone.utc),
        })
        print(f"Created system user: {SYSTEM_USER_NAME}")
    else:
        print(f"System user already exists: {SYSTEM_USER_NAME}")


def make_slug(title, job_id):
    slug_base = re.sub(r'[^\w\s-]', '', title.lower().strip())
    slug_base = re.sub(r'[\s_]+', '-', slug_base)
    slug_base = re.sub(r'-+', '-', slug_base)[:60].strip('-')
    return f"{slug_base}-{job_id[:8]}" if slug_base else job_id[:12]


async def seed_videos():
    """Create 40 seeded video entries with real metadata."""
    thumbnails = await get_existing_thumbnails()
    if not thumbnails:
        print("WARNING: No existing thumbnails found. Videos will have no thumbnails.")

    await create_system_user()

    # Check how many already seeded
    existing_count = await db.pipeline_jobs.count_documents({"user_id": SYSTEM_USER_ID})
    if existing_count >= 40:
        print(f"Already have {existing_count} seeded videos. Skipping Phase A seeding.")
        return

    created = 0
    base_date = datetime.now(timezone.utc) - timedelta(days=14)

    for i, item in enumerate(SEED_DATA):
        # Check if this title already exists
        existing = await db.pipeline_jobs.find_one({"title": item["title"], "user_id": SYSTEM_USER_ID})
        if existing:
            print(f"  Skipping existing: {item['title']}")
            continue

        job_id = str(uuid.uuid4())
        slug = make_slug(item["title"], job_id)

        # Distribute creation dates across the last 14 days
        created_at = base_date + timedelta(hours=random.randint(0, 336))

        # Random engagement metrics
        views = random.randint(5, 800)
        remix_count = random.randint(0, int(views * 0.25))

        # Use a random existing thumbnail
        thumbnail = random.choice(thumbnails) if thumbnails else ""

        # Generate fake but realistic scenes (3-5 per video)
        num_scenes = random.randint(3, 5)
        scenes = []
        for s_idx in range(num_scenes):
            scenes.append({
                "scene_number": s_idx + 1,
                "narration": f"Scene {s_idx + 1} of the story...",
                "image_url": thumbnail if thumbnail else "",
                "audio_url": "",
                "duration": random.uniform(3.0, 8.0),
            })

        doc = {
            "job_id": job_id,
            "user_id": SYSTEM_USER_ID,
            "slug": slug,
            "title": item["title"],
            "story_text": item["prompt"],
            "animation_style": item["style"],
            "age_group": item["age_group"],
            "category": item["category"],
            "tags": item["tags"],
            "status": "COMPLETED",
            "progress": 100,
            "scenes": scenes,
            "thumbnail_url": thumbnail,
            "views": views,
            "remix_count": remix_count,
            "created_at": created_at,
            "completed_at": created_at + timedelta(minutes=random.randint(1, 5)),
            "is_seeded": True,
        }

        await db.pipeline_jobs.insert_one(doc)
        created += 1
        print(f"  [{created}/{len(SEED_DATA)}] Seeded: {item['title']} [{item['category']}]")

    print(f"\nSeeding complete! Created {created} new videos.")
    total = await db.pipeline_jobs.count_documents({"user_id": SYSTEM_USER_ID})
    print(f"Total seeded videos: {total}")


if __name__ == "__main__":
    asyncio.run(seed_videos())
