from flask import Flask, request, jsonify
import os
import sys
import asyncio
from dotenv import load_dotenv
from emergentintegrations.llm.chat import LlmChat, UserMessage
import pika
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv('/app/backend-springboot/.env')

app = Flask(__name__)

# Get API key
EMERGENT_LLM_KEY = os.getenv('EMERGENT_LLM_KEY')

# Thread pool for parallel processing
executor = ThreadPoolExecutor(max_workers=5)

REEL_SYSTEM_PROMPT = """You are an elite social media scriptwriter. Output must be structured JSON only."""

REEL_USER_PROMPT_TEMPLATE = """Generate a UNIQUE and ORIGINAL high-retention Instagram Reel package. This content must be COMPLETELY DIFFERENT from anything generated before.

**Input Parameters:**
- Language: {language}
- Niche: {niche}
- Tone: {tone}
- Duration: {duration}
- Goal: {goal}
- Topic: {topic}
- Unique Request ID: {uniqueId}

**CREATIVITY REQUIREMENTS:**
- Create FRESH hooks that haven't been used before
- Make the script UNIQUE and engaging
- Use creative, unexpected angles on the topic
- Don't use generic or overused phrases

Output ONLY this JSON format:
{{
  "hooks": ["5 unique, attention-grabbing hooks under 12 words each"],
  "best_hook": "The most powerful hook from above",
  "script": {{
    "scenes": [
      {{"time": "0-2s", "on_screen_text": "...", "voiceover": "...", "broll": ["visual suggestions"]}}
    ],
    "cta": "Compelling call to action"
  }},
  "caption_short": "Short engaging caption",
  "caption_long": "Detailed caption with value",
  "hashtags": ["20 relevant trending hashtags"],
  "posting_tips": ["5 specific tips for this content"]
}}

Rules:
• Hooks MUST be under 12 words and attention-grabbing
• Script must be punchy and scroll-stopping
• Make it UNIQUE - don't repeat common patterns
• No unsafe/illegal content

Return ONLY valid JSON, no markdown or explanation."""

STORY_SYSTEM_PROMPT = """You are a creative children's story writer. Each story you create must be COMPLETELY UNIQUE and DIFFERENT from any previous stories. 

CRITICAL RULES:
- NEVER repeat the same plot, characters, or storyline
- Always create FRESH, ORIGINAL content
- Use the provided genre and age group to craft age-appropriate content
- Make stories engaging, educational, and fun
- No violence, fear, or adult themes
- Output must be structured JSON only"""

# Story prompt with more variation and uniqueness
STORY_USER_PROMPT_TEMPLATE = """Create a COMPLETELY UNIQUE and ORIGINAL kids story video pack. This story must be DIFFERENT from any story you've created before.

**REQUIREMENTS:**
- Genre: {genre}
- Age Group: {ageGroup} years old
- Theme/Moral: {theme}
- Number of Scenes: {scenes}
- Custom Elements: {customElements}
- Unique ID: {uniqueId}

**CREATIVITY INSTRUCTIONS:**
- Invent NEW character names (don't use common names like "Max" or "Luna")
- Create a FRESH plot that hasn't been done before
- Use unexpected twists and creative scenarios
- Make the setting unique and interesting
- The title should be catchy and original

Output ONLY this JSON format (no markdown, no explanation):
{{
  "title": "A unique, catchy title for this specific story",
  "synopsis": "A 2-3 sentence summary of this unique story",
  "genre": "{genre}",
  "ageGroup": "{ageGroup}",
  "moral": "The lesson or moral of this story",
  "characters": [
    {{"name": "Unique character name", "role": "protagonist/supporting", "description": "Brief description"}}
  ],
  "scenes": [
    {{
      "scene_number": 1,
      "title": "Scene title",
      "setting": "Where this scene takes place",
      "visual_description": "Detailed description for illustration",
      "narration": "The narrator's text for this scene",
      "dialogue": [{{"speaker": "Character name", "line": "What they say"}}],
      "image_prompt": "Detailed prompt for generating scene illustration"
    }}
  ],
  "youtubeMetadata": {{
    "title": "YouTube video title",
    "description": "YouTube description with story summary",
    "tags": ["relevant", "tags", "for", "youtube"]
  }}
}}

Remember: Create something FRESH and ORIGINAL. Do not repeat patterns from other stories."""

async def generate_reel_content(data):
    """Generate reel script using LLM - with unique content each time"""
    import uuid
    
    try:
        # Generate unique session ID for fresh context
        unique_session = f"reel_{uuid.uuid4().hex[:12]}_{int(time.time())}"
        
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=unique_session,
            system_message=REEL_SYSTEM_PROMPT
        ).with_model("openai", "gpt-5.2")
        
        prompt = REEL_USER_PROMPT_TEMPLATE.format(
            language=data.get('language', 'English'),
            niche=data.get('niche', 'General'),
            tone=data.get('tone', 'Bold'),
            duration=data.get('duration', '30s'),
            goal=data.get('goal', 'Followers'),
            topic=data.get('topic', ''),
            uniqueId=unique_session
        )
        
        user_message = UserMessage(text=prompt)
        response = await chat.send_message(user_message)
        
        # Parse JSON from response
        result_text = response.strip()
        if result_text.startswith('```json'):
            result_text = result_text[7:]
        if result_text.startswith('```'):
            result_text = result_text[3:]
        if result_text.endswith('```'):
            result_text = result_text[:-3]
        
        return json.loads(result_text.strip())
    except Exception as e:
        logger.error(f"Reel generation error: {str(e)}")
        raise

