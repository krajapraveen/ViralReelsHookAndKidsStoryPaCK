"""Seed the gallery with professional AI-generated showcase items.
All images are 100% AI-generated (Gemini Imagen 4.0) — zero copyright/legal/piracy issues.
These are original artworks owned entirely by the platform."""
import asyncio
import uuid
from datetime import datetime, timezone, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
import os

MONGO_URL = os.environ.get("MONGO_URL")
DB_NAME = os.environ.get("DB_NAME", "creatorstudio_production").strip('"')

SHOWCASE_ITEMS = [
    {
        "title": "Dragon Protects a Hidden Village",
        "story_text": "A friendly dragon watched over a small colorful village nestled on a hilltop. Every evening at sunset, the dragon curled around the village like a warm blanket, keeping the townspeople safe. The children loved climbing on its tail, and the dragon would gently breathe warm air to dry their laundry on cold days.",
        "animation_style": "cartoon_2d",
        "age_group": "kids_5_8",
        "thumbnail_url": "https://static.prod-images.emergentagent.com/jobs/d29dba27-ba90-4188-b2b5-0b75f69ea76d/images/a872e7715ba85b6197e0284e7c99f80a41ac2fd542033ef355b80dfdde7aa866.png",
        "remix_count": 142,
    },
    {
        "title": "Robot Exploring Mars",
        "story_text": "A curious little robot named Bolt landed on Mars with big, excited eyes. Walking across the red rocky terrain, Bolt discovered ancient crystals that glowed blue when touched. Looking up at Earth in the starry sky, Bolt sent a message home: 'Mars is beautiful. You should come visit.'",
        "animation_style": "3d_pixar",
        "age_group": "kids_8_12",
        "thumbnail_url": "https://static.prod-images.emergentagent.com/jobs/d29dba27-ba90-4188-b2b5-0b75f69ea76d/images/bf426f3d9d2a7bbac3318cb92270fbb00cd235294e4c0bc78d4bb1007827b7b3.png",
        "remix_count": 98,
    },
    {
        "title": "Magical Bedtime Forest Story",
        "story_text": "In a forest where mushrooms glowed and fireflies danced, a tiny fox cub found the perfect spot to sleep under the biggest, oldest tree. As moonlight filtered through the leaves, the tree whispered ancient lullabies that only those with kind hearts could hear. The little fox dreamed of flying.",
        "animation_style": "watercolor",
        "age_group": "kids_3_5",
        "thumbnail_url": "https://static.prod-images.emergentagent.com/jobs/d29dba27-ba90-4188-b2b5-0b75f69ea76d/images/a8a0e43d4cede87f383e6695d758daed26d17059583c24a4d4b30be236496545.png",
        "remix_count": 87,
    },
    {
        "title": "Underwater Kingdom Adventure",
        "story_text": "Deep beneath the sparkling ocean, a magnificent kingdom of coral castles and crystal towers thrived. Tropical fish of every color swam through archways while sea turtles carried messages between towers. The mer-people had lived in peace for a thousand years, protected by the gentle current.",
        "animation_style": "3d_pixar",
        "age_group": "kids_5_8",
        "thumbnail_url": "https://static.prod-images.emergentagent.com/jobs/d29dba27-ba90-4188-b2b5-0b75f69ea76d/images/a375c94249f29116bbdc5d252b4bb6a0ddb0fcf8ff10c8cd86bae0efd01a961f.png",
        "remix_count": 76,
    },
    {
        "title": "Superhero Origin Story",
        "story_text": "Five ordinary kids discovered glowing stones that gave them extraordinary powers. By dawn, they could fly over their city, leaving trails of light across the neon skyline. They made a pact: use their powers only to help others. The city had never felt safer than when these young heroes took to the sky.",
        "animation_style": "comic_book",
        "age_group": "kids_8_12",
        "thumbnail_url": "https://static.prod-images.emergentagent.com/jobs/d29dba27-ba90-4188-b2b5-0b75f69ea76d/images/350b1df7d754acbe6a1c441e5c173234d7761650ce38d22c92f694d519bd88e5.png",
        "remix_count": 65,
    },
    {
        "title": "Animal Friendship Tale",
        "story_text": "On the golden African savanna, a baby elephant discovered she could paint rainbows with her trunk. Giraffes, zebras, and birds gathered in amazement as brilliant colors arced across the sky. The elephant shared her gift freely, painting joy across the entire plain every afternoon at sunset.",
        "animation_style": "cartoon_2d",
        "age_group": "kids_3_5",
        "thumbnail_url": "https://static.prod-images.emergentagent.com/jobs/d29dba27-ba90-4188-b2b5-0b75f69ea76d/images/fe80be8f82d0d1bc31aebc6f9e8d68ae8ba50c461bf98db0c88d3583598cc93e.png",
        "remix_count": 54,
    },
    {
        "title": "Candy Pirate Adventure",
        "story_text": "Captain Whiskers sailed a magnificent ship made entirely of candy through cotton candy clouds. With a crew of adorable animal pirates, they searched for the legendary Lollipop Island where the sweetest treasure in all the seven skies was hidden. The parrot navigator spotted land through a gumdrop telescope.",
        "animation_style": "3d_pixar",
        "age_group": "kids_5_8",
        "thumbnail_url": "https://static.prod-images.emergentagent.com/jobs/d29dba27-ba90-4188-b2b5-0b75f69ea76d/images/c98915b0c37a14774dc792bea83ad907203f022f954b5c5a928cd43733f00eb4.png",
        "remix_count": 43,
    },
    {
        "title": "The Tiny Baker Mice",
        "story_text": "Behind the walls of a grand old bakery, a family of mice ran the most wonderful miniature kitchen. Wearing tiny chef hats and aprons, they baked the most incredible cakes and pastries. Their secret ingredient was love, and their golden oven made everything taste like a warm hug.",
        "animation_style": "watercolor",
        "age_group": "kids_3_5",
        "thumbnail_url": "https://static.prod-images.emergentagent.com/jobs/d29dba27-ba90-4188-b2b5-0b75f69ea76d/images/ba3e0ad163bfd7357e11a867f3afb26f32bafd0b2c82ffbfe55bea124f5683dd.png",
        "remix_count": 38,
    },
    {
        "title": "Princess Frost and the Ice Kingdom",
        "story_text": "Atop the highest frozen mountain stood a magnificent castle made entirely of sparkling ice crystals. Princess Frost and her loyal polar bear companion guarded the ancient magic that painted the aurora borealis across the northern sky every night, lighting up the world with green and purple wonder.",
        "animation_style": "anime_style",
        "age_group": "kids_5_8",
        "thumbnail_url": "https://static.prod-images.emergentagent.com/jobs/d29dba27-ba90-4188-b2b5-0b75f69ea76d/images/a1c635fa62475e769cfdbfed9bb4a03ca64a798672ab72ea5814cb2279e2d4e1.png",
        "remix_count": 31,
    },
    {
        "title": "Robo Teacher's Fun Academy",
        "story_text": "In a classroom of the future, a friendly robot named Professor Chip used holographic displays to bring lessons to life. Dinosaurs roamed across desks, planets orbited above heads, and the kids learned by exploring rather than just reading. Every day at Chip's Academy was an adventure.",
        "animation_style": "3d_pixar",
        "age_group": "kids_8_12",
        "thumbnail_url": "https://static.prod-images.emergentagent.com/jobs/d29dba27-ba90-4188-b2b5-0b75f69ea76d/images/fa218782cf315a943ff9cf4c9f7c58fb6754c256f84d7afcf468a6f2a6cd43d4.png",
        "remix_count": 25,
    },
    {
        "title": "Sir Squeaks the Mouse Knight",
        "story_text": "The bravest knight in the medieval village was only three inches tall. Sir Squeaks the mouse rode his loyal cat steed through cobblestone streets, protecting the market from wandering hawks and keeping peace among the animal townsfolk. His courage proved that heroes come in all sizes.",
        "animation_style": "cartoon_2d",
        "age_group": "kids_5_8",
        "thumbnail_url": "https://static.prod-images.emergentagent.com/jobs/d29dba27-ba90-4188-b2b5-0b75f69ea76d/images/506d6012a03a6a2ca6de28111b1e17c96ea07a23a0673aa0c7780ca80da217f0.png",
        "remix_count": 19,
    },
    {
        "title": "Dinosaur Birthday Party",
        "story_text": "The biggest birthday party the prehistoric jungle had ever seen was happening today. A T-Rex wearing a sparkly party hat tried to blow out candles on a massive cake while pterodactyls dropped confetti from above. Every dinosaur was invited, and they danced until the meteor shower lit up the sky.",
        "animation_style": "cartoon_2d",
        "age_group": "kids_3_5",
        "thumbnail_url": "https://static.prod-images.emergentagent.com/jobs/d29dba27-ba90-4188-b2b5-0b75f69ea76d/images/dcc66fbc8d1254c0e2688c23a2b6e885136c0608451742782c32f441d18c69ee.png",
        "remix_count": 14,
    },
]

