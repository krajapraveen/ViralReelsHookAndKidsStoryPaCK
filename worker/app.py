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

REEL_USER_PROMPT_TEMPLATE = """Generate a high-retention Instagram Reel package.
Constraints:
• Language: {language}
• Niche: {niche}
• Tone: {tone}
• Duration: {duration}
• Goal: {goal}
• Topic: {topic}
Output JSON schema:
{{
"hooks":["hook1", "hook2", "hook3", "hook4", "hook5"],
"best_hook":"selected hook",
"script":{{
"scenes":[
{{"time":"0-2s","on_screen_text":"...","voiceover":"...","broll":["..."]}},
],
"cta":"call to action"
}},
"caption_short":"...",
"caption_long":"...",
"hashtags":["20 hashtags"],
"posting_tips":["5 tips"]
}}
Rules:
• Hook must be under 12 words.
• Scenes must be punchy and scroll-stopping.
• No unsafe/illegal content.

Return ONLY valid JSON, no markdown or explanation."""

STORY_SYSTEM_PROMPT = """You create safe kids content. Output must be structured JSON only. No violence, no fear, no adult themes."""

# Optimized story prompt - concise and fast
STORY_USER_PROMPT_TEMPLATE = """Create kids story video pack in JSON format.

Input: Age:{ageGroup}|Theme:{theme}|Moral:{moral}|Chars:{characters}|Setting:{setting}|Scenes:{scenes}|Lang:{language}

Output ONLY this JSON (no markdown):
{{
"title":"catchy title",
"synopsis":"2 sentence summary",
"characters":[{{"name":"","description":""}}],
"scenes":[
{{"scene_number":1,"shot_type":"Medium/Close","visual_description":"1 sentence","narration":"narrator text","dialogue":[{{"speaker":"","line":""}}],"image_prompt":"detailed visual"}}
],
"youtube":{{"title":"","description":"","tags":["tag1","tag2","tag3"]}}
}}

Keep concise, safe, consistent characters. JSON only."""

async def generate_reel_content(data):
    """Generate reel script using LLM - optimized"""
    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"reel_{int(time.time())}"
        ).with_model("openai", "gpt-5.2").with_system_message(REEL_SYSTEM_PROMPT)
        
        prompt = REEL_USER_PROMPT_TEMPLATE.format(
            language=data.get('language', 'English'),
            niche=data.get('niche', 'General'),
            tone=data.get('tone', 'Bold'),
            duration=data.get('duration', '30s'),
            goal=data.get('goal', 'Followers'),
            topic=data.get('topic', '')
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
    """Generate story pack using LLM - optimized and fast"""
    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"story_{int(time.time())}",
            system_message=STORY_SYSTEM_PROMPT
        ).with_model("openai", "gpt-5.2")
        
        prompt = STORY_USER_PROMPT_TEMPLATE.format(
            ageGroup=data.get('ageGroup', '4-6'),
            theme=data.get('theme', 'Adventure'),
            moral=data.get('moral', 'Friendship'),
            characters=', '.join(data.get('characters', ['Kid', 'Dog'])),
            setting=data.get('setting', 'forest'),
            scenes=data.get('scenes', 8),
            language=data.get('language', 'English')
        )
        
        user_message = UserMessage(text=prompt)
        
        # Use faster generation with timeout
        response = await asyncio.wait_for(
            chat.send_message(user_message),
            timeout=45.0  # 45 second timeout
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
        logger.error("Story generation timeout after 45s")
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

if __name__ == '__main__':
    # Start RabbitMQ consumer in background thread
    consumer_thread = threading.Thread(target=run_rabbitmq_consumer, daemon=True)
    consumer_thread.start()
    
    logger.info("Starting Flask server on port 5000...")
    
    # Start Flask app with threading support
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
