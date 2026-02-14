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

load_dotenv('/app/backend-springboot/.env')

app = Flask(__name__)

# Get API key
EMERGENT_LLM_KEY = os.getenv('EMERGENT_LLM_KEY')

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
  "hooks": ["hook1", "hook2", "hook3", "hook4", "hook5"],
  "best_hook": "selected hook",
  "script": {{
    "scenes": [
      {{"time": "0-2s", "on_screen_text": "...", "voiceover": "...", "broll": ["..."]}}
    ],
    "cta": "call to action"
  }},
  "caption_short": "...",
  "caption_long": "...",
  "hashtags": ["20 hashtags"],
  "posting_tips": ["5 tips"]
}}

Rules:
• Hook must be under 12 words
• Scenes must be punchy and scroll-stopping
• No unsafe/illegal content

Return ONLY valid JSON, no markdown or explanation."""

STORY_SYSTEM_PROMPT = """You create safe kids content. Output must be structured JSON only. No violence, no fear, no adult themes."""

STORY_USER_PROMPT_TEMPLATE = """Create a kids story video pack.

Age: {ageGroup} | Theme: {theme} | Moral: {moral}
Characters: {characters} | Setting: {setting} | Scenes: {scenes}
Language: {language} | Style: {style} | Length: {length}

Generate JSON with this EXACT structure (no markdown):
{{
  "title": "short catchy title",
  "synopsis": "2-3 sentence summary",
  "characters": [{{"name": "...", "description": "brief visual description"}}],
  "scenes": [
    {{
      "scene_number": 1,
      "shot_type": "Medium/Close-up",
      "visual_description": "what we see (1 sentence)",
      "narration": "narrator text",
      "dialogue": [{{"speaker": "name", "line": "..."}}],
      "image_prompt": "detailed prompt for consistent character style"
    }}
  ],
  "youtube": {{
    "title": "optimized title",
    "description": "brief description",
    "tags": ["tag1", "tag2", "tag3"]
  }}
}}

Keep it concise, safe for kids, maintain character consistency. Return ONLY valid JSON."""

async def generate_reel_content(data):
    """Generate reel script using LLM"""
    chat = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=f"reel_{int(time.time())}",
        system_message=REEL_SYSTEM_PROMPT
    ).with_model("openai", "gpt-5.2")
    
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

async def generate_story_content(data):
    """Generate story pack using LLM"""
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
        language=data.get('language', 'English'),
        style=data.get('style', 'Pixar-like 3D'),
        length=data.get('length', '60s')
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

@app.route('/generate/reel', methods=['POST'])
def generate_reel():
    """Endpoint for instant reel generation"""
    try:
        data = request.json
        result = asyncio.run(generate_reel_content(data))
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy"}), 200

def process_story_queue():
    """Background worker for story generation queue"""
    print("Starting RabbitMQ consumer for story generation...")
    
    rabbitmq_host = os.getenv('RABBITMQ_HOST', 'localhost')
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=rabbitmq_host))
    channel = connection.channel()
    
    channel.queue_declare(queue='story.request', durable=True)
    
    def callback(ch, method, properties, body):
        print(f" [x] Received story request")
        message = json.loads(body)
        generation_id = message.get('generationId')
        input_json = message.get('inputJson')
        
        try:
            # Generate story
            output = asyncio.run(generate_story_content(input_json))
            
            # Update database via API (simplified - in production use direct DB or result queue)
            print(f" [✓] Story generated successfully for {generation_id}")
            # Here you would update the Generation table with output
            # For MVP, we'll publish to result queue
            result_message = {
                "generationId": generation_id,
                "success": True,
                "output": output,
                "errorMessage": None
            }
            channel.basic_publish(
                exchange='gen.exchange',
                routing_key='story.result',
                body=json.dumps(result_message)
            )
        except Exception as e:
            print(f" [x] Error generating story: {str(e)}")
            result_message = {
                "generationId": generation_id,
                "success": False,
                "output": None,
                "errorMessage": str(e)
            }
            channel.basic_publish(
                exchange='gen.exchange',
                routing_key='story.result',
                body=json.dumps(result_message)
            )
        
        ch.basic_ack(delivery_tag=method.delivery_tag)
    
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue='story.request', on_message_callback=callback)
    
    print(' [*] Waiting for story generation requests. To exit press CTRL+C')
    channel.start_consuming()

if __name__ == '__main__':
    # Start queue consumer in background thread
    consumer_thread = threading.Thread(target=process_story_queue, daemon=True)
    consumer_thread.start()
    
    # Start Flask app
    app.run(host='0.0.0.0', port=5000, debug=False)
