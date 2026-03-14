"""Seed the gallery with professional AI-generated showcase items."""
import asyncio
import uuid
from datetime import datetime, timezone, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
import os

MONGO_URL = os.environ.get("MONGO_URL")
DB_NAME = os.environ.get("DB_NAME", "creatorstudio_production").strip('"')

SHOWCASE_ITEMS = [
    {
        "title": "Luna and the Cloud Dragon",
        "story_text": "A brave young girl named Luna befriended a baby dragon made of clouds. Together they soared through magical sunsets, discovering hidden kingdoms above the sky. Their friendship proved that courage and kindness can unlock the most extraordinary adventures.",
        "animation_style": "cartoon_2d",
        "age_group": "kids_5_8",
        "thumbnail_url": "https://static.prod-images.emergentagent.com/jobs/d29dba27-ba90-4188-b2b5-0b75f69ea76d/images/81e8023a07a846e50a5a29af4506739392b87307dca3ece86f168ded85a2fb97.png",
        "remix_count": 47,
        "voice_preset": "narrator_warm",
    },
    {
        "title": "The Underwater Crystal Kingdom",
        "story_text": "Deep beneath the ocean waves, a glowing coral castle held secrets of an ancient underwater kingdom. Friendly fish and sea creatures welcomed curious visitors to their magical realm of light and wonder.",
        "animation_style": "cartoon_2d",
        "age_group": "kids_5_8",
        "thumbnail_url": "https://static.prod-images.emergentagent.com/jobs/d29dba27-ba90-4188-b2b5-0b75f69ea76d/images/9767ca5ec978bf4b91d67b24d17f267c28109cc21f9450a7737f122b0ce2b61f.png",
        "remix_count": 31,
        "voice_preset": "narrator_warm",
    },
    {
        "title": "Captain Whiskers in Space",
        "story_text": "An astronaut cat named Captain Whiskers blasted off to explore the colorful galaxy. Floating past ringed planets and sparkling nebulas, the brave feline discovered that the universe is full of friendly neighbors waiting to say hello.",
        "animation_style": "3d_cartoon",
        "age_group": "kids_5_8",
        "thumbnail_url": "https://static.prod-images.emergentagent.com/jobs/d29dba27-ba90-4188-b2b5-0b75f69ea76d/images/4e397a85980ce79c7eccaea4380ce879a3927ff7e53a32dc3c7ffe24ff8c6183.png",
        "remix_count": 28,
        "voice_preset": "narrator_warm",
    },
    {
        "title": "The Enchanted Treehouse Party",
        "story_text": "Hidden deep in an enchanted forest, a magical treehouse hosted the most wonderful tea parties. Squirrels, rabbits, and owls gathered under twinkling lanterns to share stories and laughter as golden light filtered through the ancient trees.",
        "animation_style": "watercolor",
        "age_group": "kids_3_5",
        "thumbnail_url": "https://static.prod-images.emergentagent.com/jobs/d29dba27-ba90-4188-b2b5-0b75f69ea76d/images/fede8e7aea1097f77278458543b556ce91bd9e14f124e8f2dbd3e66de55fd021.png",
        "remix_count": 22,
        "voice_preset": "narrator_warm",
    },
    {
        "title": "Sky Pirates of Cloud Harbor",
        "story_text": "A colorful pirate ship sailed through cotton candy clouds with a crew of adorable animal pirates. Captain Fox and First Mate Parrot discovered floating islands of treasure while the golden sunset painted the sky in brilliant colors.",
        "animation_style": "comic_strip",
        "age_group": "kids_8_12",
        "thumbnail_url": "https://static.prod-images.emergentagent.com/jobs/d29dba27-ba90-4188-b2b5-0b75f69ea76d/images/136d1ea5250582a5ff542adb4412235a8799e7f89463a2028b10349cc46c7853.png",
        "remix_count": 19,
        "voice_preset": "narrator_warm",
    },
    {
        "title": "The Midnight Fairy Garden",
        "story_text": "When night falls, a magical garden comes alive with glowing flowers and dancing fairies. Tiny wings shimmer in pink and purple light as the fairies tend to their enchanted blooms under the gentle moonlight.",
        "animation_style": "watercolor",
        "age_group": "kids_3_5",
        "thumbnail_url": "https://static.prod-images.emergentagent.com/jobs/d29dba27-ba90-4188-b2b5-0b75f69ea76d/images/a23659b0577941f830f1e7942e9f68c9aa78ac4256bc485e02b114a3fedf5165.png",
        "remix_count": 15,
        "voice_preset": "narrator_warm",
    },
    {
        "title": "Aurora and the Brave Little Fox",
        "story_text": "A small fox named Aurora climbed to the highest peak to watch the northern lights dance across the sky. The shimmering green and purple waves told stories of ancient legends while the stars twinkled in approval of her courage.",
        "animation_style": "anime",
        "age_group": "kids_8_12",
        "thumbnail_url": "https://static.prod-images.emergentagent.com/jobs/d29dba27-ba90-4188-b2b5-0b75f69ea76d/images/b20e870026536257af402b64c2eb5aadbfee003405d7956e1a7cedcfff2c0bcf.png",
        "remix_count": 12,
        "voice_preset": "narrator_warm",
    },
    {
        "title": "Robo Teacher's Fun Academy",
        "story_text": "In a futuristic classroom that sparkles with holographic displays, a friendly robot named Professor Chip teaches kids about the wonders of science. Together they build amazing inventions and explore the mysteries of the universe.",
        "animation_style": "3d_cartoon",
        "age_group": "kids_5_8",
        "thumbnail_url": "https://static.prod-images.emergentagent.com/jobs/d29dba27-ba90-4188-b2b5-0b75f69ea76d/images/3565d1a93a96933f99a3a54cffdd96dbb5ffb43cad86f9a447c441c069f0a604.png",
        "remix_count": 9,
        "voice_preset": "narrator_warm",
    },
    {
        "title": "Ella the Rainbow Painter",
        "story_text": "A baby elephant named Ella discovered she could paint rainbows with her trunk. On the warm African savanna, she sprayed colors across the sky, bringing joy to all the animals who gathered to watch her magical artwork light up the golden plains.",
        "animation_style": "cartoon_2d",
        "age_group": "kids_3_5",
        "thumbnail_url": "https://static.prod-images.emergentagent.com/jobs/d29dba27-ba90-4188-b2b5-0b75f69ea76d/images/a7160123f9fc76dbacee28e0b5e961e7bef0efb293697df6325361fcfb1291a1.png",
        "remix_count": 7,
        "voice_preset": "narrator_warm",
    },
    {
        "title": "Princess Frost and the Ice Kingdom",
        "story_text": "Atop a frozen mountain stood a magnificent castle of pure crystal ice. Princess Frost and her loyal polar bear companion guarded the ancient magic that kept winter beautiful and balanced across the enchanted northern lands.",
        "animation_style": "anime",
        "age_group": "kids_5_8",
        "thumbnail_url": "https://static.prod-images.emergentagent.com/jobs/d29dba27-ba90-4188-b2b5-0b75f69ea76d/images/793618143f5b260cd5bf9a4a26ee85258c4acf270a51b2e732d449157f732bbd.png",
        "remix_count": 5,
        "voice_preset": "narrator_warm",
    },
    {
        "title": "The Junior Justice League",
        "story_text": "Five extraordinary kids discovered they had amazing superpowers. Flying high over the colorful city skyline at dawn, they vowed to protect their neighborhood from trouble and always help those in need with bravery and teamwork.",
        "animation_style": "comic_strip",
        "age_group": "kids_8_12",
        "thumbnail_url": "https://static.prod-images.emergentagent.com/jobs/d29dba27-ba90-4188-b2b5-0b75f69ea76d/images/877098fdc64ed85c4f119440005b3a3f032178630452545dfc88d585ecd243e3.png",
        "remix_count": 3,
        "voice_preset": "narrator_warm",
    },
    {
        "title": "The Tiny Baker Mice",
        "story_text": "In a cozy bakery hidden behind the walls, a family of mice crafted the most delicious tiny cakes and pastries. Using miniature ovens and flour sacks, they baked with love and sprinkled magic into every treat they made.",
        "animation_style": "watercolor",
        "age_group": "kids_3_5",
        "thumbnail_url": "https://static.prod-images.emergentagent.com/jobs/d29dba27-ba90-4188-b2b5-0b75f69ea76d/images/a848820fbb698d2db5d95cccb2044f3f8a394ef9dd83436a352025bcbe296703.png",
        "remix_count": 2,
        "voice_preset": "narrator_warm",
    },
]

async def seed():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]

    # Remove old showcase items
    await db.pipeline_jobs.delete_many({"is_showcase": True})

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
            "voice_preset": item["voice_preset"],
            "status": "COMPLETED",
            "progress": 100,
            "current_step": "Showcase item",
            "output_url": None,
            "thumbnail_url": item["thumbnail_url"],
            "remix_count": item["remix_count"],
            "completed_at": now - timedelta(hours=i * 3),
            "created_at": now - timedelta(hours=i * 3 + 1),
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

    client.close()

if __name__ == "__main__":
    asyncio.run(seed())
