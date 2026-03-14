"""Generate 5 comic storybooks and 5 coloring books."""
import asyncio, aiohttp, json, sys
API_URL = sys.argv[1]

COMICS = [
    {"title": "The Dragon Who Learned to Dance", "story": "A clumsy baby dragon named Flame wants to learn to dance for the Dragon Festival. He trips and falls, scorches the dance floor, and knocks over the music stand. But with help from a patient flamingo teacher, Flame learns that dancing is about having fun, not being perfect. At the festival, Flame's unique fire-dance becomes the most popular performance, and everyone joins in.", "style": "manga", "pages": 10},
    {"title": "Starlight and the Moon Garden", "story": "A little girl named Starlight discovers that her grandmother's garden comes alive at night. Flowers sing lullabies, mushrooms glow like lanterns, and tiny fairies tend the moonlit blooms. When a dark cloud threatens to block the moonlight forever, Starlight and the fairies work together to create a giant mirror from dewdrops that reflects starlight onto the garden. The garden is saved, and Starlight becomes its nighttime guardian.", "style": "storybook", "pages": 10},
    {"title": "Professor Penguin's Ice Lab", "story": "Professor Penguin runs a secret science laboratory inside an iceberg. She invents amazing gadgets: ice cream that never melts, snow boots that help penguins fly, and a telescope that can see underwater. When a walrus accidentally drinks the flying potion and floats away, Professor Penguin must build a rescue balloon from frozen bubbles to save him before he floats to the sun.", "style": "cartoon", "pages": 10},
    {"title": "The Treasure Map of Friendship Island", "story": "Three animal friends, a fox, a rabbit, and a turtle, find a treasure map on the beach. Each friend has a unique skill: Fox can read maps, Rabbit can dig fast, and Turtle knows the tides. They follow the map through jungle puzzles, across rope bridges, and through crystal caves. The treasure they find is not gold but a magical friendship stone that glows whenever true friends are near.", "style": "superhero", "pages": 10},
    {"title": "Robo-Chef and the Golden Cupcake", "story": "In a futuristic bakery, a robot named Chef-3000 dreams of baking the legendary Golden Cupcake. Every great chef has tried and failed because the recipe requires a secret ingredient: a genuine smile. Chef-3000 learns that robots cannot smile until a little girl teaches it that smiling comes from making others happy. Chef-3000 bakes cupcakes for the whole neighborhood, and finally creates the Golden Cupcake with the biggest smile ever computed.", "style": "cartoon", "pages": 10},
]

COLORING_THEMES = [
    {"theme": "Enchanted Forest Animals", "style": "fantasy"},
    {"theme": "Space Adventure Rockets", "style": "cartoon"},
    {"theme": "Underwater Ocean Friends", "style": "whimsical"},
    {"theme": "Dinosaur Discovery World", "style": "realistic"},
    {"theme": "Magical Fairy Garden", "style": "fantasy"},
]

async def main():
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=300)) as s:
        # Login
        token_resp = await (await s.post(f"{API_URL}/api/auth/login", json={"email":"test@visionary-suite.com","password":"Test@2026#"})).json()
        token = token_resp.get("token")
        h = {"Authorization": f"Bearer {token}"}

        # Generate 5 comic storybooks
        print("=== COMIC STORYBOOKS ===")
        for i, comic in enumerate(COMICS):
            try:
                form = aiohttp.FormData()
                form.add_field("story_text", comic["story"])
                form.add_field("style", comic["style"])
                form.add_field("page_count", str(comic["pages"]))
                form.add_field("title", comic["title"])
                form.add_field("author", "Visionary Suite AI")
                resp = await s.post(f"{API_URL}/api/comic-storybook/generate", headers=h, data=form)
                d = await resp.json()
                print(f"Comic {i+1}: success={d.get('success')} title={comic['title']}")
            except Exception as e:
                print(f"Comic {i+1}: ERROR {e}")

        # Generate 5 coloring books
        print("\n=== COLORING BOOKS ===")
        for i, cb in enumerate(COLORING_THEMES):
            try:
                resp = await s.post(f"{API_URL}/api/coloring-book-v2/generate/preview",
                    headers={**h, "Content-Type": "application/json"},
                    json={"theme": cb["theme"], "style": cb["style"], "complexity": "medium", "pages": 5})
                d = await resp.json()
                print(f"Coloring {i+1}: success={d.get('success', d.get('detail',''))} theme={cb['theme']}")
            except Exception as e:
                print(f"Coloring {i+1}: ERROR {e}")

asyncio.run(main())