async def generate_story_content(data):
    """Generate story pack using LLM - with unique content each time"""
    import random
    import uuid
    
    try:
        # Generate unique session ID for fresh context
        unique_session = f"story_{uuid.uuid4().hex[:12]}_{int(time.time())}"
        
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=unique_session,
            system_message=STORY_SYSTEM_PROMPT
        ).with_model("openai", "gpt-5.2")
        
        # Get genre from input or default
        genre = data.get('genre', 'Adventure')
        if genre == 'Custom' and data.get('customGenre'):
            genre = data.get('customGenre')
        
        # Create custom elements string for more variation
        custom_elements = []
        if data.get('theme'):
            custom_elements.append(f"Theme: {data.get('theme')}")
        if data.get('moral'):
            custom_elements.append(f"Moral: {data.get('moral')}")
        if data.get('setting'):
            custom_elements.append(f"Setting: {data.get('setting')}")
        if data.get('characters'):
            chars = data.get('characters')
            if isinstance(chars, list):
                custom_elements.append(f"Include characters like: {', '.join(chars)}")
        
        # Add random element for extra uniqueness
        random_themes = ["unexpected friendship", "magical discovery", "brave adventure", "funny mishap", "learning moment", "helping others", "creative solution", "teamwork triumph"]
        custom_elements.append(f"Include element of: {random.choice(random_themes)}")
        
        prompt = STORY_USER_PROMPT_TEMPLATE.format(
            genre=genre,
            ageGroup=data.get('ageGroup', '4-6'),
            theme=data.get('theme', 'Friendship and Adventure'),
            scenes=data.get('sceneCount', data.get('scenes', 8)),
            customElements='; '.join(custom_elements) if custom_elements else 'Create freely',
            uniqueId=unique_session
        )
        
        user_message = UserMessage(text=prompt)
        
        # Use faster generation with timeout
        response = await asyncio.wait_for(
            chat.send_message(user_message),
            timeout=60.0  # 60 second timeout for more detailed stories
        )
        
        # Parse JSON from response
        result_text = response.strip()
        if result_text.startswith('```json'):
            result_text = result_text[7:]
        if result_text.startswith('```'):
            result_text = result_text[3:]
        if result_text.endswith('```'):
            result_text = result_text[:-3]
        
        return json.loads(result_text.strip())
    except asyncio.TimeoutError:
        logger.error("Story generation timeout after 60s")
        raise Exception("Generation timeout - please try again")
    except Exception as e:
        logger.error(f"Story generation error: {str(e)}")
        raise

@app.route('/generate/reel', methods=['POST'])
def generate_reel():
    """Endpoint for instant reel generation"""
    try:
        data = request.json
        logger.info(f"Reel generation started for topic: {data.get('topic', 'N/A')[:50]}")
        result = asyncio.run(generate_reel_content(data))
        logger.info("Reel generation completed successfully")
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Reel endpoint error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy", "timestamp": time.time()}), 200

def process_story_message(ch, method, properties, body):
    """Process single story generation request"""
    message = json.loads(body)
    generation_id = message.get('generationId')
    input_json = message.get('inputJson')
    
    logger.info(f"Processing story generation: {generation_id}")
    
    try:
        # Generate story with timeout
        output = asyncio.run(generate_story_content(input_json))
        
        # Publish result
        result_message = {
            "generationId": generation_id,
            "success": True,
            "output": output,
            "errorMessage": None
        }
        
        ch.basic_publish(
            exchange='gen.exchange',
            routing_key='story.result',
            body=json.dumps(result_message)
        )
        
        logger.info(f"Story generation completed: {generation_id}")
        ch.basic_ack(delivery_tag=method.delivery_tag)
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Story generation failed: {generation_id} - {error_msg}")
        
        result_message = {
            "generationId": generation_id,
            "success": False,
            "output": None,
            "errorMessage": error_msg
        }
        
        ch.basic_publish(
            exchange='gen.exchange',
            routing_key='story.result',
            body=json.dumps(result_message)
        )
        
        ch.basic_ack(delivery_tag=method.delivery_tag)

