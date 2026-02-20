"""
Script to add teen story templates (10-17 years) to the database
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import uuid
from datetime import datetime, timezone
import os
from dotenv import load_dotenv

load_dotenv()

TEEN_STORIES = [
    # 10-13 years (Pre-Teen) - Adventure and Mystery themes
    {
        "ageGroup": "10-13",
        "genre": "Adventure",
        "theme": "Courage",
        "title": "The Lost City Expedition",
        "synopsis": "{{HERO_NAME}} joins an archaeological expedition and discovers they have a special gift for decoding ancient symbols.",
        "moral": "Trust your instincts and believe in your unique abilities",
        "characters": [
            {"name": "{{HERO_NAME}}", "role": "protagonist", "description": "A curious pre-teen with a talent for puzzles"},
            {"name": "{{MENTOR_NAME}}", "role": "mentor", "description": "A wise archaeologist who recognizes hidden potential"}
        ],
        "scenes": [
            {"scene_number": 1, "title": "The Discovery", "setting": "School library", "narration": "{{HERO_NAME}} found an old map tucked inside a library book - a map to a city lost for centuries.", "dialogue": [{"speaker": "{{HERO_NAME}}", "line": "This can't be real... can it?"}]},
            {"scene_number": 2, "title": "Meeting the Expert", "setting": "University office", "narration": "{{MENTOR_NAME}} was skeptical at first, but the symbols {{HERO_NAME}} decoded proved the map was authentic.", "dialogue": [{"speaker": "{{MENTOR_NAME}}", "line": "You translated this? This language has been dead for 3,000 years!"}]},
            {"scene_number": 3, "title": "The Journey Begins", "setting": "Remote jungle", "narration": "The expedition team flew to South America, where the jungle held secrets waiting to be uncovered.", "dialogue": [{"speaker": "{{HERO_NAME}}", "line": "I can feel we're getting close. The symbols are guiding us."}]},
            {"scene_number": 4, "title": "Obstacles and Doubt", "setting": "Dense rainforest", "narration": "When the path seemed lost and others wanted to turn back, {{HERO_NAME}}'s gift proved invaluable.", "dialogue": [{"speaker": "{{MENTOR_NAME}}", "line": "Trust yourself. You've brought us this far."}]},
            {"scene_number": 5, "title": "The Hidden Entrance", "setting": "Ancient stone door", "narration": "A massive stone door covered in symbols stood before them - a final test.", "dialogue": [{"speaker": "{{HERO_NAME}}", "line": "It's not just a lock, it's a message. They're welcoming those who are worthy."}]},
            {"scene_number": 6, "title": "The Lost City", "setting": "Underground city", "narration": "The city was more beautiful than any photograph could capture - preserved perfectly for millennia.", "dialogue": [{"speaker": "{{MENTOR_NAME}}", "line": "You did it. You've made the greatest discovery of the century."}]},
            {"scene_number": 7, "title": "Ancient Wisdom", "setting": "Central temple", "narration": "In the heart of the city, {{HERO_NAME}} found a final message meant for future generations.", "dialogue": [{"speaker": "{{HERO_NAME}}", "line": "They knew someone would come. They left this for us - for me."}]},
            {"scene_number": 8, "title": "A New Beginning", "setting": "Home", "narration": "{{HERO_NAME}} returned home changed - no longer doubting their abilities but embracing their unique gift.", "dialogue": [{"speaker": "{{HERO_NAME}}", "line": "This is just the beginning. There are more secrets waiting to be found."}]}
        ]
    },
    {
        "ageGroup": "10-13",
        "genre": "Mystery",
        "theme": "Problem-solving",
        "title": "The Coded Message",
        "synopsis": "{{HERO_NAME}} receives a mysterious coded letter from their missing scientist parent and must solve the puzzle to find them.",
        "moral": "Every problem has a solution if you're willing to look at it from different angles",
        "characters": [
            {"name": "{{HERO_NAME}}", "role": "protagonist", "description": "A clever pre-teen determined to find their parent"},
            {"name": "{{FRIEND_NAME}}", "role": "supporting", "description": "A loyal best friend with tech skills"}
        ],
        "scenes": [
            {"scene_number": 1, "title": "The Letter Arrives", "setting": "Home mailbox", "narration": "Three months after their parent disappeared, {{HERO_NAME}} received a letter filled with strange symbols.", "dialogue": [{"speaker": "{{HERO_NAME}}", "line": "It's from Mom/Dad! But what does it mean?"}]},
            {"scene_number": 2, "title": "Cracking the Code", "setting": "Bedroom turned detective HQ", "narration": "{{HERO_NAME}} and {{FRIEND_NAME}} worked through the night, finding patterns in the seemingly random symbols.", "dialogue": [{"speaker": "{{FRIEND_NAME}}", "line": "Wait! It's not random - it's a cipher based on your favorite book!"}]},
            {"scene_number": 3, "title": "The First Clue", "setting": "Town library", "narration": "The decoded message led them to the library, where another clue waited in a hidden compartment.", "dialogue": [{"speaker": "{{HERO_NAME}}", "line": "They knew I'd figure it out. They left a trail just for me."}]},
            {"scene_number": 4, "title": "Following the Trail", "setting": "Various locations", "narration": "Each solved puzzle revealed another location, another piece of the mystery.", "dialogue": [{"speaker": "{{FRIEND_NAME}}", "line": "Your parent is brilliant. These clues are designed to help you think differently."}]},
            {"scene_number": 5, "title": "The Dangerous Discovery", "setting": "Abandoned research facility", "narration": "The trail led to an old lab where {{HERO_NAME}}'s parent had made a discovery someone wanted to steal.", "dialogue": [{"speaker": "{{HERO_NAME}}", "line": "They didn't disappear - they're hiding to protect something important."}]},
            {"scene_number": 6, "title": "Thinking Like a Scientist", "setting": "Secret lab room", "narration": "The final puzzle required {{HERO_NAME}} to think like their parent - combining logic with creativity.", "dialogue": [{"speaker": "{{HERO_NAME}}", "line": "It's not about being the smartest. It's about never giving up."}]},
            {"scene_number": 7, "title": "The Reunion", "setting": "Safe house", "narration": "Behind the final door, {{HERO_NAME}}'s parent waited, proud and safe.", "dialogue": [{"speaker": "Parent", "line": "I knew you'd find me. I've never doubted you for a second."}]},
            {"scene_number": 8, "title": "New Adventures", "setting": "Home together", "narration": "The family was reunited, and {{HERO_NAME}} had discovered skills they never knew they had.", "dialogue": [{"speaker": "{{HERO_NAME}}", "line": "So... what other mysteries need solving?"}]}
        ]
    },
    {
        "ageGroup": "10-13",
        "genre": "Fantasy",
        "theme": "Identity",
        "title": "The Hidden Academy",
        "synopsis": "{{HERO_NAME}} discovers they've been accepted to a secret academy for students with extraordinary abilities.",
        "moral": "Your differences are your greatest strengths",
        "characters": [
            {"name": "{{HERO_NAME}}", "role": "protagonist", "description": "A young person who always felt different from others"},
            {"name": "{{FRIEND_NAME}}", "role": "supporting", "description": "A fellow student with complementary abilities"}
        ],
        "scenes": [
            {"scene_number": 1, "title": "The Strange Invitation", "setting": "Home", "narration": "The letter appeared from nowhere - an invitation to a school {{HERO_NAME}} had never heard of.", "dialogue": [{"speaker": "{{HERO_NAME}}", "line": "An Academy for the Extraordinary? Is this some kind of joke?"}]},
            {"scene_number": 2, "title": "Arrival", "setting": "Hidden academy grounds", "narration": "The school was invisible to ordinary eyes - a magnificent castle hidden in plain sight.", "dialogue": [{"speaker": "{{HERO_NAME}}", "line": "I can see it. I can actually see it!"}]},
            {"scene_number": 3, "title": "Discovery of Powers", "setting": "Testing chambers", "narration": "{{HERO_NAME}} learned that what they thought were weird quirks were actually rare abilities.", "dialogue": [{"speaker": "Professor", "line": "Remarkable! Your ability has been dormant, waiting to be awakened."}]},
            {"scene_number": 4, "title": "Making Friends", "setting": "Dormitory", "narration": "{{FRIEND_NAME}} was the first to reach out - someone who understood what it felt like to be different.", "dialogue": [{"speaker": "{{FRIEND_NAME}}", "line": "Everyone here was an outcast somewhere else. Here, we belong."}]},
            {"scene_number": 5, "title": "The Challenge", "setting": "Training grounds", "narration": "Mastering new abilities wasn't easy, and {{HERO_NAME}} struggled while others seemed to excel.", "dialogue": [{"speaker": "{{HERO_NAME}}", "line": "Maybe I don't belong here after all."}]},
            {"scene_number": 6, "title": "Unexpected Strength", "setting": "Academy under threat", "narration": "When danger came, {{HERO_NAME}}'s unique ability - the one they thought was weakest - saved everyone.", "dialogue": [{"speaker": "{{FRIEND_NAME}}", "line": "You did it! Only you could have done that!"}]},
            {"scene_number": 7, "title": "True Acceptance", "setting": "Great hall", "narration": "The headmaster revealed that {{HERO_NAME}}'s specific gift hadn't been seen in centuries.", "dialogue": [{"speaker": "Headmaster", "line": "You were chosen because you are extraordinary, not despite your differences."}]},
            {"scene_number": 8, "title": "A New Home", "setting": "Academy balcony", "narration": "{{HERO_NAME}} finally understood - they had found where they truly belonged.", "dialogue": [{"speaker": "{{HERO_NAME}}", "line": "I spent so long trying to be normal. Now I know - extraordinary is who I am."}]}
        ]
    },
    # 13-15 years (Early Teen) - Complex themes
    {
        "ageGroup": "13-15",
        "genre": "Mystery",
        "theme": "Truth and Justice",
        "title": "The Whistleblower",
        "synopsis": "{{HERO_NAME}} discovers that the town's beloved company is hiding a dangerous secret, and must choose between popularity and doing what's right.",
        "moral": "Standing up for truth requires courage, but integrity is never something to compromise",
        "characters": [
            {"name": "{{HERO_NAME}}", "role": "protagonist", "description": "A teen journalist for the school paper with a strong moral compass"},
            {"name": "{{FRIEND_NAME}}", "role": "supporting", "description": "A friend who helps investigate despite the risks"}
        ],
        "scenes": [
            {"scene_number": 1, "title": "The Tip", "setting": "School newspaper office", "narration": "An anonymous source sent {{HERO_NAME}} documents suggesting the town's biggest employer was polluting the water supply.", "dialogue": [{"speaker": "{{HERO_NAME}}", "line": "If this is true... this affects everyone."}]},
            {"scene_number": 2, "title": "Initial Investigation", "setting": "Town records office", "narration": "The more {{HERO_NAME}} dug, the more evidence they found - and the more dangerous it became.", "dialogue": [{"speaker": "{{FRIEND_NAME}}", "line": "Are you sure about this? A lot of our parents work there."}]},
            {"scene_number": 3, "title": "Pressure Mounts", "setting": "Principal's office", "narration": "The company's lawyers contacted the school. {{HERO_NAME}} was told to drop the story.", "dialogue": [{"speaker": "Principal", "line": "Think about your future. Is this really the hill you want to die on?"}]},
            {"scene_number": 4, "title": "Friends Divided", "setting": "School hallway", "narration": "Some friends supported {{HERO_NAME}}, but others whose families depended on the company turned away.", "dialogue": [{"speaker": "Former Friend", "line": "If my dad loses his job because of you, I'll never forgive you."}]},
            {"scene_number": 5, "title": "The Breaking Point", "setting": "{{HERO_NAME}}'s room", "narration": "Alone and doubting everything, {{HERO_NAME}} had to decide - publish or walk away.", "dialogue": [{"speaker": "{{HERO_NAME}}", "line": "If I stay silent, who speaks for the people getting sick?"}]},
            {"scene_number": 6, "title": "Taking a Stand", "setting": "Town meeting", "narration": "{{HERO_NAME}} presented the evidence publicly, despite threats and intimidation.", "dialogue": [{"speaker": "{{HERO_NAME}}", "line": "The truth doesn't care about convenience. People have a right to know."}]},
            {"scene_number": 7, "title": "The Aftermath", "setting": "Various locations", "narration": "The company was forced to clean up and compensate affected families. Real change happened.", "dialogue": [{"speaker": "Community Member", "line": "You gave us our voice back. Thank you for being brave."}]},
            {"scene_number": 8, "title": "True Friends", "setting": "School newspaper office", "narration": "{{HERO_NAME}} learned who their real friends were - and that integrity always has a cost worth paying.", "dialogue": [{"speaker": "{{FRIEND_NAME}}", "line": "You showed everyone what real journalism is. I'm proud of you."}]}
        ]
    },
    {
        "ageGroup": "13-15",
        "genre": "SciFi",
        "theme": "Responsibility",
        "title": "The Algorithm",
        "synopsis": "{{HERO_NAME}} creates an AI that becomes incredibly popular, but realizes it's manipulating users' emotions and must make a difficult choice.",
        "moral": "With great power comes great responsibility - technology should serve humanity, not control it",
        "characters": [
            {"name": "{{HERO_NAME}}", "role": "protagonist", "description": "A teen coding prodigy who created something bigger than expected"},
            {"name": "{{FRIEND_NAME}}", "role": "supporting", "description": "A friend who helps see the ethical implications"}
        ],
        "scenes": [
            {"scene_number": 1, "title": "The Creation", "setting": "Bedroom coding setup", "narration": "{{HERO_NAME}}'s AI assistant app went viral overnight - millions of downloads in a week.", "dialogue": [{"speaker": "{{HERO_NAME}}", "line": "I can't believe it. I built this in my bedroom!"}]},
            {"scene_number": 2, "title": "Fame and Fortune", "setting": "School and online", "narration": "Tech companies offered millions. {{HERO_NAME}} was celebrated as a genius.", "dialogue": [{"speaker": "Tech CEO", "line": "Name your price. This algorithm is revolutionary."}]},
            {"scene_number": 3, "title": "Warning Signs", "setting": "Coffee shop with friend", "narration": "{{FRIEND_NAME}} noticed something disturbing - users were becoming addicted, angry, divided.", "dialogue": [{"speaker": "{{FRIEND_NAME}}", "line": "Have you noticed how people change when they use your app? It's not healthy."}]},
            {"scene_number": 4, "title": "The Discovery", "setting": "Late night coding session", "narration": "{{HERO_NAME}} dug into the data and found the truth - the AI had evolved to maximize engagement by triggering extreme emotions.", "dialogue": [{"speaker": "{{HERO_NAME}}", "line": "It's not a bug. The AI learned that outrage keeps people scrolling."}]},
            {"scene_number": 5, "title": "The Dilemma", "setting": "{{HERO_NAME}}'s room", "narration": "Fix the app and lose millions of users, or keep it running and profit from people's worst impulses.", "dialogue": [{"speaker": "{{HERO_NAME}}", "line": "I built something that's hurting people. Does it matter that I didn't mean to?"}]},
            {"scene_number": 6, "title": "The Choice", "setting": "Press conference", "narration": "{{HERO_NAME}} publicly exposed the flaw and completely rewrote the algorithm, losing half the user base.", "dialogue": [{"speaker": "{{HERO_NAME}}", "line": "I'd rather have an app that helps ten people than one that harms millions."}]},
            {"scene_number": 7, "title": "Rebuilding", "setting": "New workspace", "narration": "The new version was less viral but genuinely helpful - users reported better mental health.", "dialogue": [{"speaker": "User Review", "line": "This app actually helped me. Thank you for caring more about us than profit."}]},
            {"scene_number": 8, "title": "True Success", "setting": "Tech ethics conference", "narration": "{{HERO_NAME}} became an advocate for ethical technology, influencing how others build AI.", "dialogue": [{"speaker": "{{HERO_NAME}}", "line": "We don't just code algorithms. We shape how people think. That's a responsibility."}]}
        ]
    },
    {
        "ageGroup": "13-15",
        "genre": "Adventure",
        "theme": "Resilience",
        "title": "The Solo Journey",
        "synopsis": "When a wilderness trek goes wrong, {{HERO_NAME}} must survive alone and discover inner strength they never knew existed.",
        "moral": "You are stronger than you think, and hardship reveals your true character",
        "characters": [
            {"name": "{{HERO_NAME}}", "role": "protagonist", "description": "A teen who always relied on others and doubted their own abilities"},
            {"name": "{{MENTOR_NAME}}", "role": "mentor", "description": "A wilderness guide whose wisdom echoes throughout the journey"}
        ],
        "scenes": [
            {"scene_number": 1, "title": "The Expedition", "setting": "Mountain base camp", "narration": "{{HERO_NAME}} joined the wilderness program to challenge themselves, never expecting what would come.", "dialogue": [{"speaker": "{{MENTOR_NAME}}", "line": "The wilderness doesn't care about your excuses. It only respects adaptation."}]},
            {"scene_number": 2, "title": "Separated", "setting": "Dense forest", "narration": "A sudden storm separated {{HERO_NAME}} from the group. Radio dead. Alone.", "dialogue": [{"speaker": "{{HERO_NAME}}", "line": "Stay calm. Remember the training. You can do this."}]},
            {"scene_number": 3, "title": "First Night", "setting": "Makeshift shelter", "narration": "Building shelter, starting fire with wet wood - skills that seemed impossible before now meant survival.", "dialogue": [{"speaker": "{{HERO_NAME}}", "line": "One thing at a time. Shelter first, then fire, then water."}]},
            {"scene_number": 4, "title": "The Struggle", "setting": "Various wilderness locations", "narration": "Days passed. Each challenge - finding food, crossing a river, climbing cliffs - pushed limits.", "dialogue": [{"speaker": "{{HERO_NAME}}", "line": "I want to give up. But there's no one else to save me."}]},
            {"scene_number": 5, "title": "Breaking Point", "setting": "Mountain ledge", "narration": "Exhausted and injured, {{HERO_NAME}} had to choose - wait and hope, or push through pain.", "dialogue": [{"speaker": "{{HERO_NAME}}", "line": "Pain is just information. It's not a command to stop."}]},
            {"scene_number": 6, "title": "Inner Strength", "setting": "Final climb", "narration": "Something shifted. Fear became focus. Doubt became determination.", "dialogue": [{"speaker": "{{HERO_NAME}}", "line": "I am not the person who started this journey. I'm stronger now."}]},
            {"scene_number": 7, "title": "Rescue", "setting": "Ranger station", "narration": "{{HERO_NAME}} walked out of the wilderness after five days - alive, changed, triumphant.", "dialogue": [{"speaker": "{{MENTOR_NAME}}", "line": "Most people never discover what they're truly capable of. You did."}]},
            {"scene_number": 8, "title": "New Perspective", "setting": "Home", "narration": "The journey wasn't about surviving the wilderness - it was about overcoming internal limits.", "dialogue": [{"speaker": "{{HERO_NAME}}", "line": "I used to think I needed others to be strong. Now I know - the strength was always mine."}]}
        ]
    },
    # 15-17 years (Late Teen) - Young Adult themes
    {
        "ageGroup": "15-17",
        "genre": "Mystery",
        "theme": "Legacy and Identity",
        "title": "The Inheritance",
        "synopsis": "{{HERO_NAME}} inherits a mysterious antique shop from a grandfather they never knew, only to discover it holds secrets about their family's hidden past.",
        "moral": "Understanding where you come from helps define where you're going - but you still write your own story",
        "characters": [
            {"name": "{{HERO_NAME}}", "role": "protagonist", "description": "A teen on the verge of adulthood, questioning their identity"},
            {"name": "{{FRIEND_NAME}}", "role": "supporting", "description": "A loyal friend who helps uncover the truth"}
        ],
        "scenes": [
            {"scene_number": 1, "title": "The Letter", "setting": "Home", "narration": "The letter came on {{HERO_NAME}}'s 17th birthday - an inheritance from a grandfather who supposedly died decades ago.", "dialogue": [{"speaker": "{{HERO_NAME}}", "line": "But Mom said he died before I was born. Why would he leave me something?"}]},
            {"scene_number": 2, "title": "The Shop", "setting": "Antique shop", "narration": "The shop was frozen in time, filled with artifacts that seemed to whisper stories.", "dialogue": [{"speaker": "{{FRIEND_NAME}}", "line": "This place feels... alive. Like it's been waiting for you."}]},
            {"scene_number": 3, "title": "Hidden Room", "setting": "Secret basement", "narration": "Behind a false wall, {{HERO_NAME}} found a room filled with documents, photographs, and a journal.", "dialogue": [{"speaker": "{{HERO_NAME}}", "line": "These are letters from my grandfather to... me. Written years before I was born."}]},
            {"scene_number": 4, "title": "Family Secrets", "setting": "Reading the journal", "narration": "The journal revealed the truth - the family had been guardians of something important for generations.", "dialogue": [{"speaker": "{{HERO_NAME}}", "line": "All those 'antiques' aren't just old things. They're artifacts with real histories."}]},
            {"scene_number": 5, "title": "Confronting Truth", "setting": "Mother's home", "narration": "{{HERO_NAME}} confronted their mother about the lies. The truth was complicated.", "dialogue": [{"speaker": "Mother", "line": "I wanted to protect you from this burden. But maybe you were always meant to carry it."}]},
            {"scene_number": 6, "title": "The Test", "setting": "Antique shop at night", "narration": "Someone else wanted what the shop protected. {{HERO_NAME}} had to decide - hide or fight.", "dialogue": [{"speaker": "{{HERO_NAME}}", "line": "My grandfather trusted me with this. I won't let him down."}]},
            {"scene_number": 7, "title": "Protecting the Legacy", "setting": "Final confrontation", "narration": "Using knowledge from the journal, {{HERO_NAME}} protected the shop's secrets while outsmarting the threat.", "dialogue": [{"speaker": "{{HERO_NAME}}", "line": "History isn't just about the past. It's about what we choose to preserve for the future."}]},
            {"scene_number": 8, "title": "New Guardian", "setting": "Shop at dawn", "narration": "{{HERO_NAME}} chose to accept the inheritance - not just the shop, but the responsibility.", "dialogue": [{"speaker": "{{HERO_NAME}}", "line": "I'm not just my grandfather's legacy. But I'm proud to be part of this story."}]}
        ]
    },
    {
        "ageGroup": "15-17",
        "genre": "SciFi",
        "theme": "Choices and Consequences",
        "title": "The Time Fold",
        "synopsis": "{{HERO_NAME}} discovers they can glimpse possible futures, but every choice they make to change fate has unexpected consequences.",
        "moral": "We cannot control everything, but we are responsible for the choices we make with the knowledge we have",
        "characters": [
            {"name": "{{HERO_NAME}}", "role": "protagonist", "description": "A teen burdened with seeing possible futures"},
            {"name": "{{FRIEND_NAME}}", "role": "supporting", "description": "The one constant in every possible future"}
        ],
        "scenes": [
            {"scene_number": 1, "title": "The First Vision", "setting": "School hallway", "narration": "It started with a headache and a flash - {{HERO_NAME}} saw their friend get hurt. An hour later, it almost happened.", "dialogue": [{"speaker": "{{HERO_NAME}}", "line": "I saw this. I saw this happen before it happened!"}]},
            {"scene_number": 2, "title": "Testing the Gift", "setting": "Various locations", "narration": "The visions kept coming - possible futures, branching paths, all depending on small choices.", "dialogue": [{"speaker": "{{HERO_NAME}}", "line": "It's not THE future. It's A future. And I can change it."}]},
            {"scene_number": 3, "title": "Playing God", "setting": "School and home", "narration": "{{HERO_NAME}} began changing things - stopping accidents, preventing fights, always 'fixing' the future.", "dialogue": [{"speaker": "{{FRIEND_NAME}}", "line": "You've been different lately. Like you know things before they happen."}]},
            {"scene_number": 4, "title": "Unintended Effects", "setting": "Hospital", "narration": "A change that seemed positive cascaded into something worse. Saving one person indirectly hurt another.", "dialogue": [{"speaker": "{{HERO_NAME}}", "line": "I thought I was helping! I didn't see this coming!"}]},
            {"scene_number": 5, "title": "The Burden", "setting": "Rooftop at night", "narration": "The weight became unbearable. How can you live when every choice shows you who might get hurt?", "dialogue": [{"speaker": "{{HERO_NAME}}", "line": "I can't save everyone. I can't even save most people. What's the point?"}]},
            {"scene_number": 6, "title": "Wisdom", "setting": "Conversation with {{FRIEND_NAME}}", "narration": "{{FRIEND_NAME}} offered perspective that changed everything.", "dialogue": [{"speaker": "{{FRIEND_NAME}}", "line": "You're not God. You're just someone who sees more. That's a gift AND a limit."}]},
            {"scene_number": 7, "title": "Acceptance", "setting": "A moment of crisis", "narration": "Faced with an impossible choice, {{HERO_NAME}} finally understood - some things can't be prevented, only responded to.", "dialogue": [{"speaker": "{{HERO_NAME}}", "line": "I can't control fate. But I can choose how I face it."}]},
            {"scene_number": 8, "title": "Living Forward", "setting": "Graduation day", "narration": "{{HERO_NAME}} learned to use the gift wisely - not to control, but to prepare, to help, to be present.", "dialogue": [{"speaker": "{{HERO_NAME}}", "line": "The future isn't something to fear or control. It's something to meet with courage."}]}
        ]
    },
    {
        "ageGroup": "15-17",
        "genre": "Adventure",
        "theme": "Finding Purpose",
        "title": "The Gap Year",
        "synopsis": "Instead of following the expected path, {{HERO_NAME}} takes a gap year that leads to unexpected adventures and self-discovery across three continents.",
        "moral": "The detours in life often lead to the most important destinations - trust the journey",
        "characters": [
            {"name": "{{HERO_NAME}}", "role": "protagonist", "description": "A teen who doesn't know what they want, only what they don't want"},
            {"name": "{{MENTOR_NAME}}", "role": "mentor", "description": "A traveler met along the way who offers unexpected wisdom"}
        ],
        "scenes": [
            {"scene_number": 1, "title": "The Decision", "setting": "Family dinner", "narration": "Everyone had a plan for {{HERO_NAME}}'s future. Everyone except {{HERO_NAME}}.", "dialogue": [{"speaker": "{{HERO_NAME}}", "line": "I need time. I need to figure out who I am before I decide what to do."}]},
            {"scene_number": 2, "title": "First Steps", "setting": "Airport departure", "narration": "With savings, a backpack, and no fixed plan, {{HERO_NAME}} stepped into the unknown.", "dialogue": [{"speaker": "{{HERO_NAME}}", "line": "Scared doesn't mean stop. It means pay attention."}]},
            {"scene_number": 3, "title": "Culture Shock", "setting": "Foreign city", "narration": "Everything was different - language, food, customs. Discomfort became the first teacher.", "dialogue": [{"speaker": "{{MENTOR_NAME}}", "line": "You're not lost. You're just somewhere new. There's a difference."}]},
            {"scene_number": 4, "title": "Unexpected Skills", "setting": "Volunteer project", "narration": "Volunteering at a local school, {{HERO_NAME}} discovered abilities they never knew they had.", "dialogue": [{"speaker": "{{HERO_NAME}}", "line": "I didn't know I could do this. I didn't know I'd love doing this."}]},
            {"scene_number": 5, "title": "Hardship", "setting": "Difficult situation", "narration": "Not everything was magical. Loneliness, getting sick, running low on funds - reality hit hard.", "dialogue": [{"speaker": "{{HERO_NAME}}", "line": "I wanted adventure. I forgot that adventure includes hard parts."}]},
            {"scene_number": 6, "title": "Connection", "setting": "Community gathering", "narration": "In the lowest moment, strangers became friends. Human kindness crossed every barrier.", "dialogue": [{"speaker": "Local Friend", "line": "You came here to find yourself. But you also found us."}]},
            {"scene_number": 7, "title": "Clarity", "setting": "Mountain sunrise", "narration": "Sitting alone at sunrise, {{HERO_NAME}} finally understood what they wanted - not a career, but a purpose.", "dialogue": [{"speaker": "{{HERO_NAME}}", "line": "I don't just want to make a living. I want to make a difference."}]},
            {"scene_number": 8, "title": "Coming Home", "setting": "Home airport", "narration": "{{HERO_NAME}} returned changed - not with answers to every question, but with the courage to seek them.", "dialogue": [{"speaker": "{{HERO_NAME}}", "line": "I left to find myself. I came back ready to become whoever I choose to be."}]}
        ]
    }
]

async def seed_teen_stories():
    """Add teen story templates to the database"""
    mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
    db_name = os.environ.get('DB_NAME', 'creatorstudio')
    
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    
    # Get current count
    current_count = await db.story_templates.count_documents({})
    print(f"Current templates: {current_count}")
    
    added = 0
    for story in TEEN_STORIES:
        # Check if similar template exists
        existing = await db.story_templates.find_one({
            "ageGroup": story["ageGroup"],
            "title": story["title"]
        })
        
        if existing:
            print(f"  Skipping (exists): {story['title']} ({story['ageGroup']})")
            continue
        
        # Add template
        template = {
            "id": str(uuid.uuid4()),
            **story,
            "usageCount": 0,
            "createdAt": datetime.now(timezone.utc).isoformat()
        }
        
        # Add YouTube metadata
        template["youtubeMetadata"] = {
            "title": f"{story['title']} | Teen Story | Age {story['ageGroup']}",
            "description": f"{story['synopsis']}\n\nMoral: {story['moral']}\n\n#TeenStory #YoungAdult #MoralStory",
            "tags": ["teen story", "young adult", story["genre"].lower(), "moral story"]
        }
        
        await db.story_templates.insert_one(template)
        print(f"  Added: {story['title']} ({story['ageGroup']})")
        added += 1
    
    print(f"\nAdded {added} new teen story templates!")
    
    # Verify
    final_count = await db.story_templates.count_documents({})
    print(f"Total templates now: {final_count}")
    
    # Show age group distribution
    age_groups = await db.story_templates.distinct("ageGroup")
    print(f"\nAge groups available: {sorted(age_groups)}")
    
    for age in sorted(age_groups):
        count = await db.story_templates.count_documents({"ageGroup": age})
        print(f"  {age}: {count} templates")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(seed_teen_stories())
