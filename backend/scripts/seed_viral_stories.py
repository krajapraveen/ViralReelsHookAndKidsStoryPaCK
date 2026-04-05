"""
VIRAL STORY SEEDER
Seeds 30 high-quality stories into the shares collection.
Each story ends with a clear continuation gap — incomplete, compelling, demanding.

Distribution: 10 mystery, 10 thriller, 5 emotional, 5 fantasy
"""
import asyncio
import uuid
from datetime import datetime, timezone, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
import os

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "creatorstudio_production")

STORIES = [
    # ═══════════════════════════════════════════════════════════════════
    # MYSTERY (10)
    # ═══════════════════════════════════════════════════════════════════
    {
        "title": "The Room That Wasn't There",
        "genre": "mystery",
        "tone": "suspenseful",
        "conflict": "A hidden room appears in a house that's been lived in for 20 years",
        "characters": ["Elena", "The house"],
        "hookText": "She'd lived in this house for 20 years. She knew every room. Until today.",
        "shareCaption": "She found a room that shouldn't exist. What's inside changes everything.",
        "storyContext": "Elena pressed her hand against the wallpaper in the upstairs hallway. The wall gave way. Behind it was a door — old brass handle, cold to the touch — leading to a room she had never seen. Inside: a chair facing the window, a glass of water still sweating with condensation, and a notebook open to today's date. In the notebook, in handwriting identical to her own, was a single sentence: 'You finally found it.' The chair was still warm.",
        "preview": "Elena pressed her hand against the wallpaper in the upstairs hallway. The wall gave way. Behind it was a door — old brass handle, cold to the touch — leading to a room she had never seen. Inside: a chair facing the window, a glass of water still sweating with condensation, and a notebook open to today's date. In the notebook, in handwriting identical to her own, was a single sentence: 'You finally found it.' The chair was still warm.",
    },
    {
        "title": "Three Missed Calls",
        "genre": "mystery",
        "tone": "eerie",
        "conflict": "A dead woman's phone keeps calling her daughter",
        "characters": ["Priya", "Her mother (deceased)"],
        "hookText": "Her mother died three months ago. Her phone still calls every night at 2:14 AM.",
        "shareCaption": "She keeps getting calls from her dead mother's phone. At exactly 2:14 AM.",
        "storyContext": "Priya let it ring the first seven times. On the eighth night, she answered. Static. Then breathing — not mechanical, not a recording. Breathing that matched her own rhythm. When she held her breath, the other end held its breath too. She whispered 'Mom?' and the line went dead. The next morning, she found a voicemail she hadn't noticed. It was 47 minutes long. The first 46 minutes were silence. In the last minute, a voice said: 'Check the garden. I buried it before I forgot.'",
        "preview": "Priya let it ring the first seven times. On the eighth night, she answered. Static. Then breathing — not mechanical, not a recording. Breathing that matched her own rhythm. When she held her breath, the other end held its breath too.",
    },
    {
        "title": "The Lighthouse Keeper's Log",
        "genre": "mystery",
        "tone": "unsettling",
        "conflict": "A lighthouse keeper's journal describes events that haven't happened yet",
        "characters": ["James", "The previous keeper"],
        "hookText": "The last entry in the lighthouse log was dated six months from now.",
        "shareCaption": "He found a logbook in the lighthouse. The last entry is dated six months in the future.",
        "storyContext": "James took the lighthouse position because he wanted silence. The previous keeper, Harlan, had left without notice. The logbook was meticulous — weather, ships, tide patterns — until the entries started describing things that hadn't happened yet. 'March 12: The woman in the red coat arrives. Do not let her in.' James read ahead. Every entry for the next six months was filled. The last one read: 'September 4: He finally understands why I left. It's too late.' Today was March 11th.",
        "preview": "James took the lighthouse position because he wanted silence. The previous keeper had left without notice. The logbook was meticulous until the entries started describing things that hadn't happened yet.",
    },
    {
        "title": "Platform 9",
        "genre": "mystery",
        "tone": "tense",
        "conflict": "A commuter notices the same stranger dying on the same platform every morning",
        "characters": ["Marcus", "The falling man"],
        "hookText": "Every morning at 8:07, the same man falls onto the tracks. Nobody else seems to notice.",
        "shareCaption": "He watches the same man die every morning at 8:07 AM. Nobody remembers.",
        "storyContext": "The first time, Marcus screamed. The second time, he called the police. The third time, he tried to grab the man's jacket. Each morning, the man in the grey coat steps off Platform 9 at exactly 8:07 AM. Each morning, the train arrives at 8:07 and twelve seconds. Each morning, nobody else reacts. The security footage shows an empty platform. On the fifth morning, the man turned to Marcus just before stepping off and said: 'Tomorrow it's your turn to show someone.' He fell. The train came. Marcus looked at his hands — they were wearing grey gloves he didn't own.",
        "preview": "The first time, Marcus screamed. The second time, he called the police. The third time, he tried to grab the man's jacket. Each morning, the man in the grey coat steps off Platform 9 at exactly 8:07 AM.",
    },
    {
        "title": "Apartment 4B",
        "genre": "mystery",
        "tone": "creepy",
        "conflict": "A tenant receives mail for a person who lived in her apartment 30 years ago",
        "characters": ["Sana", "The previous tenant"],
        "hookText": "The letters kept arriving for someone who lived here 30 years ago. Then the letters started mentioning her by name.",
        "shareCaption": "She gets mail for a previous tenant from 30 years ago. The latest letter has HER name in it.",
        "storyContext": "The first few letters were junk mail — coupons, catalogues. Then came handwritten envelopes addressed to 'Clara Voss, Apartment 4B.' Sana left them on the lobby table. But last Tuesday, a letter arrived addressed to 'Clara Voss (who now calls herself Sana).' Inside was a photograph. It showed this apartment, this exact furniture arrangement, but in 1994. Standing in the kitchen, smiling at the camera, was a woman who looked exactly like Sana. On the back of the photo: 'You moved the bookshelf. I wouldn't have done that.'",
        "preview": "The first few letters were junk mail. Then came handwritten envelopes addressed to 'Clara Voss, Apartment 4B.' Last Tuesday, a letter arrived addressed to 'Clara Voss (who now calls herself Sana).'",
    },
    {
        "title": "The Memory Auction",
        "genre": "mystery",
        "tone": "intriguing",
        "conflict": "A woman buys a stranger's memories at an underground auction and discovers they're her own",
        "characters": ["Dara", "The auctioneer"],
        "hookText": "She bought a stranger's memories at an underground auction. They were hers.",
        "shareCaption": "An underground auction sells memories. She bought one and recognized her own childhood.",
        "storyContext": "The auction house had no address — just GPS coordinates that changed weekly. Dara paid $400 for Lot 7: a small glass vial labeled 'Summer, age 8.' She inhaled the vapor and saw a memory — running through a wheat field, a dog barking, a red bicycle crashing into a fence. Her red bicycle. Her grandmother's farm. Her dog. She had never told anyone about that summer. She bought Lot 12: 'First heartbreak, age 19.' It was hers too. Every detail. She found the auctioneer backstage and demanded answers. He smiled and said: 'You sold these to us. You just don't remember agreeing to it.'",
        "preview": "The auction house had no address — just GPS coordinates that changed weekly. Dara paid $400 for Lot 7: a small glass vial labeled 'Summer, age 8.' She inhaled the vapor and saw her own childhood.",
    },
    {
        "title": "The Photographer's Last Roll",
        "genre": "mystery",
        "tone": "haunting",
        "conflict": "A photographer's undeveloped film shows photos of events that happened after his death",
        "characters": ["Noor", "Her late grandfather"],
        "hookText": "Her grandfather's camera had one roll of undeveloped film. The photos were dated after he died.",
        "shareCaption": "She developed her dead grandfather's last roll of film. The dates don't make sense.",
        "storyContext": "Noor found the Leica in her grandfather's attic, one roll still loaded. She had it developed at the only analog lab left in the city. The photos were ordinary at first — street scenes, a park bench, pigeons. Then she noticed the newspaper in frame four. The headline described an earthquake that happened two weeks after his funeral. Frame twelve showed Noor herself, sitting in this exact darkroom, holding these exact photos. In the background of the image, just over her shoulder, someone was standing. Someone she couldn't see in the room right now. She looked behind her. Nothing. She looked at the photo again. The figure had moved closer.",
        "preview": "Noor found the Leica in her grandfather's attic, one roll still loaded. The photos were ordinary at first. Then she noticed the newspaper — the headline described an earthquake two weeks after his funeral.",
    },
    {
        "title": "Exit Interview",
        "genre": "mystery",
        "tone": "paranoid",
        "conflict": "An employee discovers his company has been recording his thoughts",
        "characters": ["Kai", "The interviewer"],
        "hookText": "During his exit interview, they played back things he had only thought — never said.",
        "shareCaption": "His exit interview played back things he THOUGHT. Not said. Thought.",
        "storyContext": "Kai was leaving after four years. Standard exit interview. The HR rep, someone he'd never met, slid a tablet across the table and pressed play. Audio. His voice: 'I think the Q3 numbers are fake.' He had never said that out loud. Then: 'I wonder if Sara knows about the merger.' He had thought that in the elevator, alone. The rep paused the recording. 'We collect ambient cognitive data through the building's environmental systems. It's in your contract — Section 14, Clause 7b. We just need you to confirm these are accurate before we archive them.' Kai looked at the door. The lock light was red.",
        "preview": "Standard exit interview. The HR rep slid a tablet across the table and pressed play. His voice: 'I think the Q3 numbers are fake.' He had never said that out loud.",
    },
    {
        "title": "Sender Unknown",
        "genre": "mystery",
        "tone": "anxious",
        "conflict": "A woman receives her own diary entries — mailed from locations she's never been",
        "characters": ["Mira"],
        "hookText": "Someone is mailing her own diary entries back to her — from cities she's never visited.",
        "shareCaption": "She keeps her diary locked. Someone in another country is mailing her entries back to her.",
        "storyContext": "The first envelope came from Reykjavik. Inside, a photocopy of page 43 of Mira's diary — the one she kept in her nightstand, locked, key around her neck. Word for word. Her handwriting. She checked: the original page was still there. The second envelope came from Buenos Aires. Page 117: the entry about her father's diagnosis, the one she wrote while crying so hard the ink smeared. The photocopy had the same smeared ink. The third envelope came from Kyoto. Page 1. The very first entry she had ever written, age 13. Attached was a sticky note in someone else's handwriting: 'We're almost at the last page. Then we need to talk about what you wrote on the inside back cover.' Mira had never written on the inside back cover. She opened her diary. There was writing there now. Fresh ink.",
        "preview": "The first envelope came from Reykjavik. Inside, a photocopy of page 43 of Mira's diary — the one she kept locked. Word for word. Her handwriting.",
    },
    {
        "title": "The Understudy",
        "genre": "mystery",
        "tone": "disorienting",
        "conflict": "An actor discovers someone else has been living his life on the days he can't remember",
        "characters": ["Leo", "The other Leo"],
        "hookText": "He loses Tuesdays. Every Tuesday is blank. Someone else is living them for him.",
        "shareCaption": "He can't remember any Tuesday for the past year. Someone else has been showing up to his life.",
        "storyContext": "Leo doesn't remember Tuesdays. Not since last January. He goes to sleep Monday night, wakes up Wednesday morning. His coworkers say he's at work on Tuesdays — productive, even cheerful. His girlfriend says they had dinner last Tuesday and he was 'more like the old Leo.' His bank shows Tuesday transactions: a coffee shop he's never been to, a bookstore in a neighborhood he doesn't visit. He set up a camera in his apartment. On Tuesday, a man walked in at 7 AM, showered, dressed in Leo's clothes, drank Leo's coffee, and left. The man looked exactly like Leo. Moved exactly like Leo. But when he smiled at the camera — and he did smile, directly into the lens — the smile reached places Leo's never did. Attached to the fridge with a magnet was a note: 'You should thank me. You were wasting them.'",
        "preview": "Leo doesn't remember Tuesdays. His coworkers say he's at work — productive, even cheerful. He set up a camera. On Tuesday, a man walked in, showered, dressed in Leo's clothes. The man looked exactly like Leo.",
    },

    # ═══════════════════════════════════════════════════════════════════
    # THRILLER (10)
    # ═══════════════════════════════════════════════════════════════════
    {
        "title": "The 7-Minute Rule",
        "genre": "thriller",
        "tone": "urgent",
        "conflict": "A negotiator has 7 minutes before a building is destroyed — but the bomber wants to talk",
        "characters": ["Agent Torres", "The bomber"],
        "hookText": "The bomber doesn't want money. He wants someone to listen. You have 7 minutes.",
        "shareCaption": "7 minutes. No demands. No ransom. He just wants someone to hear his story before it ends.",
        "storyContext": "Agent Torres picked up the phone on the third ring. 'You have seven minutes,' the voice said. 'I don't want money. I don't want a helicopter. I want you to listen to what happened at Ridgemont Elementary in 1998.' Torres signaled her team: trace it. 'I'm listening,' she said. 'No you're not. You're tracing this call. I'll know when you find me because the signal will spike. When that happens, I detonate early.' She waved the trace off. Six minutes and fourteen seconds. 'In 1998,' the voice said, 'a teacher at Ridgemont noticed something about four of her students.' Torres felt ice in her stomach. She had gone to Ridgemont Elementary. She was one of four students pulled out of class in 1998. She had never known why. Five minutes and forty-one seconds.",
        "preview": "'You have seven minutes,' the voice said. 'I don't want money. I want you to listen to what happened at Ridgemont Elementary in 1998.' Torres felt ice in her stomach. She had gone to that school.",
    },
    {
        "title": "Black Box",
        "genre": "thriller",
        "tone": "claustrophobic",
        "conflict": "A pilot's black box recording reveals she survived the crash — and something found her",
        "characters": ["Captain Adisa", "The rescue team"],
        "hookText": "The black box was recovered. The pilot survived the crash. What came next is on the recording.",
        "shareCaption": "They found the black box. The pilot survived the crash. The next 19 hours of audio will haunt you.",
        "storyContext": "Flight 2781 went down in the Andes. No survivors found. The black box was recovered 14 months later, buried under six feet of snow. The cockpit audio confirmed Captain Adisa survived the impact. She was lucid, narrating for the recorder: 'Both engines gone. Fuselage intact. Passengers — I can't check. My legs are pinned.' Hour four: 'I hear something outside. Footsteps. Not animal. Rhythmic. Like someone pacing.' Hour nine: 'The footsteps stopped. Something is breathing against the cockpit door.' Hour fourteen: 'It spoke. I don't know the language but I understood it. It said: We've been waiting for this one.' Hour nineteen, the last entry: 'I'm going to open the door. If anyone finds this — the passengers are not dead. They're standing outside. All of them. In a line. Facing away from the plane. I have to'— The recording ends.",
        "preview": "Flight 2781 went down in the Andes. The black box was recovered 14 months later. The pilot survived. Hour nine: 'Something is breathing against the cockpit door.'",
    },
    {
        "title": "The Blind Spot",
        "genre": "thriller",
        "tone": "paranoid",
        "conflict": "Every security camera in a city has the same blind spot — and someone is using it",
        "characters": ["Detective Soo-jin", "The ghost"],
        "hookText": "Every camera in the city has the same blind spot. 3 feet wide. Someone is using it to move unseen.",
        "shareCaption": "3,847 cameras. Every single one has the same 3-foot blind spot. Someone is exploiting it.",
        "storyContext": "Detective Soo-jin noticed it during the Yoon disappearance. The suspect walked from Gangnam to Hongdae — 11 kilometers — without appearing on a single camera. Not hacked. Not covered. The cameras recorded everything except a 3-foot corridor that existed in every single frame. She mapped it. The blind spot was continuous. You could walk from one end of Seoul to the other through it. Building to building, street to street — a perfect invisible path through the entire city. When she reported it to her captain, he went pale. 'That report was filed before,' he said. 'In 2019. The detective who filed it was Park Jun-ho.' Park Jun-ho had been missing since 2019. Soo-jin pulled his last known location. He had been standing at the edge of the blind spot. One foot in. One foot out. The camera caught half his body. The other half was gone.",
        "preview": "The suspect walked 11 kilometers without appearing on a single camera. Not hacked. The cameras had a blind spot — 3 feet wide — continuous through the entire city. Someone is using it.",
    },
    {
        "title": "The Last Surgeon",
        "genre": "thriller",
        "tone": "intense",
        "conflict": "A surgeon must operate on himself to remove a device implanted without his knowledge",
        "characters": ["Dr. Karim"],
        "hookText": "The X-ray showed something in his chest. He didn't put it there. It's transmitting.",
        "shareCaption": "He found a device in his chest he didn't know was there. It's been transmitting for 8 years.",
        "storyContext": "The X-ray was routine — pre-op clearance for a knee surgery. Dr. Karim almost didn't look at it. But there it was: a metallic object, 2 centimeters, lodged between his fourth and fifth ribs. Not a surgical artifact. Not a fragment. A device. Perfectly placed, deliberately implanted. His partner examined it with an RF scanner. It was transmitting. Low frequency, encrypted, continuous. It had been transmitting for approximately eight years — which meant it was implanted during his only surgery: an appendectomy in 2018. At a hospital where he also worked. By colleagues he trusted. He locked his office, sterilized a scalpel, and positioned two mirrors. He couldn't go to anyone else. The device had a secondary function listed nowhere in medical literature. It was monitoring his location. And the signal strength just changed — meaning whoever was listening now knew he had found it.",
        "preview": "The X-ray showed a metallic object between his ribs. A device. Transmitting for 8 years. Implanted during his appendectomy — by colleagues he trusted.",
    },
    {
        "title": "Switchback",
        "genre": "thriller",
        "tone": "frantic",
        "conflict": "A woman on a mountain road realizes the car behind her is driving her car",
        "characters": ["Anya"],
        "hookText": "She checked her mirror. The car behind her was the same make, model, color, and plate number. It was her car.",
        "shareCaption": "The car behind her on the mountain road has the same plate number. Same scratches. It's HER car.",
        "storyContext": "Anya was 40 minutes into the switchback when she noticed the headlights. Same distance behind her for the last six turns. She accelerated. They accelerated. She slowed. They slowed. At the next straightaway, she got a clear look in her mirror: silver Volvo XC40. Same dent on the bumper from the parking garage. Same cracked tail light she'd been meaning to fix. Same license plate: KR-7741-B. She pulled over. The car behind her pulled over at the exact same distance. She got out. The driver's door of the other car opened. Nobody got out. But the seat adjusted — she saw it move through the windshield — exactly the way her seat adjusts when she sits down. Her phone buzzed. A text from her own number: 'Get back in. It's not safe to be between us.'",
        "preview": "Same silver Volvo. Same dent. Same cracked tail light. Same license plate. The car behind her on the mountain road was her car. Then her phone buzzed — a text from her own number.",
    },
    {
        "title": "The Feedback Loop",
        "genre": "thriller",
        "tone": "disturbing",
        "conflict": "A therapist's patient describes a murder that matches a case the therapist committed",
        "characters": ["Dr. Lamont", "Patient X"],
        "hookText": "His patient described a murder in perfect detail. It was the murder he committed 12 years ago.",
        "shareCaption": "A therapist's new patient describes a murder in exact detail. The murder the therapist committed.",
        "storyContext": "Patient X was referred for recurring nightmares. 'I keep dreaming about killing someone,' she said. 'In a house by a lake. I use a kitchen knife — the kind with the wooden handle. I wrap the body in the blue shower curtain.' Dr. Lamont's pen stopped moving. Blue shower curtain. Wooden-handled knife. Lake house. She continued: 'There's a loose floorboard under the sink. That's where I hide the knife after.' He had never told anyone about the floorboard. 'I dream about the drive home too. Highway 9. The left headlight was out. I kept thinking someone would pull me over.' His left headlight had been out that night. Patient X looked directly at him. 'The dreams feel like memories, Doctor. But they can't be mine. I was eleven years old twelve years ago.' She paused. 'You went very pale just now. Should we stop?'",
        "preview": "'I keep dreaming about killing someone in a house by a lake. I use a kitchen knife with a wooden handle.' Dr. Lamont's pen stopped moving. She was describing the murder he committed.",
    },
    {
        "title": "Floor 37",
        "genre": "thriller",
        "tone": "dread",
        "conflict": "An elevator in a 35-story building starts going to Floor 37",
        "characters": ["Reese", "The building"],
        "hookText": "The building has 35 floors. Last night, the elevator went to 37.",
        "shareCaption": "A 35-story building. Last night the elevator displayed Floor 37. The doors opened.",
        "storyContext": "Reese was the night security guard. He'd watched the elevator display a hundred thousand times. Lobby, 2, 3, all the way to 35. Penthouse. That's where it stopped. Until 3:47 AM last Thursday, when the display read 36. Then 37. Then the doors opened on 37 and the interior camera showed... a hallway. Carpeted, lit, identical to every other floor. Except no floor 36 or 37 existed in the blueprints, the permits, or the building's structural plans. Reese radioed the other guard. No answer. He watched on the monitor as a figure walked out of an apartment on Floor 37, entered the elevator, and pressed L. The elevator descended: 37, 36, 35, 34... The doors opened in the lobby. Nobody stepped out. But the lobby camera showed wet footprints — bare feet — leading from the elevator to the front desk. To Reese's chair. Where he was sitting. The footprints stopped one foot behind him.",
        "preview": "The building has 35 floors. The elevator displayed Floor 37. The camera showed a hallway that doesn't exist in any blueprint. Someone walked out.",
    },
    {
        "title": "The Confession Hotline",
        "genre": "thriller",
        "tone": "menacing",
        "conflict": "An anonymous confession hotline operator hears her own murder being planned",
        "characters": ["Vera"],
        "hookText": "She runs an anonymous confession hotline. Last night, a caller confessed to planning her murder.",
        "shareCaption": "Anonymous confession hotline. The latest caller described how he's going to kill the operator. Her.",
        "storyContext": "Vera had heard everything on the hotline — affairs, thefts, lies. Anonymity brought out the truth. Caller 4,771 was calm. Male. Educated. 'I've been watching someone for six months. She lives alone. Third floor, corner apartment. She leaves for work at 7:15. She takes the same route every day. She has a cat named Miso.' Vera's blood froze. Her cat was named Miso. 'She runs a phone line where people tell her their secrets. She thinks she's safe because the calls are anonymous. But the calls route through a VoIP server in Estonia. I've had access to that server for four months. I know every caller. I know her address. I know she's listening right now.' The line went silent. Then: 'Don't hang up, Vera. If you hang up, the timer starts.' She looked at her phone. The call duration read 00:00. It hadn't been recording.",
        "preview": "'She lives alone. Third floor. She has a cat named Miso.' Vera's blood froze. Her cat was named Miso. 'She thinks she's safe because the calls are anonymous.'",
    },
    {
        "title": "Clean Slate",
        "genre": "thriller",
        "tone": "cold",
        "conflict": "A man wakes up in a hotel room with instructions to kill someone — written in his own handwriting",
        "characters": ["Owen"],
        "hookText": "He woke up in a hotel room with no memory of checking in. There was a note on the table. His handwriting. A name. An address. A time.",
        "shareCaption": "He woke in a hotel room he didn't book. The note on the table — in his handwriting — gave him a name, address, and deadline.",
        "storyContext": "Hotel Marais. Room 614. Owen woke fully dressed, shoes on, watch set to an alarm at 2:00 PM. On the desk: a note in his handwriting. 'Her name is Dana Wolfe. She will be at 1420 Rue Clement at 3:15 PM. You have done this before. You are very good at it. The envelope in the safe contains everything you need. The code is your mother's birthday.' He opened the safe. Inside: a passport in a different name with his photo, $20,000 in cash, a phone with one number saved as 'Handler,' and a small black case containing a disassembled precision instrument he recognized instinctively — his hands knew how to assemble it before his mind did. The phone buzzed. A text: 'Good morning. Please confirm you have read the brief.' He hadn't chosen any of this. But his hands were already assembling the case.",
        "preview": "Hotel room he didn't book. A note in his own handwriting: a name, an address, a time. In the safe — a passport with his face and a different name. His hands knew what to do before his mind did.",
    },
    {
        "title": "The Relay",
        "genre": "thriller",
        "tone": "breathless",
        "conflict": "A woman receives a package from her future self with a 90-minute deadline",
        "characters": ["Kit"],
        "hookText": "A courier delivered a package from herself. Inside: a USB drive, a map, and a note that said 'You have 90 minutes.'",
        "shareCaption": "She received a package from herself. Sent yesterday from an address she doesn't know. Inside: 90 minutes to live.",
        "storyContext": "The courier confirmed the sender: Kit Nakamura, 84 Riverside Drive. That was Kit's address. The package was logged as sent yesterday at 6:00 PM — while Kit had been at home, alone, and had sent nothing. Inside: a USB drive labeled 'WATCH FIRST,' a hand-drawn map of downtown, and a note in her handwriting: 'You have 90 minutes from the moment you press play. Follow the map. Do not call anyone. Do not go home. If you're reading this, I already failed once. This is your second attempt.' She plugged in the USB drive. The video showed her — same clothes, same hair, slightly more afraid — sitting in what looked like a shipping container. On-screen Kit said: 'The people who did this to me are going to do it to you in exactly 89 minutes. The map shows you where to go. At the red X, there's a locker. Inside the locker is the only thing that can stop them. The code is—' The video cut to static. The map had a red X.",
        "preview": "The courier confirmed the sender: Kit Nakamura. Her own address. Sent yesterday while she was home. Inside: a USB, a map, and 'You have 90 minutes. I already failed once.'",
    },

    # ═══════════════════════════════════════════════════════════════════
    # EMOTIONAL (5)
    # ═══════════════════════════════════════════════════════════════════
    {
        "title": "The Last Voicemail",
        "genre": "emotional",
        "tone": "bittersweet",
        "conflict": "A son discovers his late father left him a voicemail he never listened to",
        "characters": ["Arun", "His father"],
        "hookText": "His father died two years ago. Yesterday, he found a voicemail he never played.",
        "shareCaption": "Two years after his father's death, he found an unplayed voicemail. He pressed play.",
        "storyContext": "Arun was clearing old phones from a drawer when he found his previous one — cracked screen, dead battery. He charged it out of curiosity. When it powered on, there was one unplayed voicemail. From his father. Dated the day before he died. Arun had been in a meeting. He'd seen the call, declined it, and texted 'Call you later.' He never called back. He pressed play. His father's voice, steady but quieter than usual: 'Arun. I know you're busy. I just wanted to say — your mother and I had lunch at that restaurant you took us to. The one with the garden. She wore the yellow dress. I ordered the fish you recommended. It was perfect. I don't tell you this enough, but the life you built — I look at it and I think: he figured it out. He really figured it out. Anyway. Call me when you—' The voicemail cut off at the time limit. The last word was 'when.'",
        "preview": "He found an unplayed voicemail from his father, dated the day before he died. He'd declined the call and texted 'Call you later.' He never did. He pressed play.",
    },
    {
        "title": "The Bench at Gate 14",
        "genre": "emotional",
        "tone": "tender",
        "conflict": "Two strangers share a life-changing conversation during a 4-hour flight delay",
        "characters": ["Grace", "Tomás"],
        "hookText": "They sat next to each other for four hours at Gate 14. They never exchanged names. She thinks about him every day.",
        "shareCaption": "A 4-hour delay. A bench at Gate 14. A conversation that changed everything. They never exchanged names.",
        "storyContext": "Grace sat down because it was the only seat with an outlet. He was already there, reading a book she recognized — her mother's favorite. She said so. He smiled. Over the next four hours, they talked about everything and nothing. He told her he was flying home to forgive his brother. She told him she was flying away to stop forgiving hers. He said: 'Forgiveness isn't about them. It's about putting the weight down.' She told him about the letter she'd been carrying in her bag for three years — the one she'd written to her mother but never sent. He said: 'What if you sent it to yourself instead? What if you're the one who needs to read it?' Gate 14 boarded. They stood up. He walked to the right. She walked to the left. She never asked his name. On the plane, she opened the letter. It began: 'Dear Mom, I'm sorry I became the person you were afraid I'd become.' She crossed out 'Mom' and wrote her own name. Then she kept reading.",
        "preview": "They sat next to each other for four hours at Gate 14. He was flying home to forgive his brother. She was flying away to stop forgiving hers. They never exchanged names.",
    },
    {
        "title": "Room 402",
        "genre": "emotional",
        "tone": "heartbreaking",
        "conflict": "A nurse reads to a comatose patient for 8 months — and discovers who she was",
        "characters": ["Nina", "The woman in Room 402"],
        "hookText": "She read to the woman in Room 402 every night for 8 months. She never expected her to answer.",
        "shareCaption": "8 months of reading to a comatose patient. When she finally woke up, Nina wasn't ready for what she said.",
        "storyContext": "Nina started reading to the woman in Room 402 because nobody visited her. No flowers. No cards. Chart said: 'Jane Doe. Estimated age 70. Found at bus station, unresponsive.' Nina read her the newspaper at first, then novels, then poetry. After three months, she started talking to her instead — about her day, her breakup, her fear that she was wasting her twenties. After six months, Nina held her hand during the night shift and whispered: 'I don't know who you are, but you're the person I talk to most in this world.' On a Tuesday in March, the woman's eyes opened. She looked at Nina and said, very clearly: 'I know. I heard everything. Your boyfriend isn't coming back and you need to stop waiting. And Nina — the poetry was lovely, but you read Neruda wrong. The emphasis is on the second line.' She smiled. Her hand was warm. 'My name is Celeste. And you have been the best part of my very long sleep.'",
        "preview": "Nobody visited the woman in Room 402. No flowers. No cards. Nina read to her every night for 8 months. On a Tuesday in March, her eyes opened.",
    },
    {
        "title": "The Playlist",
        "genre": "emotional",
        "tone": "nostalgic",
        "conflict": "A woman finds a Spotify playlist her late best friend made for her — updated after death",
        "characters": ["Jess", "Sam (deceased)"],
        "hookText": "Her best friend died in April. The playlist was updated in July.",
        "shareCaption": "Sam died in April. But the playlist she made for Jess? New songs were added in July.",
        "storyContext": "Sam made Jess a playlist for every birthday. 'Jess Turns 28' had 28 songs — one for every year. After Sam's accident, Jess couldn't listen to music at all. In July, she opened Spotify for the first time. The playlist had 29 songs. The 29th was added three months after Sam died. It was a song Jess had never heard: 'The Light Behind Your Eyes.' She checked the account. Last login: July 3rd, 2:41 AM. Sam's account. Sam's password hadn't been changed. Nobody else had access. Jess played the song. In the middle of it, there was a 4-second gap of silence. Then Sam's voice — recorded, embedded in the track file somehow — said: 'Jess. I know this is weird. I made this before. I set it to add automatically. I made playlists through your 40th birthday. Every year, you'll get one. I can't be there. But the music can. Happy birthday, Jess. You're going to be okay.' Jess was 28. That meant there were 12 more playlists waiting.",
        "preview": "Sam made Jess a playlist for every birthday. Sam died in April. In July, the playlist had a new song. Inside the audio, Sam's voice: 'I made playlists through your 40th birthday.'",
    },
    {
        "title": "17 Seconds",
        "genre": "emotional",
        "tone": "devastating",
        "conflict": "A father gets 17 seconds of video from his daughter's phone — her last moments",
        "characters": ["David", "Emma"],
        "hookText": "The police returned her phone. There was a 17-second video she recorded in her last moments.",
        "shareCaption": "17 seconds. That's all she recorded. But what she said in those 17 seconds changed everything.",
        "storyContext": "The police returned Emma's phone in a clear bag. Screen cracked. Case still on — the one with the sunflower. David charged it and found a 17-second video in the camera roll, recorded the day of the accident. She was in the passenger seat. The car was already spinning. In the video, you can see the dashboard rotating, glass beginning to fracture, someone screaming. But Emma wasn't screaming. She had the phone up, and she was looking into it, directly, calmly, and she said: 'Dad. I'm okay. I love you. Tell mom the letter is in my desk. Left drawer. I'm okay. I'm not scared.' The video ended. David watched it eleven times. On the twelfth, he noticed something he hadn't before. In the last frame, reflected in the car window behind Emma, there was someone sitting in the back seat. Someone who wasn't in the car. Someone who looked like they were reaching for Emma's hand.",
        "preview": "17 seconds. The car was already spinning. Glass fracturing. But Emma wasn't screaming. She looked into the camera and said: 'Dad. I'm okay. I'm not scared.'",
    },

    # ═══════════════════════════════════════════════════════════════════
    # FANTASY (5)
    # ═══════════════════════════════════════════════════════════════════
    {
        "title": "The Cartographer of Unwritten Places",
        "genre": "fantasy",
        "tone": "wondrous",
        "conflict": "A mapmaker discovers she can draw places into existence",
        "characters": ["Solenne", "The Empty Continent"],
        "hookText": "She drew a mountain on a blank map. The next morning, it existed.",
        "shareCaption": "A cartographer drew a mountain that didn't exist. The next morning, it appeared on satellite images.",
        "storyContext": "Solenne's specialty was filling in the blank spaces — the terra incognita of old maps. She worked in ink on vellum, drawing coastlines of places she invented to pass time. The mountain range she sketched on a Tuesday was pure imagination: seven peaks, a river through the valley, a forest of trees she named 'moonwoods.' On Wednesday, a seismology lab in Switzerland reported a geological event. A new mountain range had appeared in the South Pacific, in an area previously documented as open ocean. Seven peaks. A river through the valley. Satellite images showed trees that matched no known species. Solenne's ink pot was empty. Her map showed the range perfectly. She hadn't signed it. When she reached for a new pen to add a city, her hand trembled. Because the question wasn't could she create places — she'd apparently already done that. The question was: what happened to the people she'd drawn inside the buildings?",
        "preview": "She sketched a mountain range on a blank map. Pure imagination. The next morning, a seismology lab reported the exact formation had appeared in the South Pacific.",
    },
    {
        "title": "The Library of Endings",
        "genre": "fantasy",
        "tone": "melancholic",
        "conflict": "A library exists that contains only the last pages of every story ever told",
        "characters": ["Wren", "The Librarian"],
        "hookText": "The library has no beginnings. Only endings. Every story ever told — but only its last page.",
        "shareCaption": "A library that stores only the final page of every story ever written. She found hers.",
        "storyContext": "Wren found the library at the bottom of a staircase that shouldn't have existed — in the back of a bookshop in Prague, behind a shelf labeled 'Returns.' Inside: endless corridors of single pages, each framed, each labeled with a name. She walked past thousands. Some pages were tear-stained. Some were burned at the edges. Some were written in languages that no longer existed. The Librarian appeared beside her without sound. 'Every story has an ending,' he said. 'We keep them here so they are not lost when the stories are forgotten.' 'Can I find mine?' she asked. He led her to a corridor she hadn't noticed. Her name was on a frame. Inside was a single page — not yet written. The paper was blank except for one line at the bottom, in ink that was still wet: 'And she finally understood that the door had always been open.' Wren looked at the Librarian. 'But my story isn't over.' He smiled. 'That's why the ink is still wet. You're the only visitor who arrived before their ending was written. Which means you can change it. If you dare.'",
        "preview": "The library had no beginnings. Only endings. Every story ever told — just its last page. She found hers. The ink was still wet. 'You arrived before your ending was written.'",
    },
    {
        "title": "The Night Market",
        "genre": "fantasy",
        "tone": "enchanting",
        "conflict": "A night market appears once a year where you can trade years of your life for impossible things",
        "characters": ["Lior", "The merchant"],
        "hookText": "The Night Market appears once a year. The currency isn't money — it's years of your life.",
        "shareCaption": "A market that appears once a year. You can buy anything. The price? Years of your life.",
        "storyContext": "Lior found the Night Market in an alley that didn't exist at dawn. Stalls of silk and smoke, selling impossible things: bottled laughter, a compass that points to what you need most, a mirror that shows who truly loves you. The prices were written on wooden tags — not in coins but in time. 'A year of your life for the compass,' the merchant said. 'Two years for the mirror.' Lior asked: 'What's the most expensive thing here?' The merchant led him to a stall at the very end, draped in black velvet. On a pedestal sat a small hourglass, half full. The tag read: 'The rest of your life.' 'What does it do?' Lior asked. 'It does the only thing worth everything,' the merchant said. 'It lets you live the years you already spent — but this time, knowing what you know now.' Lior looked at the hourglass. The sand was moving. 'The cost is all your remaining years?' 'Yes.' 'How many do I have left?' The merchant looked at him kindly. 'Not as many as you think. But more than you deserve.' Lior reached for the hourglass.",
        "preview": "The Night Market sells impossible things. The currency isn't money — it's years of your life. At the last stall: an hourglass. 'It lets you relive your spent years, knowing what you know now.'",
    },
    {
        "title": "The Last Dragon's Accountant",
        "genre": "fantasy",
        "tone": "witty",
        "conflict": "The last dragon in the world hires a human accountant to manage his hoard",
        "characters": ["Petra", "Voss the dragon"],
        "hookText": "The last dragon on Earth doesn't need a knight. He needs a tax accountant.",
        "shareCaption": "The last dragon doesn't want to fight. He wants someone to sort his 6,000-year-old hoard and file his taxes.",
        "storyContext": "Petra expected fire and fury. Instead, she got a spreadsheet. Voss, the last living dragon, had 6,000 years of accumulated treasure — and absolutely no idea what any of it was worth in modern currency. 'I have seventeen tons of Byzantine gold,' he said, adjusting reading glasses on his snout. 'But I also appear to own a 40% stake in the Dutch East India Company, which I believe no longer exists.' Petra set up a laptop on a stalactite. The cave was organized by century. The 1200s section alone was worth more than most countries' GDP. 'The real problem,' Voss continued, 'is the IRS. They've been sending letters. I've been eating them, but apparently that's not a valid response.' Petra pulled up his tax history. There was none. Six thousand years of unreported income. The penalties alone would be astronomical. 'Also,' Voss said delicately, 'I may have accidentally acquired a small European country in 1463. Do I need to report that?' His massive golden eye blinked at her. 'And there's the other thing.' 'What other thing?' 'The egg. In the back vault. It started glowing last Tuesday. I think it's hatching, which means my tax filing status is about to change significantly.'",
        "preview": "The last dragon doesn't want to fight. He has 6,000 years of treasure and the IRS is sending letters. 'Also,' Voss said, 'there's an egg in the vault. It started glowing.'",
    },
    {
        "title": "The God of Small Repairs",
        "genre": "fantasy",
        "tone": "gentle",
        "conflict": "A forgotten god's only remaining power is fixing small broken things — until someone brings him something he can't fix",
        "characters": ["Mend", "The girl"],
        "hookText": "He was a god once. Now his only power is fixing small broken things. Then she brought him a broken heart.",
        "shareCaption": "A forgotten god who can only fix small things: cracked cups, torn pages. Then a girl brought him something impossible.",
        "storyContext": "Mend sat in his shop at the edge of the world, where the pavement crumbled into clouds. Once, he had commanded storms. Shaped mountains. Now he fixed teacups. People brought him cracked plates, torn photographs, watches that had stopped. He touched them and they became whole. It was all the power he had left — the last trickle of divinity in a world that had stopped believing. The girl arrived on a Thursday. She was maybe twelve. She placed something on his counter — invisible to the eye but heavy enough to dent the wood. 'What is it?' he asked, though he already knew. 'My heart,' she said. 'It broke when my mother left.' Mend reached for it. His fingers touched something jagged, warm, and impossibly complicated. For the first time in ten thousand years, his power flickered. Not because the heart was too broken. Because the break was the kind that wasn't meant to be fixed — it was meant to be understood. He looked at the girl. 'I can't fix this,' he said. The girl's face fell. 'But,' he continued, and his hands began to glow in a way they hadn't since the old world, 'I think I can make it into something new.'",
        "preview": "He was a god once. Now he fixes teacups. A girl brought him something invisible but heavy enough to dent the counter. 'My heart,' she said. 'It broke when my mother left.'",
    },
]


