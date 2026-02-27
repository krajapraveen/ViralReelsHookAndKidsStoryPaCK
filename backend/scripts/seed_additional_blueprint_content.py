"""
Blueprint Library Additional Content Seeder
Adds more hooks, frameworks, and story ideas to the database
"""
import asyncio
import uuid
from datetime import datetime, timezone


async def seed_additional_content(db):
    """
    Seed additional content for the Blueprint Library.
    This expands the existing content significantly.
    """
    
    # =========================================================================
    # ADDITIONAL VIRAL HOOKS (50+ more)
    # =========================================================================
    additional_hooks = [
        # More Motivation hooks
        {"niche": "Motivation", "hook_text": "I was broke at 25. Here's what changed.", "engagement_score": 93, "featured": False,
         "variations": ["At 25 I had $200. At 30 I had...", "From broke to blessed in 5 years"],
         "script_template": "Hook → Rock bottom story → Turning point → Steps taken → Current success", "best_for": "Transformation stories"},
        
        {"niche": "Motivation", "hook_text": "The habit that millionaires never skip.", "engagement_score": 91, "featured": False,
         "variations": ["What rich people do every morning", "One thing all successful people have in common"],
         "script_template": "Hook → Reveal habit → Why it works → How to implement → CTA", "best_for": "Habit content"},
        
        {"niche": "Motivation", "hook_text": "If you're watching this at 3am, it's for you.", "engagement_score": 89, "featured": False,
         "variations": ["Can't sleep? This is your sign.", "Lying awake? You needed to hear this."],
         "script_template": "Hook → Relate to struggle → Offer hope → Action step → Encouragement", "best_for": "Late night motivation"},
        
        {"niche": "Motivation", "hook_text": "They laughed when I started. They stopped.", "engagement_score": 94, "featured": True,
         "variations": ["Everyone doubted me. Here's what happened.", "From jokes to jealousy"],
         "script_template": "Hook → Doubt faced → Persistence shown → Results achieved → Lesson", "best_for": "Proof of concept stories"},
        
        {"niche": "Motivation", "hook_text": "Your comfort zone is killing your dreams.", "engagement_score": 88, "featured": False,
         "variations": ["Comfort feels good. Until it doesn't.", "Why being comfortable is dangerous"],
         "script_template": "Hook → Explain comfort trap → Examples → Breaking free → Challenge", "best_for": "Push content"},
        
        # More Business hooks
        {"niche": "Business", "hook_text": "I turned $100 into $10,000 using this method.", "engagement_score": 95, "featured": True,
         "variations": ["How I 100x'd my investment", "The $100 challenge that changed everything"],
         "script_template": "Hook → Starting point → Strategy reveal → Execution → Results", "best_for": "Investment/growth stories"},
        
        {"niche": "Business", "hook_text": "The side hustle that works while you sleep.", "engagement_score": 92, "featured": True,
         "variations": ["Making money at 3am without waking up", "True passive income explained"],
         "script_template": "Hook → Concept introduction → How it works → Setup steps → Income proof", "best_for": "Passive income"},
        
        {"niche": "Business", "hook_text": "Why most businesses fail in year one (and how to avoid it).", "engagement_score": 87, "featured": False,
         "variations": ["90% of businesses fail. Here's why.", "The startup killer nobody talks about"],
         "script_template": "Hook → Statistics → Common mistakes → Solutions → Success path", "best_for": "Business education"},
        
        {"niche": "Business", "hook_text": "The email that landed me a $50k client.", "engagement_score": 90, "featured": False,
         "variations": ["One email changed my business", "The outreach template that works"],
         "script_template": "Hook → Context → Email breakdown → Why it worked → Template offer", "best_for": "Sales/outreach"},
        
        {"niche": "Business", "hook_text": "Stop selling. Start this instead.", "engagement_score": 86, "featured": False,
         "variations": ["Why selling doesn't work anymore", "The new way to get customers"],
         "script_template": "Hook → Problem with selling → New approach → Examples → How to start", "best_for": "Marketing education"},
        
        # More Fitness hooks
        {"niche": "Fitness", "hook_text": "The exercise you're doing wrong (and hurting yourself).", "engagement_score": 92, "featured": True,
         "variations": ["Stop! You're damaging your joints.", "The workout mistake 90% make"],
         "script_template": "Hook → Wrong form demo → Risks explained → Correct form → Practice tips", "best_for": "Form correction"},
        
        {"niche": "Fitness", "hook_text": "Build muscle without going to the gym.", "engagement_score": 89, "featured": False,
         "variations": ["No gym? No problem.", "Home workout that actually builds muscle"],
         "script_template": "Hook → Equipment needed (minimal) → Exercises → Routine → Results timeline", "best_for": "Home fitness"},
        
        {"niche": "Fitness", "hook_text": "What I eat in a day to stay shredded.", "engagement_score": 91, "featured": False,
         "variations": ["My exact meal plan revealed", "Eat this, look like this"],
         "script_template": "Hook → Breakfast → Lunch → Dinner → Snacks → Macros breakdown", "best_for": "Meal content"},
        
        {"niche": "Fitness", "hook_text": "The protein myth that's holding you back.", "engagement_score": 85, "featured": False,
         "variations": ["You don't need that much protein", "Stop wasting money on protein"],
         "script_template": "Hook → Common myth → Science → Real requirement → Practical advice", "best_for": "Nutrition education"},
        
        # More Tech hooks
        {"niche": "Tech", "hook_text": "Free apps that feel illegal to know about.", "engagement_score": 96, "featured": True,
         "variations": ["Apps they don't want you to find", "The best free apps of 2024"],
         "script_template": "Hook → App 1 → App 2 → App 3 → App 4 → App 5 → How to get them", "best_for": "App discovery"},
        
        {"niche": "Tech", "hook_text": "Your phone is tracking you. Here's how to stop it.", "engagement_score": 93, "featured": True,
         "variations": ["Privacy settings you need to change", "Stop Apple/Google from spying"],
         "script_template": "Hook → What's being tracked → Privacy risks → Settings to change → Tools to use", "best_for": "Privacy content"},
        
        {"niche": "Tech", "hook_text": "AI just changed everything. Here's how to use it.", "engagement_score": 94, "featured": True,
         "variations": ["The AI tool everyone's sleeping on", "How to 10x productivity with AI"],
         "script_template": "Hook → Tool introduction → Use cases → Demo → Getting started", "best_for": "AI tools"},
        
        {"niche": "Tech", "hook_text": "Keyboard shortcuts that save hours every week.", "engagement_score": 88, "featured": False,
         "variations": ["Stop using your mouse for this", "Work 2x faster with these shortcuts"],
         "script_template": "Hook → Shortcut 1 → Shortcut 2 → Shortcut 3 → Practice challenge", "best_for": "Productivity tips"},
        
        # More Lifestyle hooks
        {"niche": "Lifestyle", "hook_text": "Habits I quit that doubled my happiness.", "engagement_score": 90, "featured": True,
         "variations": ["Stop doing this for instant peace", "The habits making you miserable"],
         "script_template": "Hook → Habit 1 & why → Habit 2 & why → Results → How to quit", "best_for": "Habit breaking"},
        
        {"niche": "Lifestyle", "hook_text": "Living alone changed me in ways I didn't expect.", "engagement_score": 87, "featured": False,
         "variations": ["What solo living teaches you", "Lessons from living alone for a year"],
         "script_template": "Hook → Expectation vs Reality → Lessons → Growth → Advice", "best_for": "Solo life content"},
        
        {"niche": "Lifestyle", "hook_text": "The $5 hack that makes my apartment look expensive.", "engagement_score": 89, "featured": False,
         "variations": ["Budget decor that looks luxury", "How to fake an expensive home"],
         "script_template": "Hook → Item reveal → Where to buy → How to style → Before/after", "best_for": "Home decor"},
        
        # More Relationships hooks
        {"niche": "Relationships", "hook_text": "The phrase that ended every argument in my relationship.", "engagement_score": 92, "featured": True,
         "variations": ["One sentence that saves relationships", "Stop fighting with this trick"],
         "script_template": "Hook → Phrase reveal → Why it works → How to use it → Example", "best_for": "Relationship advice"},
        
        {"niche": "Relationships", "hook_text": "Signs they're not the one (I learned the hard way).", "engagement_score": 88, "featured": False,
         "variations": ["Red flags I ignored", "When to walk away from love"],
         "script_template": "Hook → Sign 1 → Sign 2 → Sign 3 → What I did → Advice", "best_for": "Dating advice"},
        
        {"niche": "Relationships", "hook_text": "How I knew my partner was 'the one'.", "engagement_score": 86, "featured": False,
         "variations": ["The moment I knew", "Signs you've found your person"],
         "script_template": "Hook → Story setup → The moment → Green flags → Relationship now", "best_for": "Love stories"},
        
        # More Food hooks
        {"niche": "Food", "hook_text": "The ingredient that makes everything taste better.", "engagement_score": 91, "featured": True,
         "variations": ["Chef's secret ingredient revealed", "Why your food tastes bland"],
         "script_template": "Hook → Ingredient reveal → Why it works → How to use → Demo", "best_for": "Cooking tips"},
        
        {"niche": "Food", "hook_text": "Grandma's recipe I finally got permission to share.", "engagement_score": 89, "featured": False,
         "variations": ["Family secret recipe revealed", "100-year-old recipe goes viral"],
         "script_template": "Hook → Story behind recipe → Ingredients → Steps → Final reveal", "best_for": "Recipe content"},
        
        {"niche": "Food", "hook_text": "What I order at every restaurant to impress my date.", "engagement_score": 84, "featured": False,
         "variations": ["How to order like a pro", "Restaurant secrets from a foodie"],
         "script_template": "Hook → Ordering tips → What to avoid → What to try → Date impressed", "best_for": "Dining content"},
        
        # More Parenting hooks
        {"niche": "Parenting", "hook_text": "The parenting hack that gave me my life back.", "engagement_score": 91, "featured": True,
         "variations": ["How I finally got free time as a parent", "The trick that changed everything"],
         "script_template": "Hook → Problem faced → Hack revealed → Implementation → Results", "best_for": "Parenting tips"},
        
        {"niche": "Parenting", "hook_text": "What I tell my kids instead of 'good job'.", "engagement_score": 88, "featured": False,
         "variations": ["Why I stopped saying good job", "Better ways to praise children"],
         "script_template": "Hook → Problem with praise → Alternative phrases → Why it works → Examples", "best_for": "Child development"},
        
        {"niche": "Parenting", "hook_text": "Screen time rules that actually work.", "engagement_score": 86, "featured": False,
         "variations": ["How we handle screens in our house", "No more screen time battles"],
         "script_template": "Hook → Rules explained → Why they work → Implementation → Results", "best_for": "Digital parenting"},
        
        # Finance niche
        {"niche": "Finance", "hook_text": "The investment I wish I made at 20.", "engagement_score": 93, "featured": True,
         "variations": ["What I'd tell my 20-year-old self about money", "The $100 that became $100k"],
         "script_template": "Hook → Investment reveal → How it works → Why start young → Getting started", "best_for": "Investment advice"},
        
        {"niche": "Finance", "hook_text": "How I save $1000 a month without noticing.", "engagement_score": 90, "featured": True,
         "variations": ["Painless saving hacks", "Money saving on autopilot"],
         "script_template": "Hook → Method 1 → Method 2 → Method 3 → Total savings → Start now", "best_for": "Saving tips"},
        
        {"niche": "Finance", "hook_text": "The bank doesn't want you to know this.", "engagement_score": 87, "featured": False,
         "variations": ["Banking secrets revealed", "Stop losing money to your bank"],
         "script_template": "Hook → Secret revealed → Why they hide it → How to benefit → Action step", "best_for": "Banking tips"},
        
        # Career niche
        {"niche": "Career", "hook_text": "How I negotiated a 40% raise (word for word).", "engagement_score": 94, "featured": True,
         "variations": ["The exact script I used", "Never accept the first offer"],
         "script_template": "Hook → Context → Script breakdown → Response handling → Result", "best_for": "Salary negotiation"},
        
        {"niche": "Career", "hook_text": "The resume mistake that's costing you interviews.", "engagement_score": 89, "featured": False,
         "variations": ["Why your resume isn't working", "Resume red flags to fix now"],
         "script_template": "Hook → Mistake revealed → Why it matters → How to fix → Better example", "best_for": "Job hunting"},
        
        {"niche": "Career", "hook_text": "Skills that will be worth millions in 5 years.", "engagement_score": 91, "featured": True,
         "variations": ["Future-proof your career", "What to learn right now"],
         "script_template": "Hook → Skill 1 → Skill 2 → Skill 3 → How to learn → Start today", "best_for": "Career development"},
        
        # Mental Health niche
        {"niche": "Mental Health", "hook_text": "The 5-minute habit that cured my anxiety.", "engagement_score": 92, "featured": True,
         "variations": ["How I finally found peace", "Anxiety hack that actually works"],
         "script_template": "Hook → My struggle → Discovery → The habit → How to do it → Results", "best_for": "Anxiety relief"},
        
        {"niche": "Mental Health", "hook_text": "It's okay to not be okay (and here's why).", "engagement_score": 88, "featured": False,
         "variations": ["Permission to feel your feelings", "Stop pretending you're fine"],
         "script_template": "Hook → Normalize struggle → Why we hide it → Permission given → Path forward", "best_for": "Mental health awareness"},
        
        {"niche": "Mental Health", "hook_text": "Things I do when I'm overwhelmed.", "engagement_score": 86, "featured": False,
         "variations": ["My emergency calm-down routine", "When everything feels like too much"],
         "script_template": "Hook → Acknowledge feeling → Coping strategy 1 → Strategy 2 → Strategy 3 → You've got this", "best_for": "Coping strategies"},
    ]
    
    # Add IDs and timestamps
    for hook in additional_hooks:
        hook["id"] = str(uuid.uuid4())
        hook["created_at"] = datetime.now(timezone.utc).isoformat()
    
    # Insert if collection is small
    existing_count = await db.blueprint_hooks.count_documents({})
    if existing_count < 100:
        await db.blueprint_hooks.insert_many(additional_hooks)
        print(f"Added {len(additional_hooks)} new hooks")
    
    # =========================================================================
    # ADDITIONAL FRAMEWORKS (10+ more)
    # =========================================================================
    additional_frameworks = [
        {
            "category": "Trending",
            "title": "The Duet/Stitch Response Framework",
            "description": "Ride viral waves by reacting to trending content with your unique perspective.",
            "featured": True,
            "preview_hook": "Wait... did they really just say that?",
            "full_script": {
                "hook": {"text": "[REACTION] to what they said. Let me explain why this is [RIGHT/WRONG].", "duration": "0-3s"},
                "context": {"text": "So they said [QUOTE]. Here's the thing...", "duration": "3-10s"},
                "your_take": {"text": "[YOUR PERSPECTIVE]. And here's why it matters.", "duration": "10-22s"},
                "value_add": {"text": "What you should actually do is [BETTER ADVICE].", "duration": "22-27s"},
                "cta": {"text": "Agree? Disagree? Let me know. Follow for more real talk.", "duration": "27-30s"}
            },
            "scene_breakdown": [
                {"scene": 1, "visual": "Split screen with original", "action": "Show genuine reaction"},
                {"scene": 2, "visual": "Quote on screen", "action": "Reference what was said"},
                {"scene": 3, "visual": "Your explanation", "action": "Be confident"},
                {"scene": 4, "visual": "Better solution", "action": "Add value"},
                {"scene": 5, "visual": "CTA", "action": "Invite debate"}
            ],
            "cta_options": ["Stitch this with your take", "What do you think?", "Am I wrong?"],
            "best_niches": ["Commentary", "Education", "Entertainment"],
            "estimated_engagement": "Very High (Viral Potential)"
        },
        
        {
            "category": "Storytelling",
            "title": "The Storytime Hook Framework",
            "description": "Master the art of addictive storytelling that keeps viewers watching until the end.",
            "featured": True,
            "preview_hook": "So there I was, at 2am, when I heard the knock...",
            "full_script": {
                "hook": {"text": "What happened next changed everything. Let me tell you about the time...", "duration": "0-3s"},
                "setup": {"text": "It was [TIME/PLACE]. I was [DOING SOMETHING NORMAL].", "duration": "3-8s"},
                "conflict": {"text": "Then [UNEXPECTED THING HAPPENED]. I couldn't believe it.", "duration": "8-15s"},
                "tension": {"text": "Here's where it gets crazy. [BUILD SUSPENSE].", "duration": "15-22s"},
                "resolution": {"text": "[REVEAL]. And that's when I learned [LESSON].", "duration": "22-28s"},
                "cta": {"text": "Want part 2? Follow and comment PART2.", "duration": "28-30s"}
            },
            "scene_breakdown": [
                {"scene": 1, "visual": "Dramatic opening", "action": "Create curiosity"},
                {"scene": 2, "visual": "Set the scene", "action": "Ground the viewer"},
                {"scene": 3, "visual": "The twist", "action": "Build tension"},
                {"scene": 4, "visual": "Peak drama", "action": "Keep them hooked"},
                {"scene": 5, "visual": "Resolution + CTA", "action": "Satisfy + engage"}
            ],
            "cta_options": ["Part 2?", "Has this happened to you?", "The craziest part is in part 2"],
            "best_niches": ["Entertainment", "Lifestyle", "Any personal story"],
            "estimated_engagement": "Very High"
        },
        
        {
            "category": "Educational",
            "title": "The Before/After Transformation Framework",
            "description": "Show dramatic results with this proven format that builds desire and trust.",
            "featured": False,
            "preview_hook": "Day 1 vs Day 30. The results speak for themselves.",
            "full_script": {
                "hook": {"text": "This is me [BEFORE]. And this is me [AFTER]. Here's exactly what I did.", "duration": "0-4s"},
                "before": {"text": "Before, I was [PROBLEM STATE]. I felt [EMOTION].", "duration": "4-10s"},
                "method": {"text": "Then I started [METHOD]. It wasn't easy but...", "duration": "10-18s"},
                "after": {"text": "Now look at [RESULT]. It took [TIME] but it was worth it.", "duration": "18-25s"},
                "cta": {"text": "Want my exact blueprint? Follow and DM me START.", "duration": "25-30s"}
            },
            "scene_breakdown": [
                {"scene": 1, "visual": "Split before/after", "action": "Shock value"},
                {"scene": 2, "visual": "Before footage", "action": "Relatable struggle"},
                {"scene": 3, "visual": "Process montage", "action": "Show the work"},
                {"scene": 4, "visual": "After reveal", "action": "Celebrate results"},
                {"scene": 5, "visual": "CTA", "action": "Offer help"}
            ],
            "cta_options": ["Save this", "Start your journey", "DM me for the full plan"],
            "best_niches": ["Fitness", "Finance", "Skills", "Lifestyle"],
            "estimated_engagement": "High"
        },
        
        {
            "category": "Engagement",
            "title": "The This or That Framework",
            "description": "Drive massive comments by making viewers choose between options.",
            "featured": False,
            "preview_hook": "Option A or Option B? This reveals everything about you.",
            "full_script": {
                "hook": {"text": "Your choice says everything about who you are. Ready?", "duration": "0-3s"},
                "choice1": {"text": "Option A: [FIRST CHOICE]. If you pick this, you're [PERSONALITY].", "duration": "3-10s"},
                "choice2": {"text": "Option B: [SECOND CHOICE]. This means you're [PERSONALITY].", "duration": "10-17s"},
                "your_pick": {"text": "I personally choose [YOUR PICK] because [REASON].", "duration": "17-24s"},
                "cta": {"text": "Comment A or B. Let's see what team wins!", "duration": "24-30s"}
            },
            "scene_breakdown": [
                {"scene": 1, "visual": "Set up the choice", "action": "Create curiosity"},
                {"scene": 2, "visual": "Show Option A", "action": "Make it appealing"},
                {"scene": 3, "visual": "Show Option B", "action": "Make it equally good"},
                {"scene": 4, "visual": "Your choice", "action": "Take a side"},
                {"scene": 5, "visual": "CTA", "action": "Demand participation"}
            ],
            "cta_options": ["A or B?", "Comment your pick", "Team A or Team B?"],
            "best_niches": ["Any niche", "Lifestyle", "Food", "Fashion"],
            "estimated_engagement": "Very High (Comment Bait)"
        },
        
        {
            "category": "Sales",
            "title": "The Soft Sell Value Framework",
            "description": "Sell without selling by leading with pure value first.",
            "featured": True,
            "preview_hook": "Free game that took me years to figure out...",
            "full_script": {
                "hook": {"text": "I'm about to give away information people pay $1000 for. Save this.", "duration": "0-4s"},
                "value1": {"text": "First, [VALUABLE TIP 1]. This alone will [BENEFIT].", "duration": "4-10s"},
                "value2": {"text": "Second, [VALUABLE TIP 2]. Most people don't know this.", "duration": "10-16s"},
                "value3": {"text": "Third, [VALUABLE TIP 3]. This is the game changer.", "duration": "16-22s"},
                "soft_sell": {"text": "Want all [NUMBER] strategies? Link in bio. But these 3 will get you started.", "duration": "22-30s"}
            },
            "scene_breakdown": [
                {"scene": 1, "visual": "Bold promise", "action": "Hook with value"},
                {"scene": 2, "visual": "Deliver tip 1", "action": "Over-deliver"},
                {"scene": 3, "visual": "Deliver tip 2", "action": "Build trust"},
                {"scene": 4, "visual": "Deliver tip 3", "action": "Create desire for more"},
                {"scene": 5, "visual": "Soft CTA", "action": "Mention product casually"}
            ],
            "cta_options": ["Full guide in bio", "DM me GUIDE for more", "This is just the start"],
            "best_niches": ["Business", "Education", "Coaching", "Digital Products"],
            "estimated_engagement": "High (Converts well)"
        },
        
        {
            "category": "Relatable",
            "title": "The POV Skit Framework",
            "description": "Create relatable content that makes viewers feel seen and understood.",
            "featured": False,
            "preview_hook": "POV: You're trying to adult but adulting is hard",
            "full_script": {
                "hook": {"text": "POV: [RELATABLE SITUATION SETUP]", "duration": "0-2s"},
                "scenario": {"text": "[ACT OUT THE RELATABLE MOMENT]", "duration": "2-20s"},
                "punchline": {"text": "[FUNNY/RELATABLE ENDING]", "duration": "20-26s"},
                "cta": {"text": "Tag someone who does this 😂 Follow for more!", "duration": "26-30s"}
            },
            "scene_breakdown": [
                {"scene": 1, "visual": "POV text overlay", "action": "Set the scene"},
                {"scene": 2, "visual": "Act it out", "action": "Be expressive"},
                {"scene": 3, "visual": "Continue scene", "action": "Build to punchline"},
                {"scene": 4, "visual": "Punchline", "action": "Land the joke"},
                {"scene": 5, "visual": "CTA", "action": "Encourage tags/shares"}
            ],
            "cta_options": ["Tag someone who relates", "Is this just me?", "Follow for daily laughs"],
            "best_niches": ["Comedy", "Lifestyle", "Parenting", "Work Life"],
            "estimated_engagement": "Very High (Shareable)"
        },
        
        {
            "category": "Authority",
            "title": "The Industry Insider Framework",
            "description": "Position yourself as an expert by sharing insider knowledge others don't have.",
            "featured": True,
            "preview_hook": "As someone who's worked in [INDUSTRY] for 10 years...",
            "full_script": {
                "hook": {"text": "I've been in [INDUSTRY] for [YEARS]. Here's what they won't tell you.", "duration": "0-4s"},
                "insider1": {"text": "First, [INSIDER SECRET 1]. This is how it really works.", "duration": "4-12s"},
                "insider2": {"text": "Second, [INSIDER SECRET 2]. I've seen this a hundred times.", "duration": "12-20s"},
                "advice": {"text": "Here's what you should do instead: [ACTIONABLE ADVICE].", "duration": "20-26s"},
                "cta": {"text": "Follow for more industry secrets they don't want you to know.", "duration": "26-30s"}
            },
            "scene_breakdown": [
                {"scene": 1, "visual": "Establish credibility", "action": "State experience"},
                {"scene": 2, "visual": "Reveal secret 1", "action": "Shock them"},
                {"scene": 3, "visual": "Reveal secret 2", "action": "Build trust"},
                {"scene": 4, "visual": "Give solution", "action": "Add value"},
                {"scene": 5, "visual": "CTA", "action": "Promise more"}
            ],
            "cta_options": ["More industry secrets coming", "Follow an insider", "What else do you want to know?"],
            "best_niches": ["B2B", "Professional Services", "Any industry expertise"],
            "estimated_engagement": "High (Authority Building)"
        },
        
        {
            "category": "Viral",
            "title": "The Controversial Hot Take Framework",
            "description": "Generate massive engagement by taking a bold stance on divisive topics.",
            "featured": False,
            "preview_hook": "This is going to get me cancelled but someone needs to say it...",
            "full_script": {
                "hook": {"text": "I know this is controversial but [BOLD STATEMENT].", "duration": "0-3s"},
                "stance": {"text": "Here's the thing: [ELABORATE ON YOUR POSITION].", "duration": "3-12s"},
                "evidence": {"text": "And before you comment, consider this: [SUPPORTING POINT].", "duration": "12-20s"},
                "challenge": {"text": "Prove me wrong. I'll wait.", "duration": "20-25s"},
                "cta": {"text": "Agree or disagree? Comment your take. Follow for real opinions.", "duration": "25-30s"}
            },
            "scene_breakdown": [
                {"scene": 1, "visual": "Bold opening", "action": "Create tension"},
                {"scene": 2, "visual": "State your case", "action": "Own your opinion"},
                {"scene": 3, "visual": "Back it up", "action": "Show logic"},
                {"scene": 4, "visual": "Challenge viewers", "action": "Invite debate"},
                {"scene": 5, "visual": "CTA", "action": "Drive comments"}
            ],
            "cta_options": ["Fight me in the comments", "Prove me wrong", "Hot take or facts?"],
            "best_niches": ["Any", "Works best with actual expertise"],
            "estimated_engagement": "Extremely High (Viral Potential)"
        }
    ]
    
    for framework in additional_frameworks:
        framework["id"] = str(uuid.uuid4())
        framework["created_at"] = datetime.now(timezone.utc).isoformat()
    
    existing_fw_count = await db.blueprint_frameworks.count_documents({})
    if existing_fw_count < 20:
        await db.blueprint_frameworks.insert_many(additional_frameworks)
        print(f"Added {len(additional_frameworks)} new frameworks")
    
    # =========================================================================
    # ADDITIONAL STORY IDEAS (15+ more)
    # =========================================================================
    additional_story_ideas = [
        # More Adventure
        {
            "genre": "Adventure",
            "age_group": "5-7",
            "title": "The Pirate Pup's Treasure Map",
            "brief_synopsis": "A puppy finds an old treasure map in his backyard and sets sail with his animal friends.",
            "featured": True,
            "full_synopsis": "Captain Biscuit the puppy discovers a mysterious map buried under his favorite digging spot. With the help of his crew - Polly the parrot who can't stop talking, Sheldon the seasick turtle, and Whiskers the cat who's actually scared of water - they build a boat from the garden shed and set sail across Puddle Lake to find the legendary Golden Bone.",
            "characters": [
                {"name": "Captain Biscuit", "type": "Protagonist", "description": "A brave golden retriever puppy with a pirate hat"},
                {"name": "Polly", "type": "Sidekick", "description": "A colorful parrot who narrates everything"},
                {"name": "Sheldon", "type": "Comic Relief", "description": "A turtle who gets seasick on land"},
                {"name": "Whiskers", "type": "Sidekick", "description": "A cat pretending to be brave"}
            ],
            "moral": "The real treasure is the friends we make along the way",
            "scene_outlines": [
                {"scene": 1, "title": "The Discovery", "description": "Biscuit finds the map while digging"},
                {"scene": 2, "title": "Gathering the Crew", "description": "He recruits his unlikely friends"},
                {"scene": 3, "title": "Building the Ship", "description": "They turn a shed into a boat"},
                {"scene": 4, "title": "Setting Sail", "description": "The adventure begins with mishaps"},
                {"scene": 5, "title": "The Storm", "description": "A sprinkler creates chaos"},
                {"scene": 6, "title": "Land Ho!", "description": "They reach the island (sandbox)"},
                {"scene": 7, "title": "The Treasure", "description": "What they find isn't gold"},
                {"scene": 8, "title": "The Real Prize", "description": "They realize friendship is the treasure"}
            ]
        },
        
        # Humor
        {
            "genre": "Humor",
            "age_group": "4-6",
            "title": "The Day My Teddy Bear Came to School",
            "brief_synopsis": "A child's teddy bear magically comes to life and causes hilarious chaos at school.",
            "featured": True,
            "full_synopsis": "When Emma wishes her teddy bear Mr. Snuggles could come to school, she doesn't expect it to actually happen! Mr. Snuggles comes to life and tries to be helpful, but a bear doesn't know how to act in class. He finger paints with his whole body, falls asleep during storytime (and snores loudly), and tries to eat the class goldfish. Can Emma teach Mr. Snuggles how to be a good student before the teacher notices?",
            "characters": [
                {"name": "Emma", "type": "Protagonist", "description": "A 5-year-old girl with big imagination"},
                {"name": "Mr. Snuggles", "type": "Main Character", "description": "A teddy bear who doesn't understand rules"},
                {"name": "Mrs. Apple", "type": "Supporting", "description": "The patient kindergarten teacher"},
                {"name": "Classmates", "type": "Supporting", "description": "Kids who think a walking bear is cool"}
            ],
            "moral": "Everyone needs patience when learning something new",
            "scene_outlines": [
                {"scene": 1, "title": "The Wish", "description": "Emma wishes Mr. Snuggles was real"},
                {"scene": 2, "title": "Morning Surprise", "description": "He comes to life!"},
                {"scene": 3, "title": "Bus Ride Chaos", "description": "Bears don't fit in bus seats"},
                {"scene": 4, "title": "Art Disaster", "description": "Finger painting gone wrong"},
                {"scene": 5, "title": "Snack Time", "description": "Mr. Snuggles eats ALL the snacks"},
                {"scene": 6, "title": "Naptime", "description": "The loudest snoring ever"},
                {"scene": 7, "title": "Learning to Behave", "description": "Emma teaches him the rules"},
                {"scene": 8, "title": "Best Day Ever", "description": "He becomes the class hero"}
            ]
        },
        
        # Science/Nature
        {
            "genre": "Educational",
            "age_group": "5-7",
            "title": "The Incredible Shrinking Sarah",
            "brief_synopsis": "A girl shrinks to the size of an ant and discovers the amazing world of insects.",
            "featured": False,
            "full_synopsis": "When Sarah spills her mom's mysterious gardening formula, she shrinks to bug size! Now she must journey through her own backyard to find the antidote. Along the way, she meets Andy the helpful ant, learns how butterflies drink nectar, watches spiders build webs, and realizes that 'creepy crawlies' aren't so creepy after all.",
            "characters": [
                {"name": "Sarah", "type": "Protagonist", "description": "A curious girl who was scared of bugs"},
                {"name": "Andy", "type": "Guide", "description": "A hardworking ant who offers to help"},
                {"name": "Bella", "type": "Supporting", "description": "A beautiful butterfly who gives advice"},
                {"name": "Webster", "type": "Supporting", "description": "A spider who is actually friendly"}
            ],
            "moral": "Don't judge something before you understand it",
            "scene_outlines": [
                {"scene": 1, "title": "The Accident", "description": "Sarah spills the formula"},
                {"scene": 2, "title": "A Tiny World", "description": "Everything is suddenly huge"},
                {"scene": 3, "title": "Meeting Andy", "description": "An ant becomes her guide"},
                {"scene": 4, "title": "Ant Colony", "description": "Learning about teamwork"},
                {"scene": 5, "title": "Butterfly Garden", "description": "Seeing beauty up close"},
                {"scene": 6, "title": "Spider's Web", "description": "Not so scary after all"},
                {"scene": 7, "title": "The Antidote", "description": "Finding the way to grow back"},
                {"scene": 8, "title": "New Respect", "description": "Sarah now loves the garden"}
            ]
        },
        
        # Emotions
        {
            "genre": "Emotional Growth",
            "age_group": "4-6",
            "title": "The Monster in My Closet Needs a Friend",
            "brief_synopsis": "A child discovers their closet monster is actually lonely and just wants to play.",
            "featured": True,
            "full_synopsis": "Every night, Leo hears strange sounds from his closet. When he finally gets brave enough to look, he finds Grum - a fuzzy purple monster who isn't scary at all. Grum explains that monsters make noise because they're lonely and bored. Together, Leo and Grum have the best sleepover ever, and Leo learns that things that seem scary are often just misunderstood.",
            "characters": [
                {"name": "Leo", "type": "Protagonist", "description": "A brave little boy who faces his fears"},
                {"name": "Grum", "type": "Main Character", "description": "A purple monster who just wants a friend"},
                {"name": "Mom and Dad", "type": "Supporting", "description": "Parents who can't see Grum"},
                {"name": "Flashlight Fred", "type": "Comic Relief", "description": "A talking flashlight"}
            ],
            "moral": "Facing your fears reveals they're not so scary",
            "scene_outlines": [
                {"scene": 1, "title": "Scary Sounds", "description": "Leo hears the closet monster"},
                {"scene": 2, "title": "Building Courage", "description": "Leo decides to investigate"},
                {"scene": 3, "title": "Meeting Grum", "description": "The monster isn't scary!"},
                {"scene": 4, "title": "Grum's Story", "description": "Why monsters make noise"},
                {"scene": 5, "title": "Sleepover!", "description": "They play games all night"},
                {"scene": 6, "title": "Almost Caught", "description": "Mom almost finds Grum"},
                {"scene": 7, "title": "Best Friends", "description": "They become friends forever"},
                {"scene": 8, "title": "No More Fear", "description": "Leo helps other scared kids"}
            ]
        },
        
        # Space
        {
            "genre": "Science Fiction",
            "age_group": "5-7",
            "title": "Luna's Rocket Ship Bedroom",
            "brief_synopsis": "A girl's bedroom transforms into a real rocket ship that takes her to visit friendly aliens.",
            "featured": False,
            "full_synopsis": "Luna loves space so much that she decorated her whole room like a rocket ship. One night, she presses the 'launch' button on her cardboard control panel and... it actually works! Her bedroom blasts off to space where she meets Zip and Zap, alien twins who've never seen an Earth kid before. She shows them her favorite Earth things while they teach her about their planet made entirely of bouncy material.",
            "characters": [
                {"name": "Luna", "type": "Protagonist", "description": "A space-obsessed girl with big dreams"},
                {"name": "Zip", "type": "Friend", "description": "A blue alien who loves to learn"},
                {"name": "Zap", "type": "Friend", "description": "Zip's twin who loves to bounce"},
                {"name": "Captain Teddy", "type": "Sidekick", "description": "Luna's teddy bear co-pilot"}
            ],
            "moral": "Imagination can take you anywhere",
            "scene_outlines": [
                {"scene": 1, "title": "Blast Off!", "description": "Luna's room becomes a real rocket"},
                {"scene": 2, "title": "Space Travel", "description": "Flying through the stars"},
                {"scene": 3, "title": "Alien Planet", "description": "Landing on Bouncy World"},
                {"scene": 4, "title": "New Friends", "description": "Meeting Zip and Zap"},
                {"scene": 5, "title": "Earth Show-and-Tell", "description": "Luna shares her favorite things"},
                {"scene": 6, "title": "Alien Adventures", "description": "Bouncing everywhere!"},
                {"scene": 7, "title": "Time to Go", "description": "Luna must return home"},
                {"scene": 8, "title": "Sweet Dreams", "description": "Back home with new memories"}
            ]
        },
        
        # Sibling
        {
            "genre": "Family",
            "age_group": "3-5",
            "title": "My Little Brother is a Superhero",
            "brief_synopsis": "A big sister discovers her annoying little brother has surprising superpowers.",
            "featured": True,
            "full_synopsis": "Maya thinks her little brother Max is the most annoying person in the world. He breaks her toys, messes up her room, and follows her everywhere. But when Maya's favorite stuffed animal falls down a storm drain, Max reveals his secret superpowers - he can talk to animals! With help from a friendly rat and some brave birds, they save Mr. Bunny together, and Maya realizes her brother is pretty cool after all.",
            "characters": [
                {"name": "Maya", "type": "Protagonist", "description": "A 6-year-old who finds her brother annoying"},
                {"name": "Max", "type": "Main Character", "description": "A 4-year-old with a secret power"},
                {"name": "Mr. Bunny", "type": "Object", "description": "Maya's beloved stuffed bunny"},
                {"name": "Ratty", "type": "Supporting", "description": "A helpful sewer rat"}
            ],
            "moral": "Our siblings have special gifts we might not see",
            "scene_outlines": [
                {"scene": 1, "title": "So Annoying!", "description": "Max bothers Maya all day"},
                {"scene": 2, "title": "The Disaster", "description": "Mr. Bunny falls down a drain"},
                {"scene": 3, "title": "Maya's Tears", "description": "She's heartbroken"},
                {"scene": 4, "title": "Max's Secret", "description": "He reveals he can talk to animals"},
                {"scene": 5, "title": "The Rescue Team", "description": "Animals come to help"},
                {"scene": 6, "title": "Down the Drain", "description": "The brave rescue mission"},
                {"scene": 7, "title": "Mr. Bunny Saved!", "description": "Success! Bunny is rescued"},
                {"scene": 8, "title": "Best Brother Ever", "description": "Maya sees Max differently"}
            ]
        },
        
        # Seasonal/Holiday
        {
            "genre": "Holiday",
            "age_group": "3-5",
            "title": "The Snowman Who Wanted to See Summer",
            "brief_synopsis": "A snowman wishes to see summer and his animal friends try to make his dream come true.",
            "featured": False,
            "full_synopsis": "Frosty the snowman has heard wonderful stories about summer - beaches, ice cream, flowers, and sunshine. He wishes he could see it, but everyone knows snowmen melt in summer. His friends - a fox, an owl, and a rabbit - decide to bring summer to Frosty! They create a special 'summer day' in winter, complete with paper flowers, pretend beaches, and 'sun' made of yellow leaves.",
            "characters": [
                {"name": "Frosty", "type": "Protagonist", "description": "A curious snowman who dreams of summer"},
                {"name": "Felix Fox", "type": "Friend", "description": "The idea maker of the group"},
                {"name": "Olivia Owl", "type": "Friend", "description": "Wise and helpful"},
                {"name": "Ruby Rabbit", "type": "Friend", "description": "Energetic and crafty"}
            ],
            "moral": "True friends find ways to make your dreams come true",
            "scene_outlines": [
                {"scene": 1, "title": "Frosty's Wish", "description": "He wants to see summer"},
                {"scene": 2, "title": "The Problem", "description": "Snowmen can't survive summer"},
                {"scene": 3, "title": "The Plan", "description": "Friends decide to help"},
                {"scene": 4, "title": "Making Summer", "description": "Creating decorations"},
                {"scene": 5, "title": "Paper Flowers", "description": "A garden in winter"},
                {"scene": 6, "title": "Beach Party", "description": "Sand replaced with snow"},
                {"scene": 7, "title": "Frosty's Summer Day", "description": "The surprise reveal"},
                {"scene": 8, "title": "Best Winter Ever", "description": "Frosty's dream came true"}
            ]
        },
        
        # Problem-Solving
        {
            "genre": "Problem-Solving",
            "age_group": "4-6",
            "title": "The Great Cookie Mystery",
            "brief_synopsis": "A young detective must solve the case of the missing cookies before dinner.",
            "featured": False,
            "full_synopsis": "Someone has eaten all of Mom's fresh-baked cookies! Detective Danny takes the case, following a trail of crumbs and clues through the house. Each family member and pet becomes a suspect. Using his detective skills (and his magnifying glass), Danny discovers surprising evidence that leads to an unexpected culprit - and an important lesson about honesty.",
            "characters": [
                {"name": "Detective Danny", "type": "Protagonist", "description": "A 5-year-old detective with a magnifying glass"},
                {"name": "Mom", "type": "Supporting", "description": "The cookie baker who discovered the crime"},
                {"name": "Dad", "type": "Suspect", "description": "Claims he didn't do it"},
                {"name": "Biscuit the Dog", "type": "Suspect", "description": "The usual suspect"},
                {"name": "Baby Sister", "type": "Suspect", "description": "Too small to reach... or is she?"}
            ],
            "moral": "It's always better to tell the truth",
            "scene_outlines": [
                {"scene": 1, "title": "The Crime Scene", "description": "Empty cookie plate discovered"},
                {"scene": 2, "title": "Taking the Case", "description": "Danny becomes a detective"},
                {"scene": 3, "title": "The Clues", "description": "Following crumb trails"},
                {"scene": 4, "title": "Dad's Alibi", "description": "Interviewing suspect #1"},
                {"scene": 5, "title": "Biscuit's Defense", "description": "The dog looks guilty but..."},
                {"scene": 6, "title": "Baby Sister", "description": "The plot thickens"},
                {"scene": 7, "title": "Case Solved!", "description": "The real culprit revealed"},
                {"scene": 8, "title": "The Lesson", "description": "Truth is always best"}
            ]
        }
    ]
    
    for idea in additional_story_ideas:
        idea["id"] = str(uuid.uuid4())
        idea["created_at"] = datetime.now(timezone.utc).isoformat()
    
    existing_idea_count = await db.blueprint_story_ideas.count_documents({})
    if existing_idea_count < 25:
        await db.blueprint_story_ideas.insert_many(additional_story_ideas)
        print(f"Added {len(additional_story_ideas)} new story ideas")
    
    return {
        "hooks_added": len(additional_hooks) if existing_count < 100 else 0,
        "frameworks_added": len(additional_frameworks) if existing_fw_count < 20 else 0,
        "story_ideas_added": len(additional_story_ideas) if existing_idea_count < 25 else 0
    }
