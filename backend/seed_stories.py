"""
Script to seed pre-created story templates into MongoDB
Run once to populate the database with 300+ story templates
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import random
import uuid
from datetime import datetime, timezone

# Story templates organized by age group, genre, and theme
STORY_TEMPLATES = []

# Character name placeholders that will be replaced dynamically
PLACEHOLDER_NAMES = ["{{HERO_NAME}}", "{{FRIEND_NAME}}", "{{VILLAIN_NAME}}", "{{MENTOR_NAME}}"]

# Default character names by gender/type
DEFAULT_NAMES = {
    "hero_male": ["Max", "Leo", "Sam", "Jack", "Finn", "Oliver", "Noah", "Ethan", "Liam", "Ben"],
    "hero_female": ["Luna", "Maya", "Zoe", "Lily", "Emma", "Ava", "Mia", "Sophie", "Ella", "Ruby"],
    "friend": ["Pip", "Buddy", "Sparky", "Whiskers", "Fuzzy", "Patches", "Buttons", "Ziggy", "Coco", "Peanut"],
    "mentor": ["Grandma Rose", "Old Wizard", "Wise Owl", "Elder Tree", "Magic Fox", "Ancient Turtle"],
}

# Pre-defined story structures
STORY_STRUCTURES = [
    # Adventure stories
    {
        "genre": "Adventure",
        "themes": ["Courage", "Exploration", "Discovery"],
        "morals": ["Bravery conquers fear", "The journey matters more than the destination", "True courage is facing your fears"],
        "age_groups": ["4-6", "6-8", "8-10"],
        "templates": [
            {
                "title": "The Hidden Cave Mystery",
                "synopsis": "{{HERO_NAME}} discovers a mysterious cave and embarks on an exciting adventure to uncover its secrets.",
                "moral": "Curiosity leads to wonderful discoveries",
                "scenes": [
                    {"scene_number": 1, "title": "The Discovery", "setting": "A sunny meadow near the forest", "narration": "One bright morning, {{HERO_NAME}} was playing in the meadow when something sparkly caught their eye near the old oak tree.", "visual_description": "A cheerful child in a meadow, sunlight streaming through trees, something glittering near rocks", "dialogue": [{"speaker": "{{HERO_NAME}}", "line": "What's that shiny thing over there?"}], "image_prompt": "Colorful children's book illustration of a curious child in a sunny meadow discovering something sparkling near an old oak tree"},
                    {"scene_number": 2, "title": "The Entrance", "setting": "Hidden cave entrance covered in vines", "narration": "Behind the bushes, {{HERO_NAME}} found a hidden cave entrance covered in beautiful glowing crystals!", "visual_description": "A magical cave entrance with glowing crystals and friendly vines", "dialogue": [{"speaker": "{{HERO_NAME}}", "line": "Wow! A secret cave! I wonder what's inside!"}], "image_prompt": "Whimsical illustration of a child-friendly cave entrance with colorful glowing crystals and friendly-looking vines"},
                    {"scene_number": 3, "title": "Meeting a Friend", "setting": "Inside the crystal cave", "narration": "Inside the cave, {{HERO_NAME}} met {{FRIEND_NAME}}, a friendly little creature who lived among the crystals.", "visual_description": "A cute magical creature in a crystal cave greeting a child", "dialogue": [{"speaker": "{{FRIEND_NAME}}", "line": "Hello there! Welcome to my crystal home!"}, {"speaker": "{{HERO_NAME}}", "line": "Nice to meet you! This place is amazing!"}], "image_prompt": "Adorable children's book illustration of a friendly magical creature meeting a child inside a beautiful crystal cave"},
                    {"scene_number": 4, "title": "The Challenge", "setting": "A fork in the cave path", "narration": "{{FRIEND_NAME}} told {{HERO_NAME}} about a special treasure deep in the cave, but they would need to solve riddles to find it.", "visual_description": "Two paths in a cave with glowing symbols", "dialogue": [{"speaker": "{{FRIEND_NAME}}", "line": "The treasure is this way, but we need to be brave and smart!"}], "image_prompt": "Colorful illustration of a magical cave with two glowing paths and friendly symbols on the walls"},
                    {"scene_number": 5, "title": "Solving the Puzzle", "setting": "A chamber with glowing symbols", "narration": "Together, {{HERO_NAME}} and {{FRIEND_NAME}} worked as a team to solve the first puzzle - matching the glowing shapes!", "visual_description": "Child and creature working together on a glowing puzzle", "dialogue": [{"speaker": "{{HERO_NAME}}", "line": "I think the star goes with the moon!"}, {"speaker": "{{FRIEND_NAME}}", "line": "You're right! You're so clever!"}], "image_prompt": "Cheerful illustration of a child and cute creature solving a colorful glowing puzzle together"},
                    {"scene_number": 6, "title": "The Bridge", "setting": "A magical rainbow bridge", "narration": "The puzzle opened a door to a beautiful rainbow bridge that led across an underground lake.", "visual_description": "A magical rainbow bridge over a sparkling underground lake", "dialogue": [{"speaker": "{{HERO_NAME}}", "line": "It's so beautiful! Let's cross together!"}], "image_prompt": "Stunning children's book illustration of a magical rainbow bridge over a glittering underground lake"},
                    {"scene_number": 7, "title": "Finding the Treasure", "setting": "The treasure chamber", "narration": "At the end of the bridge, they found the treasure - a chest full of seeds that would grow into magical flowers!", "visual_description": "A treasure chest with glowing magical seeds", "dialogue": [{"speaker": "{{FRIEND_NAME}}", "line": "These seeds will make our world more beautiful!"}, {"speaker": "{{HERO_NAME}}", "line": "Let's plant them everywhere!"}], "image_prompt": "Joyful illustration of a child and creature opening a treasure chest filled with glowing magical seeds"},
                    {"scene_number": 8, "title": "Happy Ending", "setting": "The meadow, now full of magical flowers", "narration": "{{HERO_NAME}} and {{FRIEND_NAME}} planted the seeds, and soon the whole meadow was filled with the most beautiful magical flowers anyone had ever seen!", "visual_description": "A meadow transformed with colorful magical flowers, child and creature celebrating", "dialogue": [{"speaker": "{{HERO_NAME}}", "line": "This is the best adventure ever! And I made a new best friend!"}], "image_prompt": "Beautiful children's book illustration of a magical meadow full of colorful glowing flowers with a happy child and cute creature celebrating"}
                ],
                "characters": [
                    {"name": "{{HERO_NAME}}", "role": "protagonist", "description": "A curious and brave young adventurer"},
                    {"name": "{{FRIEND_NAME}}", "role": "supporting", "description": "A friendly magical creature who lives in the crystal cave"}
                ]
            },
            {
                "title": "The Rainbow Mountain Quest",
                "synopsis": "{{HERO_NAME}} climbs the magical Rainbow Mountain to help return colors to a faded village.",
                "moral": "Helping others brings joy to everyone",
                "scenes": [
                    {"scene_number": 1, "title": "The Faded Village", "setting": "A gray, colorless village", "narration": "{{HERO_NAME}} lived in a village where all the colors had mysteriously faded away. Everything was gray and sad.", "visual_description": "A village in shades of gray with sad-looking buildings", "dialogue": [{"speaker": "{{HERO_NAME}}", "line": "I wish our village had beautiful colors again!"}], "image_prompt": "Children's book illustration of a gray colorless village with a determined child looking hopeful"},
                    {"scene_number": 2, "title": "The Legend", "setting": "Village elder's cottage", "narration": "{{MENTOR_NAME}} told {{HERO_NAME}} about the Rainbow Mountain where colors were born.", "visual_description": "A wise elder telling a story to an eager child", "dialogue": [{"speaker": "{{MENTOR_NAME}}", "line": "Legend says the Rainbow Keeper at the mountain top can restore our colors!"}, {"speaker": "{{HERO_NAME}}", "line": "I'll go find them!"}], "image_prompt": "Warm illustration of a kind elderly mentor telling a story to an excited child by candlelight"},
                    {"scene_number": 3, "title": "Starting the Journey", "setting": "Path leading to Rainbow Mountain", "narration": "With a backpack full of snacks and courage in their heart, {{HERO_NAME}} began the climb up Rainbow Mountain.", "visual_description": "Child with backpack at the base of a colorful mountain", "dialogue": [{"speaker": "{{HERO_NAME}}", "line": "Here I go! I can do this!"}], "image_prompt": "Inspiring illustration of a brave child with a small backpack starting to climb a magical colorful mountain"},
                    {"scene_number": 4, "title": "The Red Zone", "setting": "Section of mountain glowing red", "narration": "First, {{HERO_NAME}} passed through the Red Zone, where everything glowed like rubies and the air was warm and cozy.", "visual_description": "A section of mountain bathed in beautiful red light", "dialogue": [{"speaker": "{{HERO_NAME}}", "line": "Red is so warm and happy! Like a big hug!"}], "image_prompt": "Beautiful children's illustration of a child walking through a magical red-glowing section of a mountain"},
                    {"scene_number": 5, "title": "The Blue Rapids", "setting": "Blue glowing waterfall", "narration": "Next came the Blue Rapids, where {{HERO_NAME}} had to carefully cross stepping stones over a sparkling blue waterfall.", "visual_description": "Child hopping across stones near a magical blue waterfall", "dialogue": [{"speaker": "{{HERO_NAME}}", "line": "One step at a time... I can do it!"}], "image_prompt": "Exciting illustration of a child carefully crossing stepping stones by a magical blue glowing waterfall"},
                    {"scene_number": 6, "title": "Meeting the Rainbow Keeper", "setting": "Mountain top with rainbow lights", "narration": "At the very top, {{HERO_NAME}} met the Rainbow Keeper, a kind spirit made entirely of swirling colors!", "visual_description": "A friendly colorful spirit greeting a child at mountain top", "dialogue": [{"speaker": "Rainbow Keeper", "line": "You climbed all this way to help your village? How wonderful!"}, {"speaker": "{{HERO_NAME}}", "line": "Please, can you bring back our colors?"}], "image_prompt": "Magical illustration of a friendly rainbow spirit made of swirling colors meeting a brave child at a mountain top"},
                    {"scene_number": 7, "title": "The Gift", "setting": "Mountain top glowing with all colors", "narration": "The Rainbow Keeper was so touched by {{HERO_NAME}}'s kindness that they created a special Rainbow Crystal.", "visual_description": "A glowing rainbow crystal being given to a child", "dialogue": [{"speaker": "Rainbow Keeper", "line": "Take this Rainbow Crystal. It will restore colors wherever you go!"}], "image_prompt": "Heartwarming illustration of a rainbow spirit giving a glowing crystal to a happy child"},
                    {"scene_number": 8, "title": "Colors Return", "setting": "The village now full of beautiful colors", "narration": "When {{HERO_NAME}} returned home, the Rainbow Crystal filled the village with the most beautiful colors. Everyone cheered!", "visual_description": "A now colorful village with celebrating people", "dialogue": [{"speaker": "Villagers", "line": "Thank you, {{HERO_NAME}}! You're our hero!"}, {"speaker": "{{HERO_NAME}}", "line": "I'm so happy I could help everyone!"}], "image_prompt": "Joyful children's book illustration of a colorful village with happy people celebrating around a proud child holding a rainbow crystal"}
                ],
                "characters": [
                    {"name": "{{HERO_NAME}}", "role": "protagonist", "description": "A kind and determined young hero"},
                    {"name": "{{MENTOR_NAME}}", "role": "supporting", "description": "A wise village elder who knows the old legends"}
                ]
            }
        ]
    },
    # Friendship stories
    {
        "genre": "Friendship",
        "themes": ["Making Friends", "Teamwork", "Kindness"],
        "morals": ["True friends help each other", "Kindness makes everyone happy", "Together we are stronger"],
        "age_groups": ["4-6", "6-8"],
        "templates": [
            {
                "title": "The Lonely Little Cloud",
                "synopsis": "{{HERO_NAME}} befriends a sad little cloud who has lost its way and helps it find its cloud family.",
                "moral": "A kind heart can make anyone's day brighter",
                "scenes": [
                    {"scene_number": 1, "title": "A Cloudy Day", "setting": "A hilltop on a windy day", "narration": "{{HERO_NAME}} loved to watch the clouds float by. One day, they noticed a tiny cloud sitting all alone, looking very sad.", "visual_description": "Child on a hilltop looking at a small sad cloud", "dialogue": [{"speaker": "{{HERO_NAME}}", "line": "Hello little cloud! Why do you look so sad?"}], "image_prompt": "Sweet children's illustration of a child on a grassy hilltop looking up at a small sad-looking cloud"},
                    {"scene_number": 2, "title": "The Cloud's Story", "setting": "Hilltop with the little cloud floating down", "narration": "The little cloud, named {{FRIEND_NAME}}, floated down and told {{HERO_NAME}} that the wind had blown it away from its family.", "visual_description": "A cute small cloud talking to a child", "dialogue": [{"speaker": "{{FRIEND_NAME}}", "line": "The big wind blew me so far away! I don't know where my family is!"}, {"speaker": "{{HERO_NAME}}", "line": "Don't worry! I'll help you find them!"}], "image_prompt": "Adorable illustration of a small fluffy cloud with a sad face talking to a kind child on a hilltop"},
                    {"scene_number": 3, "title": "Looking Up High", "setting": "Child climbing a tall tree", "narration": "{{HERO_NAME}} climbed the tallest tree to look for {{FRIEND_NAME}}'s cloud family in the sky.", "visual_description": "Child in a tree scanning the sky with a small cloud nearby", "dialogue": [{"speaker": "{{HERO_NAME}}", "line": "I can see so far from up here! Let me look for your family!"}], "image_prompt": "Adventurous illustration of a child climbing a tall friendly-looking tree with a small cloud floating nearby"},
                    {"scene_number": 4, "title": "Making Rain", "setting": "A sunny garden", "narration": "While searching, {{FRIEND_NAME}} felt so happy with their new friend that it accidentally made a tiny rainbow!", "visual_description": "A small cloud making a little rainbow while a child laughs", "dialogue": [{"speaker": "{{FRIEND_NAME}}", "line": "Oh! I made a rainbow! That happens when I'm really happy!"}, {"speaker": "{{HERO_NAME}}", "line": "It's beautiful! You're amazing!"}], "image_prompt": "Delightful illustration of a happy small cloud creating a tiny rainbow while a child claps with joy"},
                    {"scene_number": 5, "title": "The Signal", "setting": "Open field", "narration": "{{HERO_NAME}} had an idea! If {{FRIEND_NAME}} made more rainbows, maybe the cloud family would see them!", "visual_description": "Child and cloud making multiple small rainbows", "dialogue": [{"speaker": "{{HERO_NAME}}", "line": "Make more rainbows! Your family might see them!"}, {"speaker": "{{FRIEND_NAME}}", "line": "Great idea! Here I go!"}], "image_prompt": "Colorful illustration of a child encouraging a small cloud who is making multiple little rainbows in the sky"},
                    {"scene_number": 6, "title": "Family Found", "setting": "Sky full of clouds approaching", "narration": "It worked! A group of fluffy clouds came floating over, and they were {{FRIEND_NAME}}'s family!", "visual_description": "A family of clouds happily reuniting", "dialogue": [{"speaker": "Cloud Family", "line": "{{FRIEND_NAME}}! We found you! We were so worried!"}, {"speaker": "{{FRIEND_NAME}}", "line": "Mommy! Daddy! My new friend helped me!"}], "image_prompt": "Heartwarming illustration of a family of fluffy clouds reuniting with the small cloud while a happy child watches"},
                    {"scene_number": 7, "title": "Thank You Gift", "setting": "Beautiful sunset sky", "narration": "The cloud family was so grateful that they created the most beautiful sunset {{HERO_NAME}} had ever seen.", "visual_description": "A spectacular sunset with cloud shapes forming a thank you", "dialogue": [{"speaker": "Cloud Family", "line": "Thank you for helping our little one! This sunset is for you!"}], "image_prompt": "Stunning children's illustration of a magnificent sunset with clouds forming beautiful patterns as a thank you gift"},
                    {"scene_number": 8, "title": "Forever Friends", "setting": "Hilltop at evening", "narration": "From that day on, whenever {{HERO_NAME}} looked up at the sky, {{FRIEND_NAME}} would float by and wave with a little rainbow.", "visual_description": "Child waving at a small cloud with a rainbow trail", "dialogue": [{"speaker": "{{HERO_NAME}}", "line": "See you tomorrow, {{FRIEND_NAME}}!"}, {"speaker": "{{FRIEND_NAME}}", "line": "Best friends forever!"}], "image_prompt": "Beautiful children's book ending illustration of a child waving goodbye to a happy small cloud leaving a rainbow trail in the evening sky"}
                ],
                "characters": [
                    {"name": "{{HERO_NAME}}", "role": "protagonist", "description": "A kind child who loves watching clouds"},
                    {"name": "{{FRIEND_NAME}}", "role": "supporting", "description": "A small fluffy cloud who got lost from its family"}
                ]
            }
        ]
    },
    # Fantasy stories  
    {
        "genre": "Fantasy",
        "themes": ["Magic", "Imagination", "Wonder"],
        "morals": ["Believe in yourself", "Magic is everywhere if you look", "Dreams can come true"],
        "age_groups": ["4-6", "6-8", "8-10"],
        "templates": [
            {
                "title": "The Magical Garden",
                "synopsis": "{{HERO_NAME}} discovers a secret garden where flowers can talk and grant wishes to kind children.",
                "moral": "Kindness is the greatest magic of all",
                "scenes": [
                    {"scene_number": 1, "title": "The Secret Gate", "setting": "Behind an old stone wall", "narration": "While playing in the backyard, {{HERO_NAME}} discovered a tiny golden gate hidden behind the ivy on the old stone wall.", "visual_description": "A small golden gate covered in ivy and flowers", "dialogue": [{"speaker": "{{HERO_NAME}}", "line": "I've never noticed this little gate before! I wonder where it leads?"}], "image_prompt": "Enchanting children's illustration of a small magical golden gate hidden among ivy and colorful flowers"},
                    {"scene_number": 2, "title": "Entering the Garden", "setting": "A magical garden with glowing flowers", "narration": "Through the gate was the most amazing garden {{HERO_NAME}} had ever seen! Flowers glowed in every color of the rainbow!", "visual_description": "A magical garden with luminescent flowers of all colors", "dialogue": [{"speaker": "{{HERO_NAME}}", "line": "Wow! Everything is so sparkly and beautiful!"}], "image_prompt": "Breathtaking children's book illustration of a magical garden with glowing flowers in every color of the rainbow"},
                    {"scene_number": 3, "title": "Flowers That Talk", "setting": "Among the talking flowers", "narration": "Suddenly, a beautiful rose spoke! 'Welcome to the Wish Garden, dear child!'", "visual_description": "A friendly talking rose with a kind face", "dialogue": [{"speaker": "Rose", "line": "Welcome to the Wish Garden! I'm Rosa, and these are my friends!"}, {"speaker": "{{HERO_NAME}}", "line": "You can talk! This is amazing!"}], "image_prompt": "Whimsical illustration of a friendly talking rose flower with a sweet face greeting an amazed child"},
                    {"scene_number": 4, "title": "The Garden's Secret", "setting": "Center of the magical garden", "narration": "Rosa explained that the Wish Garden grants one wish to children who show true kindness.", "visual_description": "Flowers gathered around explaining their magic", "dialogue": [{"speaker": "Rosa", "line": "Show us your kind heart, and you may make one special wish!"}, {"speaker": "{{HERO_NAME}}", "line": "How can I show kindness here?"}], "image_prompt": "Charming illustration of various talking flowers gathered around a curious child in a magical garden"},
                    {"scene_number": 5, "title": "Helping the Wilting Flower", "setting": "Corner of the garden", "narration": "{{HERO_NAME}} noticed a small flower in the corner looking droopy and sad. Without thinking, they rushed to help.", "visual_description": "Child gently caring for a wilting small flower", "dialogue": [{"speaker": "{{HERO_NAME}}", "line": "Poor little flower! Let me get you some water and find you some sunshine!"}], "image_prompt": "Touching illustration of a caring child gently helping a wilting small flower with water"},
                    {"scene_number": 6, "title": "The Flower Blooms", "setting": "Same corner, now bright", "narration": "With {{HERO_NAME}}'s care, the little flower perked up and bloomed into the most beautiful golden flower!", "visual_description": "A small flower transforming into a beautiful golden bloom", "dialogue": [{"speaker": "Little Flower", "line": "Thank you! You saved me! I'm {{FRIEND_NAME}}!"}, {"speaker": "Rosa", "line": "You showed true kindness! Now you may make your wish!"}], "image_prompt": "Magical illustration of a small flower transforming into a beautiful glowing golden flower while a child watches in wonder"},
                    {"scene_number": 7, "title": "The Wish", "setting": "Center of garden with all flowers glowing", "narration": "{{HERO_NAME}} thought carefully. They could wish for anything! But they had an idea...", "visual_description": "Child thinking surrounded by glowing flowers", "dialogue": [{"speaker": "{{HERO_NAME}}", "line": "I wish... that I can visit this garden and my flower friends whenever I want!"}], "image_prompt": "Heartfelt illustration of a thoughtful child surrounded by glowing magical flowers making a wish"},
                    {"scene_number": 8, "title": "A Magical Friendship", "setting": "Garden with a rainbow overhead", "narration": "The flowers were so happy! They gave {{HERO_NAME}} a special seed that would let them return anytime. The garden now had a new friend!", "visual_description": "Happy child receiving a glowing seed from the flowers, rainbow overhead", "dialogue": [{"speaker": "All Flowers", "line": "You're always welcome here, dear friend!"}, {"speaker": "{{HERO_NAME}}", "line": "Thank you! I'll visit every day!"}], "image_prompt": "Joyful children's book ending with a happy child receiving a glowing magical seed from smiling flowers with a beautiful rainbow overhead"}
                ],
                "characters": [
                    {"name": "{{HERO_NAME}}", "role": "protagonist", "description": "A curious and kind-hearted child"},
                    {"name": "{{FRIEND_NAME}}", "role": "supporting", "description": "A magical golden flower who was saved by the hero's kindness"}
                ]
            }
        ]
    },
    # Animal stories
    {
        "genre": "Animal",
        "themes": ["Nature", "Animals", "Environment"],
        "morals": ["Respect all living things", "Everyone has special talents", "Take care of nature"],
        "age_groups": ["4-6", "6-8"],
        "templates": [
            {
                "title": "The Brave Little Squirrel",
                "synopsis": "{{HERO_NAME}} the squirrel overcomes their fear of heights to save their forest friends.",
                "moral": "Being brave doesn't mean not being scared - it means doing what's right even when you're afraid",
                "scenes": [
                    {"scene_number": 1, "title": "A Squirrel Who Couldn't Climb", "setting": "Base of a tall oak tree", "narration": "{{HERO_NAME}} was a little squirrel who was afraid of heights. While other squirrels played in the treetops, {{HERO_NAME}} stayed on the ground.", "visual_description": "A cute small squirrel looking up nervously at a tall tree", "dialogue": [{"speaker": "{{HERO_NAME}}", "line": "I wish I could climb like the others, but I'm too scared!"}], "image_prompt": "Adorable children's illustration of a small worried squirrel looking up at a very tall oak tree with other squirrels playing above"},
                    {"scene_number": 2, "title": "The Wise Old Owl", "setting": "Lower branch of the oak tree", "narration": "{{MENTOR_NAME}} the owl saw {{HERO_NAME}} looking sad and flew down to talk.", "visual_description": "A kind owl talking to a small squirrel", "dialogue": [{"speaker": "{{MENTOR_NAME}}", "line": "Why so glum, little one?"}, {"speaker": "{{HERO_NAME}}", "line": "I can't climb high like everyone else. I'm too scared of heights!"}], "image_prompt": "Warm illustration of a wise friendly owl talking kindly to a sad small squirrel on a low branch"},
                    {"scene_number": 3, "title": "Storm Warning", "setting": "Forest with darkening sky", "narration": "Suddenly, dark clouds rolled in! A big storm was coming, and the baby birds in the highest nest couldn't fly down!", "visual_description": "Dark storm clouds approaching with worried animals", "dialogue": [{"speaker": "Bird Mother", "line": "Help! My babies are stuck in the top nest! The storm will blow them away!"}], "image_prompt": "Dramatic children's illustration of storm clouds approaching a forest with worried bird mother and animals looking up at a high nest"},
                    {"scene_number": 4, "title": "A Difficult Choice", "setting": "Base of the tallest tree", "narration": "{{HERO_NAME}} looked up at the nest, way up high. It was the scariest thing imaginable. But the baby birds needed help!", "visual_description": "Squirrel looking up at an impossibly tall tree with a nest at top", "dialogue": [{"speaker": "{{HERO_NAME}}", "line": "I'm so scared... but those babies need help. I have to try!"}], "image_prompt": "Emotional illustration of a small determined squirrel looking up a very tall tree with a nest at the top as storm approaches"},
                    {"scene_number": 5, "title": "Climbing Higher", "setting": "Halfway up the tree", "narration": "One branch at a time, {{HERO_NAME}} climbed higher than ever before. 'Don't look down,' they whispered.", "visual_description": "Brave squirrel climbing with determination", "dialogue": [{"speaker": "{{HERO_NAME}}", "line": "One more branch... I can do this... one more branch..."}], "image_prompt": "Inspiring illustration of a brave little squirrel climbing up a tall tree with determined expression, halfway to the top"},
                    {"scene_number": 6, "title": "Reaching the Top", "setting": "At the very top nest", "narration": "{{HERO_NAME}} made it! The baby birds chirped happily as {{HERO_NAME}} helped them get ready to move.", "visual_description": "Squirrel at the top nest with happy baby birds", "dialogue": [{"speaker": "Baby Birds", "line": "You came to save us! Thank you, brave squirrel!"}, {"speaker": "{{HERO_NAME}}", "line": "Hold on tight to my tail! We're going down together!"}], "image_prompt": "Heartwarming illustration of a brave squirrel at the top of a tree with happy baby birds in a nest"},
                    {"scene_number": 7, "title": "Safe Descent", "setting": "Climbing down with baby birds", "narration": "Carefully, {{HERO_NAME}} helped each baby bird down to safety, just as the first raindrops fell.", "visual_description": "Squirrel helping baby birds climb down as rain starts", "dialogue": [{"speaker": "{{HERO_NAME}}", "line": "Almost there! Just a few more branches!"}], "image_prompt": "Exciting illustration of a squirrel helping baby birds carefully descend a tree as rain begins to fall"},
                    {"scene_number": 8, "title": "A True Hero", "setting": "Under shelter as storm rages, all animals safe", "narration": "Everyone cheered for {{HERO_NAME}}! The little squirrel who was afraid of heights had become the bravest hero in the forest!", "visual_description": "All forest animals celebrating the squirrel hero while safe from storm", "dialogue": [{"speaker": "All Animals", "line": "Hooray for {{HERO_NAME}}! The bravest squirrel ever!"}, {"speaker": "{{MENTOR_NAME}}", "line": "You see? Being brave isn't about not being scared. It's about doing what's right even when you ARE scared!"}], "image_prompt": "Joyful children's book ending with forest animals celebrating a happy squirrel hero under shelter while a storm rages safely outside"}
                ],
                "characters": [
                    {"name": "{{HERO_NAME}}", "role": "protagonist", "description": "A small squirrel who is afraid of heights but has a big heart"},
                    {"name": "{{MENTOR_NAME}}", "role": "supporting", "description": "A wise old owl who believes in the little squirrel"}
                ]
            }
        ]
    },
    # Educational/Learning stories
    {
        "genre": "Educational",
        "themes": ["Learning", "Curiosity", "Problem-Solving"],
        "morals": ["Learning is fun", "Mistakes help us grow", "Never stop asking questions"],
        "age_groups": ["4-6", "6-8", "8-10"],
        "templates": [
            {
                "title": "The Number Forest",
                "synopsis": "{{HERO_NAME}} enters a magical forest where learning numbers becomes an exciting adventure.",
                "moral": "Learning can be the greatest adventure of all",
                "scenes": [
                    {"scene_number": 1, "title": "A Strange Book", "setting": "Child's bedroom", "narration": "{{HERO_NAME}} found an old book with glowing numbers on the cover. When they opened it, something magical happened!", "visual_description": "A child opening a glowing book with numbers floating out", "dialogue": [{"speaker": "{{HERO_NAME}}", "line": "Whoa! The numbers are flying out of the book!"}], "image_prompt": "Magical children's illustration of a child opening an enchanted book with glowing numbers floating out"},
                    {"scene_number": 2, "title": "Into the Number Forest", "setting": "A forest made of numbers", "narration": "{{HERO_NAME}} was transported to the Number Forest, where trees were shaped like numbers and paths were made of equations!", "visual_description": "A whimsical forest with number-shaped trees", "dialogue": [{"speaker": "{{HERO_NAME}}", "line": "This is amazing! Everything is made of numbers!"}], "image_prompt": "Fantastical children's illustration of a magical forest with trees shaped like numbers and colorful equation paths"},
                    {"scene_number": 3, "title": "Meeting One", "setting": "Near a tree shaped like 1", "narration": "{{HERO_NAME}} met their first number friend - a tall, proud number One who introduced themselves.", "visual_description": "A friendly number 1 character greeting a child", "dialogue": [{"speaker": "One", "line": "Hello! I'm One - the very first number! Everything starts with me!"}, {"speaker": "{{HERO_NAME}}", "line": "Nice to meet you, One! Can you help me explore?"}], "image_prompt": "Friendly illustration of a personified number 1 character greeting a curious child in a number forest"},
                    {"scene_number": 4, "title": "The Adding Bridge", "setting": "A bridge over a number river", "narration": "To cross the river, {{HERO_NAME}} had to solve addition problems. 1 + 1 = ?", "visual_description": "A bridge made of plus signs over a flowing number river", "dialogue": [{"speaker": "{{HERO_NAME}}", "line": "One plus one equals... TWO!"}, {"speaker": "Bridge", "line": "Correct! You may cross!"}], "image_prompt": "Fun educational illustration of a child solving math on a magical bridge made of plus signs over a river of flowing numbers"},
                    {"scene_number": 5, "title": "The Number Party", "setting": "A clearing with numbers 0-9", "narration": "In a magical clearing, all the numbers from 0 to 9 were having a party and welcomed {{HERO_NAME}}!", "visual_description": "Personified numbers 0-9 having a colorful party", "dialogue": [{"speaker": "Numbers", "line": "Welcome to the Number Party! Come count with us!"}], "image_prompt": "Joyful illustration of personified numbers 0-9 having a colorful party welcoming a happy child"},
                    {"scene_number": 6, "title": "Counting Game", "setting": "Party area with number games", "narration": "{{HERO_NAME}} played counting games with the numbers. They counted stars, apples, and even dancing butterflies!", "visual_description": "Child counting various objects with number friends", "dialogue": [{"speaker": "{{HERO_NAME}}", "line": "One, two, three, four, five! I love counting!"}], "image_prompt": "Educational children's illustration of a child happily counting stars, apples, and butterflies with number characters cheering"},
                    {"scene_number": 7, "title": "The Secret of Zero", "setting": "Meeting the mysterious Zero", "narration": "Zero seemed sad because everyone thought they meant 'nothing.' But {{HERO_NAME}} learned Zero's special secret!", "visual_description": "Child comforting a sad zero who then becomes happy", "dialogue": [{"speaker": "{{HERO_NAME}}", "line": "Zero, you're not nothing! You make ten with one, hundred with other numbers - you're super important!"}, {"speaker": "Zero", "line": "You understand! I'm the placeholder that makes big numbers possible!"}], "image_prompt": "Touching illustration of a child encouraging a personified Zero character who transforms from sad to happy"},
                    {"scene_number": 8, "title": "Home with New Friends", "setting": "Back in bedroom with the book", "narration": "{{HERO_NAME}} returned home, but now numbers weren't scary anymore - they were friends! And the book glowed warmly on the shelf.", "visual_description": "Happy child in bed with the glowing book, number friends waving", "dialogue": [{"speaker": "{{HERO_NAME}}", "line": "I can't wait to learn more! Numbers are so much fun!"}, {"speaker": "Numbers", "line": "We'll always be here when you need us!"}], "image_prompt": "Heartwarming children's book ending with a happy child in bed, a glowing number book on the shelf, and small number characters waving goodbye"}
                ],
                "characters": [
                    {"name": "{{HERO_NAME}}", "role": "protagonist", "description": "A curious child who discovers the joy of learning"},
                    {"name": "{{FRIEND_NAME}}", "role": "supporting", "description": "The number characters who become friends"}
                ]
            }
        ]
    }
]

def generate_youtube_metadata(story):
    """Generate YouTube metadata for a story"""
    return {
        "title": f"{story['title']} | Kids Story | Animated Bedtime Story",
        "description": f"{story['synopsis']}\n\nMoral: {story['moral']}\n\nThis is a wonderful story for children about {story.get('genre', 'adventure').lower()}. Perfect for bedtime stories, learning, and family time!\n\n#KidsStory #BedtimeStory #ChildrensBook #AnimatedStory",
        "tags": ["kids story", "bedtime story", "children's book", "animated story", story.get('genre', 'Adventure').lower(), "moral story", "educational", "family friendly", "storytime"]
    }

def create_story_templates():
    """Create all story templates"""
    templates = []
    template_id = 1
    
    for structure in STORY_STRUCTURES:
        genre = structure["genre"]
        themes = structure["themes"]
        morals = structure["morals"]
        age_groups = structure["age_groups"]
        
        for story in structure["templates"]:
            for age_group in age_groups:
                for theme in themes:
                    template = {
                        "id": str(uuid.uuid4()),
                        "templateNumber": template_id,
                        "genre": genre,
                        "ageGroup": age_group,
                        "theme": theme,
                        "title": story["title"],
                        "synopsis": story["synopsis"],
                        "moral": story["moral"],
                        "scenes": story["scenes"],
                        "characters": story["characters"],
                        "youtubeMetadata": generate_youtube_metadata(story),
                        "createdAt": datetime.now(timezone.utc).isoformat(),
                        "usageCount": 0
                    }
                    templates.append(template)
                    template_id += 1
    
    return templates

async def seed_database():
    """Seed the database with story templates"""
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client["test_database"]
    
    # Clear existing templates
    await db.story_templates.delete_many({})
    
    # Generate templates
    templates = create_story_templates()
    
    # Insert templates
    if templates:
        await db.story_templates.insert_many(templates)
        print(f"Seeded {len(templates)} story templates!")
    
    # Create index for efficient querying
    await db.story_templates.create_index([("genre", 1), ("ageGroup", 1), ("theme", 1)])
    await db.story_templates.create_index([("ageGroup", 1)])
    
    client.close()
    return len(templates)

if __name__ == "__main__":
    count = asyncio.run(seed_database())
    print(f"Done! Created {count} story templates.")
