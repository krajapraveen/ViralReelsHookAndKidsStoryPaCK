"""
Fallback Output Service - Provides Alternative Outputs When Generation Fails
Implements graceful degradation instead of silent failures
"""
import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)


class FallbackOutputService:
    """Service for generating fallback outputs when primary generation fails"""
    
    COLLECTION_NAME = "fallback_outputs"
    
    # Fallback templates for different job types
    FALLBACK_TEMPLATES = {
        "TEXT_TO_VIDEO": {
            "type": "script_fallback",
            "message": "Video generation encountered an issue. Here's your video script instead:",
            "provides": ["script", "storyboard_outline", "visual_suggestions"],
        },
        "TEXT_TO_IMAGE": {
            "type": "prompt_enhancement",
            "message": "Image generation encountered an issue. Here's an enhanced prompt you can try:",
            "provides": ["enhanced_prompt", "style_suggestions", "alternative_prompts"],
        },
        "IMAGE_TO_VIDEO": {
            "type": "animation_guide",
            "message": "Video animation encountered an issue. Here's an animation guide for your image:",
            "provides": ["motion_suggestions", "transition_ideas", "timing_guide"],
        },
        "STORY_GENERATION": {
            "type": "story_outline",
            "message": "Full story generation encountered an issue. Here's a story outline:",
            "provides": ["story_outline", "character_sketches", "scene_suggestions"],
        },
        "REEL_GENERATION": {
            "type": "reel_framework",
            "message": "Reel script generation encountered an issue. Here's a content framework:",
            "provides": ["hook_ideas", "content_structure", "cta_suggestions"],
        },
    }
    
    def __init__(self, db):
        self.db = db
    
    async def initialize(self):
        """Create indexes for fallback collection"""
        try:
            await self.db[self.COLLECTION_NAME].create_index("jobId", unique=True)
            await self.db[self.COLLECTION_NAME].create_index("userId")
            await self.db[self.COLLECTION_NAME].create_index("createdAt")
            logger.info("Fallback output indexes created")
        except Exception as e:
            logger.warning(f"Fallback index creation: {e}")
    
    async def generate_fallback(
        self, 
        job_id: str,
        user_id: str,
        job_type: str, 
        input_data: Dict[str, Any],
        error_message: str
    ) -> Optional[Dict[str, Any]]:
        """
        Generate a fallback output for a failed job.
        Returns None if no fallback is available for this job type.
        """
        template = self.FALLBACK_TEMPLATES.get(job_type)
        if not template:
            logger.info(f"No fallback template for job type: {job_type}")
            return None
        
        fallback_content = await self._create_fallback_content(job_type, input_data, template)
        
        if not fallback_content:
            return None
        
        # Store the fallback output
        fallback_record = {
            "jobId": job_id,
            "userId": user_id,
            "jobType": job_type,
            "fallbackType": template["type"],
            "message": template["message"],
            "content": fallback_content,
            "originalError": error_message,
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "creditsRefunded": True  # Partial refund for fallback
        }
        
        try:
            await self.db[self.COLLECTION_NAME].insert_one(fallback_record)
        except Exception as e:
            if "duplicate key" not in str(e).lower():
                logger.error(f"Failed to store fallback: {e}")
        
        # Remove MongoDB _id before returning
        fallback_record.pop("_id", None)
        
        logger.info(f"Generated {template['type']} fallback for job {job_id}")
        return fallback_record
    
    async def _create_fallback_content(
        self, 
        job_type: str, 
        input_data: Dict[str, Any],
        template: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Create the actual fallback content based on job type"""
        
        if job_type == "TEXT_TO_VIDEO":
            return self._video_to_script_fallback(input_data)
        
        elif job_type == "TEXT_TO_IMAGE":
            return self._image_to_prompt_fallback(input_data)
        
        elif job_type == "IMAGE_TO_VIDEO":
            return self._animation_guide_fallback(input_data)
        
        elif job_type == "STORY_GENERATION":
            return self._story_outline_fallback(input_data)
        
        elif job_type == "REEL_GENERATION":
            return self._reel_framework_fallback(input_data)
        
        return None
    
    def _video_to_script_fallback(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert video request to script fallback"""
        prompt = input_data.get("prompt", "")
        duration = input_data.get("duration", 4)
        
        return {
            "script": f"""VIDEO SCRIPT
Duration: {duration} seconds
Prompt: {prompt}

SCENE BREAKDOWN:
- Opening (0-{duration//4}s): Establish the scene with {prompt[:50]}...
- Middle ({duration//4}-{duration*3//4}s): Main action and development
- Closing ({duration*3//4}-{duration}s): Resolution and call-to-action

VISUAL SUGGESTIONS:
- Use smooth camera movements
- Consider adding text overlays for key points
- Background music tempo: {'upbeat' if duration < 10 else 'cinematic'}
""",
            "storyboard_outline": [
                {"time": "0s", "description": "Opening shot"},
                {"time": f"{duration//2}s", "description": "Main content"},
                {"time": f"{duration}s", "description": "Closing shot"}
            ],
            "visual_suggestions": [
                "Consider using stock footage as placeholder",
                "Add motion graphics for engagement",
                "Include captions for accessibility"
            ],
            "retry_tips": [
                "Try a simpler prompt",
                "Reduce video duration",
                "Check if the content violates guidelines"
            ]
        }
    
    def _image_to_prompt_fallback(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance prompt and provide alternatives"""
        prompt = input_data.get("prompt", "")
        aspect_ratio = input_data.get("aspect_ratio", "1:1")
        
        return {
            "enhanced_prompt": f"High quality, detailed, professional photography style: {prompt}. Sharp focus, good lighting, 8k resolution.",
            "style_suggestions": [
                f"Photorealistic: {prompt}, photorealistic, detailed, professional",
                f"Artistic: {prompt}, digital art, vibrant colors, stylized",
                f"Minimalist: {prompt}, minimalist design, clean lines, simple"
            ],
            "alternative_prompts": [
                f"{prompt}, closeup view, detailed",
                f"{prompt}, wide shot, environmental",
                f"{prompt}, dramatic lighting, cinematic"
            ],
            "technical_tips": [
                f"Aspect ratio {aspect_ratio} works best with centered subjects",
                "Add specific style keywords like 'watercolor', 'oil painting', etc.",
                "Include lighting descriptors: 'soft lighting', 'golden hour', etc."
            ]
        }
    
    def _animation_guide_fallback(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Provide animation guidance for image-to-video"""
        motion_prompt = input_data.get("motionPrompt", input_data.get("prompt", ""))
        duration = input_data.get("duration", 4)
        
        return {
            "motion_suggestions": [
                "Subtle zoom in/out (Ken Burns effect)",
                "Gentle pan across the image",
                "Parallax effect with depth layers",
                "Particle effects overlay"
            ],
            "transition_ideas": [
                "Fade in from black",
                "Crossfade to next scene",
                "Slide transition"
            ],
            "timing_guide": {
                "duration_seconds": duration,
                "keyframes": [
                    {"time": 0, "action": "Initial state"},
                    {"time": duration / 2, "action": "Mid-animation peak"},
                    {"time": duration, "action": "Final state"}
                ]
            },
            "diy_tools": [
                "CapCut - Free mobile video editor with animation",
                "Canva - Simple animation features",
                "After Effects - Professional animation"
            ]
        }
    
    def _story_outline_fallback(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Provide story outline when full generation fails"""
        genre = input_data.get("genre", "Adventure")
        age_group = input_data.get("ageGroup", "4-6")
        theme = input_data.get("theme", "Friendship")
        scene_count = input_data.get("sceneCount", 8)
        
        return {
            "story_outline": {
                "genre": genre,
                "target_age": age_group,
                "theme": theme,
                "structure": {
                    "introduction": f"Scene 1-2: Introduce main character in a {genre.lower()} setting",
                    "rising_action": f"Scene 3-{scene_count//2}: Character faces challenges related to {theme.lower()}",
                    "climax": f"Scene {scene_count//2 + 1}-{scene_count - 2}: The big moment of the story",
                    "resolution": f"Scene {scene_count - 1}-{scene_count}: Happy ending with lesson learned"
                }
            },
            "character_sketches": [
                {"name": "Main Character", "traits": "Curious, brave, kind"},
                {"name": "Helper Friend", "traits": "Loyal, funny, supportive"},
                {"name": "Mentor Figure", "traits": "Wise, patient, encouraging"}
            ],
            "scene_suggestions": [
                f"Opening: A beautiful {genre.lower()} world",
                f"Challenge: Something tests the {theme.lower()} theme",
                f"Solution: Working together saves the day",
                f"Ending: Everyone celebrates and learns"
            ]
        }
    
    def _reel_framework_fallback(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Provide reel content framework"""
        niche = input_data.get("niche", "General")
        tone = input_data.get("tone", "Bold")
        duration = input_data.get("duration", "30s")
        topic = input_data.get("topic", "")
        
        return {
            "hook_ideas": [
                f"Start with a surprising fact about {topic or niche}",
                f"Ask a provocative question: 'Did you know...?'",
                f"Use a {tone.lower()} statement to grab attention",
                "Show the end result first (before/after)"
            ],
            "content_structure": {
                "hook": "0-3 seconds: Attention grabber",
                "context": "3-10 seconds: Set up the topic",
                "value": "10-25 seconds: Deliver the main content",
                "cta": f"25-{duration}: Call to action"
            },
            "cta_suggestions": [
                "Follow for more tips!",
                "Save this for later",
                "Share with someone who needs this",
                "Comment your thoughts below",
                "Link in bio for more"
            ],
            "trending_formats": [
                "Story time with text overlays",
                "Quick tips carousel",
                "Behind the scenes",
                "Day in the life",
                f"{tone} take on {niche}"
            ]
        }
    
    async def get_fallback_for_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve fallback output for a job"""
        fallback = await self.db[self.COLLECTION_NAME].find_one(
            {"jobId": job_id},
            {"_id": 0}
        )
        return fallback
    
    async def get_user_fallbacks(
        self, 
        user_id: str, 
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Get fallback outputs for a user"""
        fallbacks = await self.db[self.COLLECTION_NAME].find(
            {"userId": user_id},
            {"_id": 0}
        ).sort("createdAt", -1).limit(limit).to_list(limit)
        return fallbacks


# Singleton instance
_fallback_service: Optional[FallbackOutputService] = None


async def get_fallback_service(db) -> FallbackOutputService:
    """Get or create the fallback service singleton"""
    global _fallback_service
    if _fallback_service is None:
        _fallback_service = FallbackOutputService(db)
        await _fallback_service.initialize()
    return _fallback_service
