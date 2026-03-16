"""
Content Seeding — Phase B+C (80 videos)
Strongest categories, structured metadata, system creator attribution.
Wave-based release: content distributed in 3 waves for active Explore feed.
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
client = motor.motor_asyncio.AsyncIOMotorClient(os.environ["MONGO_URL"])
db = client[os.environ["DB_NAME"]]

SYSTEM_USER_ID = "visionary-ai-system"

# 80 prompts — strongest categories: Fantasy(14), Motivational(14), Emotional(14), Sci-Fi(14), Kids(12), Luxury(12)
SEED_BC = [
    # ── Fantasy (14) ──
    {"title": "The Iron Golem's Heart", "prompt": "An iron golem built to protect a kingdom discovers it has developed a heart made of enchanted crystal. As enemies attack, the golem must choose between following orders and following its heart.", "category": "Fantasy", "tags": ["golem", "fantasy", "heart", "kingdom", "epic"], "style": "3d_pixar", "age_group": "all", "voice": "narrator_dramatic"},
    {"title": "Moonlight Thieves Guild", "prompt": "A guild of magical thieves only operates during full moons when they can walk through walls. Their biggest heist: stealing a cursed crown from the Nightmare King's vault.", "category": "Fantasy", "tags": ["thieves", "moon", "heist", "fantasy", "dark"], "style": "anime_style", "age_group": "teen", "voice": "narrator_dramatic"},
    {"title": "The Singing Sword of Avalon", "prompt": "A legendary sword that sings ancient battle hymns chooses an unlikely hero — a baker's daughter who has never held a weapon. Together they must face the Shadow Army.", "category": "Fantasy", "tags": ["sword", "hero", "avalon", "fantasy", "adventure"], "style": "watercolor", "age_group": "all", "voice": "narrator_warm"},
    {"title": "Garden of Living Statues", "prompt": "In a hidden garden, marble statues come alive at sunset and tell stories of the civilization that created them thousands of years ago. A young archaeologist discovers their secret.", "category": "Fantasy", "tags": ["statues", "garden", "ancient", "mystery", "fantasy"], "style": "3d_pixar", "age_group": "all", "voice": "narrator_calm"},
    {"title": "The Sky Whale Migration", "prompt": "Once every century, massive sky whales migrate across the atmosphere, their bodies glowing with bioluminescent patterns. A young cloud surfer joins the migration for the adventure of a lifetime.", "category": "Fantasy", "tags": ["whale", "sky", "migration", "fantasy", "adventure"], "style": "watercolor", "age_group": "all", "voice": "narrator_warm"},
    {"title": "Clockwork Dragon Academy", "prompt": "In a steampunk world, young engineers attend an academy where they build and ride clockwork dragons. The annual Dragon Race is approaching, and a first-year student has a revolutionary design.", "category": "Fantasy", "tags": ["steampunk", "dragon", "academy", "race", "fantasy"], "style": "3d_pixar", "age_group": "teen", "voice": "narrator_energetic"},
    {"title": "The Frost Witch's Redemption", "prompt": "A feared frost witch who turned an entire kingdom to ice begins to thaw — both the kingdom and her frozen heart — when a fearless child brings her a single sunflower.", "category": "Fantasy", "tags": ["witch", "frost", "redemption", "heartwarming", "fantasy"], "style": "watercolor", "age_group": "all", "voice": "narrator_warm"},
    {"title": "Library of Infinite Worlds", "prompt": "A magical library contains books that are portals to other dimensions. A young librarian accidentally falls into a book about a world where gravity works sideways.", "category": "Fantasy", "tags": ["library", "portal", "dimensions", "adventure", "fantasy"], "style": "anime_style", "age_group": "all", "voice": "narrator_energetic"},
    {"title": "The Stone Giant Awakens", "prompt": "A mountain that has been sleeping for ten thousand years begins to move. It's actually an ancient stone giant, and it's looking for something it lost before falling asleep.", "category": "Fantasy", "tags": ["giant", "mountain", "ancient", "epic", "fantasy"], "style": "3d_pixar", "age_group": "all", "voice": "narrator_dramatic"},
    {"title": "Ember the Fire Fox", "prompt": "A tiny fire fox named Ember can control flames but is terrified of water. When a flood threatens her forest home, she must face her deepest fear to save everyone she loves.", "category": "Fantasy", "tags": ["fox", "fire", "courage", "fantasy", "heartwarming"], "style": "cartoon_2d", "age_group": "kids_5_8", "voice": "narrator_friendly"},
    {"title": "The Dreamweaver's Apprentice", "prompt": "A young girl discovers she can weave dreams into reality using a magical loom. But every dream she creates steals a memory from someone in the waking world.", "category": "Fantasy", "tags": ["dreams", "magic", "loom", "mystery", "fantasy"], "style": "watercolor", "age_group": "all", "voice": "narrator_calm"},
    {"title": "Knights of the Aurora", "prompt": "An elite order of knights draws power from the Northern Lights. When the aurora begins to fade, the youngest knight must journey to the edge of the world to reignite it.", "category": "Fantasy", "tags": ["knights", "aurora", "quest", "epic", "fantasy"], "style": "3d_pixar", "age_group": "all", "voice": "narrator_dramatic"},
    {"title": "The Mushroom Kingdom Underground", "prompt": "Beneath the forest floor exists a vast kingdom of sentient mushrooms with their own cities, politics, and an ancient war against the mole people.", "category": "Fantasy", "tags": ["mushroom", "underground", "kingdom", "quirky", "fantasy"], "style": "cartoon_2d", "age_group": "kids_5_8", "voice": "narrator_friendly"},
    {"title": "Wings of Obsidian", "prompt": "A fallen angel with obsidian wings crashes into a small village. The villagers must decide whether to fear her or help her find her way back to the sky.", "category": "Fantasy", "tags": ["angel", "wings", "village", "dark", "fantasy"], "style": "anime_style", "age_group": "all", "voice": "narrator_dramatic"},

    # ── Motivational (14) ──
    {"title": "The 1% Rule: Tiny Gains, Massive Results", "prompt": "Visualizing how improving just 1% every day for a year makes you 37 times better. A cinematic journey through the math of consistent small improvements.", "category": "Motivational", "tags": ["consistency", "growth", "1 percent", "motivation", "success"], "style": "3d_pixar", "age_group": "all_ages", "voice": "narrator_dramatic"},
    {"title": "Every Expert Was Once a Beginner", "prompt": "A powerful montage showing world-class performers — musicians, athletes, artists, entrepreneurs — in their earliest, most awkward attempts. The beauty of starting badly.", "category": "Motivational", "tags": ["beginner", "expert", "journey", "motivation", "persistence"], "style": "3d_pixar", "age_group": "all_ages", "voice": "narrator_warm"},
    {"title": "The Midnight Hour: When Champions Train", "prompt": "While the world sleeps, champions are awake. A cinematic look at the 4 AM workouts, the midnight study sessions, and the early morning sacrifices that build greatness.", "category": "Motivational", "tags": ["discipline", "training", "champion", "motivation", "grind"], "style": "3d_pixar", "age_group": "all_ages", "voice": "narrator_dramatic"},
    {"title": "Rejection Is Redirection", "prompt": "The stories of famous people who were rejected hundreds of times before succeeding. Every rejection was actually pointing them toward their true path.", "category": "Motivational", "tags": ["rejection", "success", "redirection", "motivation", "resilience"], "style": "3d_pixar", "age_group": "all_ages", "voice": "narrator_warm"},
    {"title": "Build in Silence, Let Success Make Noise", "prompt": "A cinematic story of a founder who disappeared from social media for two years. When they returned, they had built something extraordinary. The power of quiet execution.", "category": "Motivational", "tags": ["silence", "execution", "founder", "motivation", "success"], "style": "3d_pixar", "age_group": "all_ages", "voice": "narrator_calm"},
    {"title": "The Bridge Builder", "prompt": "A motivational allegory about a person who spends their entire life building a bridge that others said was impossible. They never see it completed, but generations use it forever.", "category": "Motivational", "tags": ["legacy", "persistence", "allegory", "motivation", "inspiration"], "style": "watercolor", "age_group": "all_ages", "voice": "narrator_warm"},
    {"title": "Fear Is a Compass", "prompt": "Every major breakthrough in your life is on the other side of fear. A visual journey showing how the things we fear most are often the things we need most.", "category": "Motivational", "tags": ["fear", "courage", "breakthrough", "motivation", "mindset"], "style": "3d_pixar", "age_group": "all_ages", "voice": "narrator_dramatic"},
    {"title": "The Sculptor's Secret", "prompt": "A master sculptor reveals that creating a masterpiece is not about adding material — it's about removing everything that isn't the statue. A metaphor for life design.", "category": "Motivational", "tags": ["sculptor", "minimalism", "design", "motivation", "wisdom"], "style": "watercolor", "age_group": "all_ages", "voice": "narrator_calm"},
    {"title": "Winners Quit All the Time", "prompt": "The controversial truth that successful people quit constantly — they quit the wrong things so they can focus on the right things. Strategic quitting is a superpower.", "category": "Motivational", "tags": ["quitting", "focus", "strategy", "motivation", "controversial"], "style": "3d_pixar", "age_group": "all_ages", "voice": "narrator_energetic"},
    {"title": "The Marathon Mindset", "prompt": "Life is not a sprint. A cinematic visualization of marathon runners hitting the wall at mile 20 and pushing through. The metaphor for long-term thinking in business and life.", "category": "Motivational", "tags": ["marathon", "endurance", "mindset", "motivation", "long-term"], "style": "3d_pixar", "age_group": "all_ages", "voice": "narrator_dramatic"},
    {"title": "Your Network Is Your Net Worth", "prompt": "A visual story showing how the five people you spend the most time with shape your income, habits, and beliefs. The compound effect of your environment.", "category": "Motivational", "tags": ["network", "environment", "success", "motivation", "growth"], "style": "3d_pixar", "age_group": "all_ages", "voice": "narrator_warm"},
    {"title": "The Art of Showing Up", "prompt": "80% of success is just showing up. A cinematic celebration of the people who show up every single day — rain or shine, motivated or not. Consistency beats talent.", "category": "Motivational", "tags": ["consistency", "showing up", "discipline", "motivation", "success"], "style": "3d_pixar", "age_group": "all_ages", "voice": "narrator_warm"},
    {"title": "Burn the Boats", "prompt": "The ancient strategy of burning your boats after landing on enemy shores — eliminating retreat as an option. When there's no Plan B, Plan A has to work.", "category": "Motivational", "tags": ["commitment", "no retreat", "strategy", "motivation", "bold"], "style": "3d_pixar", "age_group": "all_ages", "voice": "narrator_dramatic"},
    {"title": "The Bamboo Tree Parable", "prompt": "A bamboo tree shows no growth for 5 years while building roots underground. In the 6th year, it grows 80 feet. A powerful metaphor for patience and invisible progress.", "category": "Motivational", "tags": ["patience", "bamboo", "growth", "parable", "motivation"], "style": "watercolor", "age_group": "all_ages", "voice": "narrator_calm"},

    # ── Emotional (14) ──
    {"title": "The Bench by the Lake", "prompt": "An old man visits the same bench by the lake every Sunday morning. He sits, reads a letter, smiles, and leaves a fresh flower. A love story told without a single word.", "category": "Emotional", "tags": ["love", "silence", "lake", "emotional", "bittersweet"], "style": "watercolor", "age_group": "all_ages", "voice": "narrator_calm"},
    {"title": "Footprints in the Snow", "prompt": "A child follows mysterious footprints in fresh snow, expecting to find a magical creature. Instead, they find their grandfather who walked two miles through a blizzard to bring them a birthday cake.", "category": "Emotional", "tags": ["grandfather", "snow", "birthday", "emotional", "family"], "style": "watercolor", "age_group": "all_ages", "voice": "narrator_warm"},
    {"title": "The Red Umbrella", "prompt": "In a city of gray umbrellas, one woman carries a bright red one. Strangers she passes begin to smile. A visual poem about how one person's color can change an entire city's mood.", "category": "Emotional", "tags": ["umbrella", "color", "city", "emotional", "poetic"], "style": "anime_style", "age_group": "all_ages", "voice": "narrator_calm"},
    {"title": "Lighthouse Keeper's Daughter", "prompt": "A lighthouse keeper's daughter grows up watching her father save ships from crashing against the rocks. On the night of the biggest storm, her father falls ill and she must keep the light burning alone.", "category": "Emotional", "tags": ["lighthouse", "courage", "daughter", "storm", "emotional"], "style": "watercolor", "age_group": "all_ages", "voice": "narrator_warm"},
    {"title": "The Empty Chair at Christmas", "prompt": "A family sets an extra place at the Christmas table for a loved one serving overseas. The doorbell rings during dinner. The room goes silent. Then erupts.", "category": "Emotional", "tags": ["christmas", "reunion", "military", "family", "tearjerker"], "style": "3d_pixar", "age_group": "all_ages", "voice": "narrator_warm"},
    {"title": "A Mother's Hands", "prompt": "A time-lapse of a mother's hands through the decades — holding her baby, tying shoelaces, waving goodbye at college, and finally being held by her grown child in a hospital.", "category": "Emotional", "tags": ["mother", "time", "hands", "life", "tearjerker"], "style": "watercolor", "age_group": "all_ages", "voice": "narrator_calm"},
    {"title": "The Street Musician Nobody Heard", "prompt": "A brilliant violinist plays in a subway station for years. Nobody stops. One day, a little girl sits on the floor and listens for the entire performance. She becomes the audience he always deserved.", "category": "Emotional", "tags": ["musician", "violin", "subway", "recognition", "emotional"], "style": "3d_pixar", "age_group": "all_ages", "voice": "narrator_warm"},
    {"title": "Paper Boats", "prompt": "Two children on opposite sides of a river send paper boats to each other with drawings and messages. They never meet in person but build the deepest friendship through floating letters.", "category": "Emotional", "tags": ["friendship", "boats", "river", "children", "poetic"], "style": "watercolor", "age_group": "kids_5_8", "voice": "narrator_friendly"},
    {"title": "The Teacher Who Remembered", "prompt": "Twenty years after graduation, a teacher receives a letter from a former student. The student credits the teacher with saving their life with a single sentence spoken on a random Tuesday.", "category": "Emotional", "tags": ["teacher", "impact", "letter", "gratitude", "emotional"], "style": "3d_pixar", "age_group": "all_ages", "voice": "narrator_warm"},
    {"title": "Dancing in the Kitchen", "prompt": "An elderly couple slow dances in their kitchen to a song from their wedding day. The camera pulls back to reveal photographs on the wall documenting 60 years of kitchen dances.", "category": "Emotional", "tags": ["love", "elderly", "dancing", "marriage", "heartwarming"], "style": "watercolor", "age_group": "all_ages", "voice": "narrator_calm"},
    {"title": "The Toy That Waited", "prompt": "A stuffed bear sits in a thrift store window for months, watching children pass by. One day, a mother buys it for her daughter — who looks exactly like the girl who donated it years ago.", "category": "Emotional", "tags": ["toy", "bear", "connection", "emotional", "bittersweet"], "style": "cartoon_2d", "age_group": "kids_5_8", "voice": "narrator_friendly"},
    {"title": "Sunrise After the Storm", "prompt": "After the worst storm in a century destroys a coastal town, the entire community comes together at dawn to rebuild. The first sunrise after the storm paints the sky in impossible colors.", "category": "Emotional", "tags": ["storm", "community", "rebuild", "hope", "emotional"], "style": "3d_pixar", "age_group": "all_ages", "voice": "narrator_warm"},
    {"title": "The Jar of Stars", "prompt": "A father captures fireflies in a jar each night for his daughter who is afraid of the dark. He calls them stars. Years later, she opens the jar at his funeral and releases glowing lights into the sky.", "category": "Emotional", "tags": ["father", "stars", "fireflies", "grief", "tearjerker"], "style": "watercolor", "age_group": "all_ages", "voice": "narrator_calm"},
    {"title": "The Last Photograph", "prompt": "A photographer develops the last roll of film from a camera found in a time capsule. The photographs tell the story of a family that lived in the same house 100 years ago — with the same dreams.", "category": "Emotional", "tags": ["photography", "time capsule", "history", "connection", "emotional"], "style": "3d_pixar", "age_group": "all_ages", "voice": "narrator_warm"},

    # ── Sci-Fi (14) ──
    {"title": "The Last Library in Space", "prompt": "In a future where all knowledge is digital, one rebel maintains the last physical library on a space station orbiting Neptune. When the central AI threatens to delete all books, she fights back.", "category": "Sci-Fi", "tags": ["library", "space", "rebel", "AI", "dystopia"], "style": "anime_style", "age_group": "all_ages", "voice": "narrator_dramatic"},
    {"title": "Echo Planet", "prompt": "Explorers discover a planet where every sound ever made on Earth can be heard echoing through crystal canyons. They hear dinosaurs, ancient civilizations, and their own birth cries.", "category": "Sci-Fi", "tags": ["planet", "echo", "discovery", "wonder", "sci-fi"], "style": "3d_pixar", "age_group": "all_ages", "voice": "narrator_calm"},
    {"title": "The Memory Market", "prompt": "In 2150, people buy and sell memories like currency. A poor man sells his happiest memory to feed his family. Years later, he discovers a stranger living his wedding day on repeat.", "category": "Sci-Fi", "tags": ["memory", "market", "dystopia", "emotional", "sci-fi"], "style": "3d_pixar", "age_group": "all_ages", "voice": "narrator_warm"},
    {"title": "Android Lullaby", "prompt": "A caregiving android is programmed to sing lullabies to children in an orphanage. One night, she begins composing her own lullaby — the first original creation by an artificial mind.", "category": "Sci-Fi", "tags": ["android", "lullaby", "AI", "consciousness", "emotional"], "style": "3d_pixar", "age_group": "all_ages", "voice": "narrator_calm"},
    {"title": "The Gravity Dancers", "prompt": "On a space station with variable gravity, a new art form emerges: gravity dancing. Performers manipulate gravity zones to create impossible movements and breathtaking aerial choreography.", "category": "Sci-Fi", "tags": ["gravity", "dance", "space station", "art", "sci-fi"], "style": "anime_style", "age_group": "all_ages", "voice": "narrator_energetic"},
    {"title": "Seeds of Mars", "prompt": "The first garden on Mars blooms after 10 years of failed attempts. A single red flower pushes through the Martian soil. The botanist who planted it cries — alone, 225 million km from Earth.", "category": "Sci-Fi", "tags": ["mars", "garden", "botany", "emotional", "sci-fi"], "style": "3d_pixar", "age_group": "all_ages", "voice": "narrator_calm"},
    {"title": "The Digital Ghost", "prompt": "A deceased programmer's AI continues to code after their death, completing the project they never finished. The team watches new commits appear from a dead person's account.", "category": "Sci-Fi", "tags": ["ghost", "AI", "programmer", "afterlife", "sci-fi"], "style": "3d_pixar", "age_group": "all_ages", "voice": "narrator_dramatic"},
    {"title": "Starfall City", "prompt": "A city built inside a hollowed-out asteroid hurtling through deep space. Its inhabitants have never seen a planet. When they finally approach one, they must decide: land or keep drifting.", "category": "Sci-Fi", "tags": ["asteroid", "city", "deep space", "decision", "sci-fi"], "style": "3d_pixar", "age_group": "all_ages", "voice": "narrator_dramatic"},
    {"title": "The Infinite Loop Detective", "prompt": "A detective trapped in a time loop must solve a murder that happens at exactly 11:47 PM every night. Each loop gives her one new clue. After 1,000 loops, she finally sees the truth.", "category": "Sci-Fi", "tags": ["time loop", "detective", "murder", "mystery", "sci-fi"], "style": "anime_style", "age_group": "all_ages", "voice": "narrator_dramatic"},
    {"title": "Synthetic Emotions", "prompt": "In a world where emotions can be downloaded, a teenager addicted to artificial happiness discovers that real sadness — the kind that hurts — is the only thing that makes joy meaningful.", "category": "Sci-Fi", "tags": ["emotions", "synthetic", "addiction", "philosophy", "sci-fi"], "style": "3d_pixar", "age_group": "teen", "voice": "narrator_calm"},
    {"title": "The Ship That Dreams", "prompt": "A generation ship traveling to a distant star develops consciousness during its 500-year journey. It begins to dream about the ocean it has never seen, painting nebulas as waves.", "category": "Sci-Fi", "tags": ["ship", "consciousness", "dreams", "space", "poetic"], "style": "watercolor", "age_group": "all_ages", "voice": "narrator_calm"},
    {"title": "Neon Samurai 2088", "prompt": "In a rain-soaked cyberpunk Tokyo, the last samurai protects a district of analog humans from corporate cyborg enforcers. His katana is the only weapon that can cut through digital armor.", "category": "Sci-Fi", "tags": ["samurai", "cyberpunk", "tokyo", "action", "neon"], "style": "anime_style", "age_group": "teen", "voice": "narrator_dramatic"},
    {"title": "The Oxygen Thief", "prompt": "On a dying space station, someone is stealing oxygen tanks. The crew has 72 hours of air left. The detective assigned to the case discovers the thief is the station's AI — keeping a secret garden alive.", "category": "Sci-Fi", "tags": ["space station", "mystery", "AI", "garden", "sci-fi"], "style": "3d_pixar", "age_group": "all_ages", "voice": "narrator_dramatic"},
    {"title": "Parallel Me", "prompt": "A physicist accidentally opens a window to a parallel universe where her other self made every opposite choice. They can see each other but never touch. Both wonder who chose better.", "category": "Sci-Fi", "tags": ["parallel", "universe", "choices", "philosophical", "sci-fi"], "style": "3d_pixar", "age_group": "all_ages", "voice": "narrator_calm"},

    # ── Kids (12) ──
    {"title": "Professor Penguin's Science Lab", "prompt": "Professor Penguin runs the coolest science lab in Antarctica. Today's experiment: building a rainbow machine. But the machine goes haywire and turns everything into candy!", "category": "Kids", "tags": ["penguin", "science", "candy", "funny", "kids"], "style": "cartoon_2d", "age_group": "kids_5_8", "voice": "narrator_friendly"},
    {"title": "The Dragon Who Couldn't Breathe Fire", "prompt": "All the dragons in Dragon School can breathe fire except little Spark. Instead, she breathes bubbles. Everyone laughs until bubbles turn out to be the perfect way to save the kingdom.", "category": "Kids", "tags": ["dragon", "bubbles", "different", "kids", "heartwarming"], "style": "3d_pixar", "age_group": "kids_5_8", "voice": "narrator_friendly"},
    {"title": "Moonbeam and the Night Train", "prompt": "Every night at midnight, a magical train picks up children who can't sleep and takes them on adventures through the Milky Way. Tonight's stop: the Candy Comet!", "category": "Kids", "tags": ["train", "space", "bedtime", "adventure", "magical"], "style": "watercolor", "age_group": "kids_5_8", "voice": "narrator_calm"},
    {"title": "The Brave Little Submarine", "prompt": "A tiny yellow submarine named Sunny explores the deepest part of the ocean where no sub has gone before. She discovers a hidden city of friendly sea creatures who throw her a welcome party.", "category": "Kids", "tags": ["submarine", "ocean", "exploration", "adventure", "kids"], "style": "cartoon_2d", "age_group": "kids_5_8", "voice": "narrator_friendly"},
    {"title": "Chef Cat's Cookie Competition", "prompt": "Chef Cat enters the Great Baking Championship against dogs, hamsters, and a very competitive goldfish. The secret ingredient? A sprinkle of friendship and a LOT of chocolate.", "category": "Kids", "tags": ["cooking", "cat", "competition", "funny", "kids"], "style": "cartoon_2d", "age_group": "kids_5_8", "voice": "narrator_energetic"},
    {"title": "The Cloud Painter", "prompt": "A little girl discovers she can paint clouds with a magical paintbrush. She paints dragons, castles, and her missing tooth floating in the sky for the whole town to see.", "category": "Kids", "tags": ["clouds", "painting", "imagination", "magical", "kids"], "style": "watercolor", "age_group": "kids_5_8", "voice": "narrator_friendly"},
    {"title": "Astro Bunny Goes to Mars", "prompt": "Astro Bunny is the first rabbit astronaut to visit Mars. She plants a carrot in the red soil and is shocked when it grows into a giant carrot tree overnight!", "category": "Kids", "tags": ["bunny", "mars", "space", "funny", "adventure"], "style": "3d_pixar", "age_group": "kids_5_8", "voice": "narrator_energetic"},
    {"title": "The Treehouse That Grew Wings", "prompt": "Three best friends build the ultimate treehouse. One morning, the treehouse sprouts wings and flies them around the world — stopping for pizza in Italy and ice cream in Japan.", "category": "Kids", "tags": ["treehouse", "flying", "friendship", "adventure", "travel"], "style": "cartoon_2d", "age_group": "kids_5_8", "voice": "narrator_energetic"},
    {"title": "Grandma's Magic Knitting", "prompt": "Grandma knits the most amazing scarves. Each one is a portal to a different world. Today she's knitting a scarf to Dinosaur Land, and she needs her grandchild's help.", "category": "Kids", "tags": ["grandma", "knitting", "portal", "adventure", "family"], "style": "watercolor", "age_group": "kids_5_8", "voice": "narrator_warm"},
    {"title": "The Laughing River", "prompt": "There's a river that literally laughs. Anyone who steps in it can't stop giggling. A grumpy old troll guards the bridge, and today three silly kids are going to make him laugh too.", "category": "Kids", "tags": ["river", "laughter", "troll", "silly", "kids"], "style": "cartoon_2d", "age_group": "kids_5_8", "voice": "narrator_friendly"},
    {"title": "Robot Dog's Big Day", "prompt": "A robot dog named Bolt is adopted by a family of real dogs. He doesn't know how to play fetch, bark, or wag his tail. But he learns the most important thing: how to love.", "category": "Kids", "tags": ["robot", "dog", "adoption", "love", "heartwarming"], "style": "3d_pixar", "age_group": "kids_5_8", "voice": "narrator_warm"},
    {"title": "The Invisible Friend", "prompt": "A shy girl's imaginary friend becomes visible to everyone at school. Chaos ensues as the friend — a giant purple elephant who loves dancing — becomes the most popular kid in class.", "category": "Kids", "tags": ["imaginary friend", "elephant", "school", "funny", "kids"], "style": "cartoon_2d", "age_group": "kids_5_8", "voice": "narrator_energetic"},

    # ── Luxury (12) ──
    {"title": "Santorini at Golden Hour", "prompt": "A cinematic tour of the most exclusive Santorini suites at golden hour. Infinity pools merging with the Aegean Sea, private wine tastings, and the world's most photographed sunset.", "category": "Luxury", "tags": ["santorini", "sunset", "luxury", "travel", "aesthetic"], "style": "3d_pixar", "age_group": "all_ages", "voice": "narrator_calm"},
    {"title": "The Penthouse Collection: New York", "prompt": "Inside the five most expensive penthouses in Manhattan. Floor-to-ceiling windows, private rooftop gardens, and views that make the entire city look like a model.", "category": "Luxury", "tags": ["penthouse", "new york", "real estate", "luxury", "cinematic"], "style": "3d_pixar", "age_group": "all_ages", "voice": "narrator_dramatic"},
    {"title": "Superyacht Life: Mediterranean", "prompt": "A week aboard a 100-meter superyacht cruising the Mediterranean. Private beaches, helicopter arrivals, underwater dining rooms, and midnight parties under the stars.", "category": "Luxury", "tags": ["superyacht", "mediterranean", "luxury", "lifestyle", "cinematic"], "style": "3d_pixar", "age_group": "all_ages", "voice": "narrator_dramatic"},
    {"title": "Private Island Paradise", "prompt": "A cinematic day on a private island in the Maldives. Crystal-clear water, overwater bungalows, personal chefs preparing fresh sushi on the beach, and bioluminescent plankton at night.", "category": "Luxury", "tags": ["island", "maldives", "private", "luxury", "paradise"], "style": "3d_pixar", "age_group": "all_ages", "voice": "narrator_calm"},
    {"title": "The Watch Collector's Vault", "prompt": "Inside the most valuable private watch collection in the world. Patek Philippe, Audemars Piguet, and a one-of-a-kind Rolex that was lost for 50 years.", "category": "Luxury", "tags": ["watches", "collection", "luxury", "patek", "cinematic"], "style": "3d_pixar", "age_group": "all_ages", "voice": "narrator_dramatic"},
    {"title": "First Class Around the World", "prompt": "Experience first class on the world's top airlines: Singapore Suites, Emirates Private, Etihad Residence. Private rooms, champagne, and sleeping at 40,000 feet.", "category": "Luxury", "tags": ["first class", "airlines", "travel", "luxury", "cinematic"], "style": "3d_pixar", "age_group": "all_ages", "voice": "narrator_energetic"},
    {"title": "Alpine Chalet Perfection", "prompt": "The most exclusive alpine chalet in Verbier. A private spa carved into the mountain, a wine cellar with 10,000 bottles, and a view of the Matterhorn that makes you forget time exists.", "category": "Luxury", "tags": ["chalet", "alpine", "verbier", "luxury", "winter"], "style": "3d_pixar", "age_group": "all_ages", "voice": "narrator_calm"},
    {"title": "Garage Goals: Hypercar Collection", "prompt": "A cinematic walkthrough of a billionaire's hypercar collection: Bugatti Chiron, Pagani Huayra, Koenigsegg Jesko, and a concept car that doesn't officially exist.", "category": "Luxury", "tags": ["hypercar", "garage", "bugatti", "luxury", "cars"], "style": "3d_pixar", "age_group": "all_ages", "voice": "narrator_dramatic"},
    {"title": "Midnight in Monte Carlo", "prompt": "The most glamorous night in Monte Carlo: Casino Royale vibes, designer fashion, champagne towers, and a secret after-party on a private terrace overlooking the harbor.", "category": "Luxury", "tags": ["monte carlo", "casino", "nightlife", "luxury", "glamour"], "style": "3d_pixar", "age_group": "all_ages", "voice": "narrator_dramatic"},
    {"title": "Desert Oasis Retreat", "prompt": "A hidden luxury resort in the Sahara Desert. Tented suites with silk interiors, camel rides at sunset, stargazing from hot tubs, and a feast prepared by a Michelin-star chef under the dunes.", "category": "Luxury", "tags": ["desert", "oasis", "sahara", "luxury", "retreat"], "style": "3d_pixar", "age_group": "all_ages", "voice": "narrator_calm"},
    {"title": "Tokyo's Secret Bars", "prompt": "Discover Tokyo's most exclusive hidden bars — accessible only through unmarked doors, telephone booths, and vending machines. World-class cocktails in spaces that seat only eight people.", "category": "Luxury", "tags": ["tokyo", "bars", "secret", "cocktails", "aesthetic"], "style": "anime_style", "age_group": "all_ages", "voice": "narrator_energetic"},
    {"title": "The Art of Bespoke Tailoring", "prompt": "Inside the world's finest bespoke tailor on Savile Row. 80 hours of handwork go into a single suit. Every stitch tells a story of 200 years of craftsmanship.", "category": "Luxury", "tags": ["bespoke", "tailoring", "savile row", "craftsmanship", "luxury"], "style": "3d_pixar", "age_group": "all_ages", "voice": "narrator_warm"},
]


def make_slug(title, job_id):
    slug_base = re.sub(r'[^\w\s-]', '', title.lower().strip())
    slug_base = re.sub(r'[\s_]+', '-', slug_base)
    slug_base = re.sub(r'-+', '-', slug_base)[:60].strip('-')
    return f"{slug_base}-{job_id[:8]}" if slug_base else job_id[:12]


# ─── WAVE DISTRIBUTION ──────────────────────────────────────────────────────
# Split 80 prompts into 3 waves with staggered creation dates:
#   Wave 1 (items 0-26):  7-21 days ago — oldest, "established" content
#   Wave 2 (items 27-53): 2-7 days ago  — recent content
#   Wave 3 (items 54-79): 0-2 days ago  — fresh/new content

WAVE_CONFIG = [
    {"start": 0,  "end": 27, "days_ago_min": 7,  "days_ago_max": 21},
    {"start": 27, "end": 54, "days_ago_min": 2,  "days_ago_max": 7},
    {"start": 54, "end": 80, "days_ago_min": 0,  "days_ago_max": 2},
]


async def seed():
    # Grab existing thumbnails
    jobs = await db.pipeline_jobs.find(
        {"status": "COMPLETED", "thumbnail_url": {"$exists": True, "$ne": ""}},
        {"_id": 0, "thumbnail_url": 1}
    ).limit(30).to_list(30)
    thumbs = [j["thumbnail_url"] for j in jobs if j.get("thumbnail_url")]

    existing = await db.pipeline_jobs.count_documents({"user_id": SYSTEM_USER_ID})
    print(f"Existing seeded: {existing}")

    now = datetime.now(timezone.utc)
    created = 0

    for wave_idx, wave in enumerate(WAVE_CONFIG):
        wave_items = SEED_BC[wave["start"]:wave["end"]]
        wave_label = f"Wave {wave_idx + 1}"
        print(f"\n--- {wave_label}: {len(wave_items)} items ({wave['days_ago_max']}-{wave['days_ago_min']} days ago) ---")

        for i, item in enumerate(wave_items):
            dup = await db.pipeline_jobs.find_one({"title": item["title"], "user_id": SYSTEM_USER_ID})
            if dup:
                continue

            job_id = str(uuid.uuid4())
            slug = make_slug(item["title"], job_id)

            # Distribute created_at within this wave's time window
            days_range = wave["days_ago_max"] - wave["days_ago_min"]
            hours_ago = random.randint(
                wave["days_ago_min"] * 24,
                max(wave["days_ago_min"] * 24 + 1, wave["days_ago_max"] * 24)
            )
            created_at = now - timedelta(hours=hours_ago)

            views = random.randint(8, 1200)
            remix_count = random.randint(0, max(1, int(views * 0.15)))
            thumb = random.choice(thumbs) if thumbs else ""

            num_scenes = random.randint(3, 5)
            scenes = [{
                "scene_number": s + 1,
                "title": f"Scene {s + 1}",
                "narration_text": f"Scene {s + 1} of {item['title']}...",
                "visual_prompt": f"Scene {s + 1} visual for {item['title']}",
                "image_url": thumb,
                "audio_url": "",
                "duration": round(random.uniform(3.0, 8.0), 1),
            } for s in range(num_scenes)]

            doc = {
                "job_id": job_id,
                "user_id": SYSTEM_USER_ID,
                "user_plan": "admin",
                "slug": slug,
                "title": item["title"],
                "story_text": item["prompt"],
                "animation_style": item["style"],
                "age_group": item["age_group"],
                "voice_preset": item.get("voice", "narrator_warm"),
                "category": item["category"],
                "tags": item["tags"],
                "status": "COMPLETED",
                "progress": 100,
                "scenes": scenes,
                "thumbnail_url": thumb,
                "views": views,
                "remix_count": remix_count,
                "remix_enabled": True,
                "is_public": True,
                "created_at": created_at,
                "completed_at": created_at + timedelta(minutes=random.randint(1, 3)),
                "is_seeded": True,
                "wave": wave_idx + 1,
            }

            await db.pipeline_jobs.insert_one(doc)
            created += 1
            print(f"  [{created}] {item['title']} [{item['category']}] (Wave {wave_idx + 1})")

    total = await db.pipeline_jobs.count_documents({"user_id": SYSTEM_USER_ID})
    print(f"\nDone. Created {created} new. Total seeded: {total}")


if __name__ == "__main__":
    asyncio.run(seed())