async def seed():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]

    # Remove ALL old showcase items
    result = await db.pipeline_jobs.delete_many({"is_showcase": True})
    print(f"Removed {result.deleted_count} old showcase items")

    now = datetime.now(timezone.utc)
    docs = []
    for i, item in enumerate(SHOWCASE_ITEMS):
        job_id = str(uuid.uuid4())
        docs.append({
            "job_id": job_id,
            "user_id": "showcase",
            "title": item["title"],
            "story_text": item["story_text"],
            "animation_style": item["animation_style"],
            "age_group": item["age_group"],
            "voice_preset": "narrator_warm",
            "status": "COMPLETED",
            "progress": 100,
            "current_step": "Showcase item",
            "output_url": None,
            "thumbnail_url": item["thumbnail_url"],
            "remix_count": item["remix_count"],
            "completed_at": now - timedelta(hours=i * 2),
            "created_at": now - timedelta(hours=i * 2 + 1),
            "is_showcase": True,
            "timing": {"total_ms": 95000},
            "stages": {},
        })

    if docs:
        await db.pipeline_jobs.insert_many(docs)
        print(f"Seeded {len(docs)} showcase items")

    # Verify
    count = await db.pipeline_jobs.count_documents({"is_showcase": True, "status": "COMPLETED"})
    print(f"Total showcase items in DB: {count}")

    # Print titles for verification
    cursor = db.pipeline_jobs.find({"is_showcase": True}, {"title": 1, "animation_style": 1, "thumbnail_url": 1, "_id": 0})
    async for doc in cursor:
        has_thumb = "YES" if doc.get("thumbnail_url") else "NO"
        print(f"  [{has_thumb}] {doc['title'][:40]:40} | {doc['animation_style']}")

    client.close()

if __name__ == "__main__":
    asyncio.run(seed())
