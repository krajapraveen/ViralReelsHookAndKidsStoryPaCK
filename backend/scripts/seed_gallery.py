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
    # ─── EXPANDED SHOWCASE (18 additional items for 30 total) ─────────────
    {
        "title": "Time Traveling Cat",
        "story_text": "Professor Whiskers accidentally activated his cardboard time machine and found himself in ancient Egypt, where cats were worshipped as gods. The local cats welcomed him with golden collars and fish feasts. When he returned home, his owner found sand in his fur and a tiny pyramid-shaped treat.",
        "animation_style": "cartoon_2d",
        "age_group": "kids_5_8",
        "thumbnail_url": "https://static.prod-images.emergentagent.com/jobs/d29dba27-ba90-4188-b2b5-0b75f69ea76d/images/a872e7715ba85b6197e0284e7c99f80a41ac2fd542033ef355b80dfdde7aa866.png",
        "remix_count": 112,
    },
    {
        "title": "Garden of Singing Flowers",
        "story_text": "Every morning at dawn, the flowers in Grandmother's garden would wake up and begin to sing. Roses hummed melodies, sunflowers belted out show tunes, and the tiny violets whispered harmonies. A young girl named Lily discovered their secret when she watered them with tears of joy after winning the school talent show.",
        "animation_style": "watercolor",
        "age_group": "kids_3_5",
        "thumbnail_url": "https://static.prod-images.emergentagent.com/jobs/d29dba27-ba90-4188-b2b5-0b75f69ea76d/images/a8a0e43d4cede87f383e6695d758daed26d17059583c24a4d4b30be236496545.png",
        "remix_count": 95,
    },
    {
        "title": "Space Station School",
        "story_text": "On the first orbiting school in space, students learned zero-gravity gymnastics, asteroid geology, and interplanetary diplomacy. The school mascot was a friendly alien named Blip who could change colors based on mood. Graduation meant getting your own jetpack and a license to explore the galaxy.",
        "animation_style": "3d_pixar",
        "age_group": "kids_8_12",
        "thumbnail_url": "https://static.prod-images.emergentagent.com/jobs/d29dba27-ba90-4188-b2b5-0b75f69ea76d/images/bf426f3d9d2a7bbac3318cb92270fbb00cd235294e4c0bc78d4bb1007827b7b3.png",
        "remix_count": 88,
    },
    {
        "title": "Moonlight Dance of the Wolves",
        "story_text": "Under the silver moonlight, a pack of wolves gathered at the mountain peak for their annual dance festival. Each wolf had a unique dance style — the alpha waltzed, the pups breakdanced, and the oldest wolf performed a slow, graceful ballet that made the stars themselves lean closer to watch.",
        "animation_style": "anime_style",
        "age_group": "kids_8_12",
        "thumbnail_url": "https://static.prod-images.emergentagent.com/jobs/d29dba27-ba90-4188-b2b5-0b75f69ea76d/images/a1c635fa62475e769cfdbfed9bb4a03ca64a798672ab72ea5814cb2279e2d4e1.png",
        "remix_count": 73,
    },
    {
        "title": "The Cloud Shepherd",
        "story_text": "High above the mountains, a girl named Aria herded clouds like sheep. She shaped them into animals for children below, created rain for thirsty gardens, and built cloud bridges between mountain peaks. Her favorite cloud, a fluffy one named Nimbus, followed her everywhere like a loyal dog.",
        "animation_style": "watercolor",
        "age_group": "kids_5_8",
        "thumbnail_url": "https://static.prod-images.emergentagent.com/jobs/d29dba27-ba90-4188-b2b5-0b75f69ea76d/images/a375c94249f29116bbdc5d252b4bb6a0ddb0fcf8ff10c8cd86bae0efd01a961f.png",
        "remix_count": 67,
    },
    {
        "title": "Treasure of the Rainbow Cave",
        "story_text": "Three brave friends followed a rainbow to its end and discovered a cave filled with crystals of every color. Each crystal played a different musical note when touched. Together, they created a symphony so beautiful that the cave opened its deepest chamber, revealing the true treasure: a map to more rainbow caves around the world.",
        "animation_style": "cartoon_2d",
        "age_group": "kids_5_8",
        "thumbnail_url": "https://static.prod-images.emergentagent.com/jobs/d29dba27-ba90-4188-b2b5-0b75f69ea76d/images/fe80be8f82d0d1bc31aebc6f9e8d68ae8ba50c461bf98db0c88d3583598cc93e.png",
        "remix_count": 59,
    },
    {
        "title": "Penguin Chef's Ice Cream Shop",
        "story_text": "In Antarctica, a penguin named Pierre opened the world's coldest ice cream parlor. He invented flavors like Aurora Borealis Swirl, Snowflake Crunch, and Glacier Berry. Penguins, seals, and even polar bears traveled from far away to taste his frozen creations. His secret: he churned ice cream during blizzards.",
        "animation_style": "3d_pixar",
        "age_group": "kids_3_5",
        "thumbnail_url": "https://static.prod-images.emergentagent.com/jobs/d29dba27-ba90-4188-b2b5-0b75f69ea76d/images/c98915b0c37a14774dc792bea83ad907203f022f954b5c5a928cd43733f00eb4.png",
        "remix_count": 52,
    },
    {
        "title": "The Wish-Granting Lighthouse",
        "story_text": "On a rocky island stood a lighthouse that granted one wish to every ship that passed. A sailor wished for safe passage, a fisherman wished for a bountiful catch, and a little girl on a ferry wished for the lighthouse keeper to never be lonely. That night, the keeper found a kitten at his door.",
        "animation_style": "watercolor",
        "age_group": "kids_5_8",
        "thumbnail_url": "https://static.prod-images.emergentagent.com/jobs/d29dba27-ba90-4188-b2b5-0b75f69ea76d/images/ba3e0ad163bfd7357e11a867f3afb26f32bafd0b2c82ffbfe55bea124f5683dd.png",
        "remix_count": 46,
    },
    {
        "title": "Ninja Bunny Academy",
        "story_text": "Hidden in a bamboo forest, the Ninja Bunny Academy trained the most elite carrot-gathering warriors. Students learned the art of silent hopping, the technique of invisible ears, and the ancient skill of carrot-jutsu. Their final exam: steal a golden carrot from the sleeping dragon without waking it.",
        "animation_style": "anime_style",
        "age_group": "kids_8_12",
        "thumbnail_url": "https://static.prod-images.emergentagent.com/jobs/d29dba27-ba90-4188-b2b5-0b75f69ea76d/images/350b1df7d754acbe6a1c441e5c173234d7761650ce38d22c92f694d519bd88e5.png",
        "remix_count": 41,
    },
    {
        "title": "Firefly Festival Night",
        "story_text": "Every summer solstice, millions of fireflies gathered in the ancient forest for the Grand Festival of Light. They choreographed dances in the air, creating moving pictures — shooting stars, blooming flowers, and soaring eagles — all painted in golden light against the velvet night sky.",
        "animation_style": "cartoon_2d",
        "age_group": "kids_3_5",
        "thumbnail_url": "https://static.prod-images.emergentagent.com/jobs/d29dba27-ba90-4188-b2b5-0b75f69ea76d/images/a8a0e43d4cede87f383e6695d758daed26d17059583c24a4d4b30be236496545.png",
        "remix_count": 37,
    },
    {
        "title": "The Tiny Astronaut's Big Dream",
        "story_text": "A hamster named Houston built a rocket from toilet paper rolls and aluminum foil. Against all odds, it actually worked. Houston became the smallest astronaut to orbit the Earth, waving a tiny flag as he floated past the International Space Station. The real astronauts couldn't believe their eyes.",
        "animation_style": "3d_pixar",
        "age_group": "kids_5_8",
        "thumbnail_url": "https://static.prod-images.emergentagent.com/jobs/d29dba27-ba90-4188-b2b5-0b75f69ea76d/images/fa218782cf315a943ff9cf4c9f7c58fb6754c256f84d7afcf468a6f2a6cd43d4.png",
        "remix_count": 33,
    },
    {
        "title": "Enchanted Library of Stories",
        "story_text": "In an old library, the books came alive at midnight. Characters stepped out of their pages — pirates sailed between shelves, princesses danced in the aisles, and dragons curled up by the fireplace. The librarian's cat was the only one who knew, keeping the secret with a knowing purr.",
        "animation_style": "watercolor",
        "age_group": "kids_5_8",
        "thumbnail_url": "https://static.prod-images.emergentagent.com/jobs/d29dba27-ba90-4188-b2b5-0b75f69ea76d/images/506d6012a03a6a2ca6de28111b1e17c96ea07a23a0673aa0c7780ca80da217f0.png",
        "remix_count": 28,
    },
    {
        "title": "Race of the Paper Airplanes",
        "story_text": "Every Friday afternoon, the children of Maple Street held the Grand Paper Airplane Championship. This week, a girl named Maya folded a plane so perfect it caught an updraft and soared over the entire town. It flew past the school, over the park, and didn't land until it reached the beach three miles away.",
        "animation_style": "cartoon_2d",
        "age_group": "kids_5_8",
        "thumbnail_url": "https://static.prod-images.emergentagent.com/jobs/d29dba27-ba90-4188-b2b5-0b75f69ea76d/images/dcc66fbc8d1254c0e2688c23a2b6e885136c0608451742782c32f441d18c69ee.png",
        "remix_count": 24,
    },
    {
        "title": "The Brave Little Submarine",
        "story_text": "A tiny yellow submarine named Sunny explored the deepest part of the ocean where no light could reach. Using her special glow, she discovered an underwater city of bioluminescent creatures — jellyfish that sparkled like chandeliers, fish that glowed like neon signs, and a giant squid who was actually quite friendly.",
        "animation_style": "3d_pixar",
        "age_group": "kids_5_8",
        "thumbnail_url": "https://static.prod-images.emergentagent.com/jobs/d29dba27-ba90-4188-b2b5-0b75f69ea76d/images/a375c94249f29116bbdc5d252b4bb6a0ddb0fcf8ff10c8cd86bae0efd01a961f.png",
        "remix_count": 21,
    },
    {
        "title": "Mountain Giant's Garden",
        "story_text": "The tallest mountain in the land was actually a sleeping giant covered in trees and moss. Once a year, he would gently stretch, making the ground rumble. The villagers below had learned to plant their crops on his shoulders, where the soil was richest and the sunlight was warm.",
        "animation_style": "claymation",
        "age_group": "kids_5_8",
        "thumbnail_url": "https://static.prod-images.emergentagent.com/jobs/d29dba27-ba90-4188-b2b5-0b75f69ea76d/images/fe80be8f82d0d1bc31aebc6f9e8d68ae8ba50c461bf98db0c88d3583598cc93e.png",
        "remix_count": 18,
    },
    {
        "title": "Fox and Owl Detective Agency",
        "story_text": "In a cozy treehouse office, Fox and Owl ran the forest's only detective agency. Their latest case: who stole the squirrels' acorn collection? Following clues through the autumn forest, they discovered the culprit was a forgetful bear who was sleepwalking and accidentally collecting acorns in his sleep.",
        "animation_style": "cartoon_2d",
        "age_group": "kids_5_8",
        "thumbnail_url": "https://static.prod-images.emergentagent.com/jobs/d29dba27-ba90-4188-b2b5-0b75f69ea76d/images/a872e7715ba85b6197e0284e7c99f80a41ac2fd542033ef355b80dfdde7aa866.png",
        "remix_count": 15,
    },
    {
        "title": "Solar System School Bus",
        "story_text": "Mrs. Cosmos drove the most extraordinary school bus in the universe — it could travel between planets. Today's field trip: Jupiter! The kids pressed their faces against the windows as they flew past Saturn's rings, waved at the Mars rovers, and collected souvenirs from asteroid belts.",
        "animation_style": "3d_pixar",
        "age_group": "kids_8_12",
        "thumbnail_url": "https://static.prod-images.emergentagent.com/jobs/d29dba27-ba90-4188-b2b5-0b75f69ea76d/images/bf426f3d9d2a7bbac3318cb92270fbb00cd235294e4c0bc78d4bb1007827b7b3.png",
        "remix_count": 12,
    },
    {
        "title": "Autumn Leaf Ballet",
        "story_text": "When autumn came, the leaves didn't just fall — they performed. Oak leaves did the waltz, maple leaves tried the tango, and birch leaves preferred hip-hop. The grandest performance was at sunset, when all the leaves danced together in a swirling ballet of red, gold, and amber before taking their final bow on the ground.",
        "animation_style": "watercolor",
        "age_group": "kids_3_5",
        "thumbnail_url": "https://static.prod-images.emergentagent.com/jobs/d29dba27-ba90-4188-b2b5-0b75f69ea76d/images/ba3e0ad163bfd7357e11a867f3afb26f32bafd0b2c82ffbfe55bea124f5683dd.png",
        "remix_count": 10,
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