async def seed():
    client = AsyncIOMotorClient(MONGO_URL)
    database = client[DB_NAME]
    shares_col = database.shares

    now = datetime.now(timezone.utc)
    expires = (now + timedelta(days=365)).isoformat()

    inserted = 0
    skipped = 0

    for story in STORIES:
        # Check if already seeded (by title)
        existing = await shares_col.find_one({"title": story["title"], "seeded": True})
        if existing:
            skipped += 1
            continue

        share_id = str(uuid.uuid4())[:12]
        doc = {
            "id": share_id,
            "generationId": f"seed-{str(uuid.uuid4())[:8]}",
            "userId": "system-seed",
            "type": "STORY_VIDEO",
            "title": story["title"],
            "preview": story["preview"],
            "thumbnailUrl": None,
            "views": 0,
            "shares": 0,
            "forks": 0,
            "storyContext": story["storyContext"],
            "characters": story["characters"],
            "tone": story["tone"],
            "conflict": story["conflict"],
            "hookText": story["hookText"],
            "shareCaption": story["shareCaption"],
            "parentShareId": None,
            "genre": story["genre"],
            "seeded": True,
            "expiresAt": expires,
            "createdAt": now.isoformat(),
        }
        await shares_col.insert_one(doc)
        inserted += 1
        print(f"  Seeded: {story['title']} ({story['genre']}) -> /share/{share_id}")

    print(f"\nDone. Inserted: {inserted}, Skipped (already exist): {skipped}")
    print(f"Total stories in DB: {await shares_col.count_documents({'seeded': True})}")

    # Verify distribution
    for genre in ["mystery", "thriller", "emotional", "fantasy"]:
        count = await shares_col.count_documents({"seeded": True, "genre": genre})
        print(f"  {genre}: {count}")

    client.close()


if __name__ == "__main__":
    asyncio.run(seed())