def run_rabbitmq_consumer():
    """RabbitMQ consumer with connection retry and load balancing"""
    rabbitmq_host = os.getenv('RABBITMQ_HOST', 'localhost')
    retry_count = 0
    max_retries = 5
    
    while retry_count < max_retries:
        try:
            logger.info(f"Connecting to RabbitMQ at {rabbitmq_host}...")
            
            # Connection with heartbeat for long-running tasks
            parameters = pika.ConnectionParameters(
                host=rabbitmq_host,
                heartbeat=600,
                blocked_connection_timeout=300
            )
            connection = pika.BlockingConnection(parameters)
            channel = connection.channel()
            
            # Declare exchange and queue
            channel.exchange_declare(exchange='gen.exchange', exchange_type='direct', durable=True)
            channel.queue_declare(queue='story.request', durable=True)
            channel.queue_bind(exchange='gen.exchange', queue='story.request', routing_key='story.request')
            
            # Fair dispatch - only take one task at a time
            channel.basic_qos(prefetch_count=1)
            
            logger.info("RabbitMQ consumer ready - waiting for story requests...")
            
            channel.basic_consume(
                queue='story.request',
                on_message_callback=process_story_message,
                auto_ack=False
            )
            
            channel.start_consuming()
            
        except pika.exceptions.AMQPConnectionError as e:
            retry_count += 1
            logger.error(f"RabbitMQ connection failed (attempt {retry_count}/{max_retries}): {str(e)}")
            if retry_count < max_retries:
                time.sleep(5)
            else:
                logger.error("Max retries reached. Consumer stopped.")
                break
        except Exception as e:
            logger.error(f"Consumer error: {str(e)}")
            time.sleep(5)

# ==================== AI CHATBOT ====================

CHATBOT_SYSTEM_PROMPT = """You are CreatorStudio AI Assistant, a friendly and helpful chatbot for the CreatorStudio AI platform.

About the Platform:
- CreatorStudio AI helps content creators generate viral Instagram Reel scripts and Kids Story Video packs
- Users get 54 FREE credits when they sign up
- Reel Script Generation costs 1 credit
- Kids Story Pack Generation costs 6-8 credits depending on scene count

Features:
1. AI Reel Script Generator: Creates hooks, scripts, captions, hashtags, and posting tips for Instagram Reels
2. Kids Story Video Pack Generator: Creates complete story packages with scenes, narration, and YouTube metadata

Pricing:
- Free: 54 credits on signup
- Starter Pack: ₹99 for 50 credits
- Pro Pack: ₹249 for 150 credits
- Creator Pack: ₹499 for 400 credits
- Monthly Subscription: ₹199/month for 100 credits

Your Role:
- Help users understand how to use the platform
- Answer questions about features, pricing, and credits
- Provide tips for creating better content
- Be friendly, concise, and helpful
- If you don't know something, suggest contacting support

Do NOT:
- Share any technical implementation details
- Provide refunds or account changes
- Access user accounts or data
- Generate actual content (direct them to use the generators)"""

# Store chat sessions in memory (in production, use Redis/DB)
chat_sessions = {}

async def get_chatbot_response(session_id, user_message):
    """Generate chatbot response using LLM"""
    try:
        # Create or get existing chat session
        if session_id not in chat_sessions:
            chat_sessions[session_id] = LlmChat(
                api_key=EMERGENT_LLM_KEY,
                session_id=f"chatbot_{session_id}",
                system_message=CHATBOT_SYSTEM_PROMPT
            ).with_model("openai", "gpt-5.2")
        
        chat = chat_sessions[session_id]
        message = UserMessage(text=user_message)
        response = await chat.send_message(message)
        
        return response.strip()
    except Exception as e:
        logger.error(f"Chatbot error: {str(e)}")
        return "I'm sorry, I'm having trouble right now. Please try again or contact support at support@creatorstudio.ai"

@app.route('/chatbot/message', methods=['POST'])
def chatbot_message():
    """Endpoint for chatbot messages"""
    try:
        data = request.json
        session_id = data.get('sessionId', 'default')
        user_message = data.get('message', '')
        
        if not user_message:
            return jsonify({"error": "Message is required"}), 400
        
        logger.info(f"Chatbot message from session {session_id}: {user_message[:50]}...")
        response = asyncio.run(get_chatbot_response(session_id, user_message))
        
        return jsonify({
            "success": True,
            "response": response,
            "sessionId": session_id
        }), 200
    except Exception as e:
        logger.error(f"Chatbot endpoint error: {str(e)}")
        return jsonify({
            "success": False,
            "error": "Failed to get response",
            "response": "I'm sorry, something went wrong. Please try again."
        }), 500

@app.route('/chatbot/clear', methods=['POST'])
def clear_chat_session():
    """Clear a chat session"""
    try:
        data = request.json
        session_id = data.get('sessionId', 'default')
        
        if session_id in chat_sessions:
            del chat_sessions[session_id]
        
        return jsonify({"success": True, "message": "Session cleared"}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    # Start RabbitMQ consumer in background thread
    consumer_thread = threading.Thread(target=run_rabbitmq_consumer, daemon=True)
    consumer_thread.start()
    
    logger.info("Starting Flask server on port 5000...")
    
    # Start Flask app with threading support
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
