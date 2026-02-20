"""
User Manual / Help Documentation Module
Provides comprehensive user guides for all features
"""
from fastapi import APIRouter, HTTPException
from typing import Optional, List, Dict, Any

router = APIRouter(prefix="/help", tags=["User Manual"])


# =============================================================================
# COMPREHENSIVE USER MANUAL DATA
# =============================================================================

USER_MANUAL = {
    "overview": {
        "title": "Welcome to CreatorStudio AI",
        "description": "Your all-in-one AI-powered content creation platform for viral reels, stories, and more.",
        "quickStart": [
            "1. Sign up or log in to your account",
            "2. Check your credit balance in the top navigation",
            "3. Choose a feature from the dashboard",
            "4. Follow the on-screen instructions",
            "5. Download or share your creations"
        ]
    },
    
    "features": {
        "genstudio": {
            "title": "GenStudio AI",
            "description": "Create stunning AI-generated images and videos from text prompts.",
            "icon": "sparkles",
            "creditCost": "10-30 credits per generation",
            "subFeatures": {
                "text_to_image": {
                    "title": "Text to Image",
                    "description": "Generate high-quality images from text descriptions.",
                    "howToUse": [
                        "1. Navigate to GenStudio → Text to Image",
                        "2. Enter a detailed description of the image you want",
                        "3. (Optional) Add negative prompts to exclude unwanted elements",
                        "4. Select aspect ratio and style",
                        "5. Click 'Generate' and wait for your image",
                        "6. Download or regenerate as needed"
                    ],
                    "tips": [
                        "Be specific about colors, lighting, and composition",
                        "Use artistic references like 'watercolor style' or 'cinematic lighting'",
                        "Negative prompts help avoid unwanted elements"
                    ],
                    "creditCost": "10 credits"
                },
                "text_to_video": {
                    "title": "Text to Video",
                    "description": "Create AI-generated videos from text prompts using Sora 2.",
                    "howToUse": [
                        "1. Navigate to GenStudio → Text to Video",
                        "2. Describe the video scene you want",
                        "3. Select duration (4, 8, or 12 seconds)",
                        "4. Choose aspect ratio",
                        "5. Click 'Generate' - videos take 2-5 minutes",
                        "6. Download when complete"
                    ],
                    "tips": [
                        "Describe movement and action clearly",
                        "Shorter videos have higher quality",
                        "Use cinematic descriptions for better results"
                    ],
                    "creditCost": "25+ credits (varies by duration)"
                },
                "image_to_video": {
                    "title": "Image to Video",
                    "description": "Animate still images into video clips.",
                    "howToUse": [
                        "1. Navigate to GenStudio → Image to Video",
                        "2. Upload an image (JPEG, PNG)",
                        "3. Describe the motion you want",
                        "4. Select duration and settings",
                        "5. Click 'Generate' and wait",
                        "6. Download the animated video"
                    ],
                    "creditCost": "20+ credits"
                }
            }
        },
        
        "story_generator": {
            "title": "Kids Story Generator",
            "description": "Create personalized children's stories with illustrations.",
            "icon": "book-open",
            "creditCost": "10 credits per story",
            "howToUse": [
                "1. Navigate to Create Kids Story Pack",
                "2. Enter character names and ages",
                "3. Select genre and theme",
                "4. Choose age group (2-4, 4-7, 7-10, 10+)",
                "5. Add any special elements",
                "6. Click 'Generate Story'",
                "7. View your story with illustrations"
            ],
            "tips": [
                "Use names of children you know for personalization",
                "Select age-appropriate themes",
                "Generated stories include moral lessons"
            ]
        },
        
        "reel_generator": {
            "title": "Reel Script Generator",
            "description": "Create viral reel scripts in seconds.",
            "icon": "video",
            "creditCost": "10 credits per reel",
            "howToUse": [
                "1. Navigate to Generate Reel Script",
                "2. Enter your topic or niche",
                "3. Select target platform (Instagram, TikTok, YouTube)",
                "4. Choose tone (Funny, Educational, Motivational)",
                "5. Click 'Generate Script'",
                "6. Copy or download your script"
            ],
            "tips": [
                "Be specific about your niche",
                "Include trending topics for better engagement",
                "Scripts include hooks and CTAs"
            ]
        },
        
        "story_series": {
            "title": "Story Series Mode",
            "description": "Turn single stories into multi-episode series with consistent characters.",
            "icon": "film",
            "creditCost": "8-18 credits (based on episode count)",
            "howToUse": [
                "1. Navigate to Story Series",
                "2. Select an existing story OR enter a new summary",
                "3. Add character names",
                "4. Select theme (Adventure, Mystery, etc.)",
                "5. Choose episode count (3, 5, or 7)",
                "6. Click 'Generate Series'",
                "7. Download outline or script pack"
            ],
            "features": [
                "Consistent character development",
                "Scene beats for each episode",
                "Cliffhanger endings",
                "Next episode hooks",
                "Character Bible add-on"
            ],
            "creditCost": {
                "3 episodes": "8 credits",
                "5 episodes": "12 credits",
                "7 episodes": "18 credits",
                "Character Bible": "+5 credits"
            }
        },
        
        "challenge_generator": {
            "title": "Challenge Generator",
            "description": "Create 7-day or 30-day content challenges with hooks and hashtags.",
            "icon": "calendar",
            "creditCost": "6-15 credits",
            "howToUse": [
                "1. Navigate to Challenge Generator",
                "2. Select duration (7 or 30 days)",
                "3. Choose your niche (Luxury, Fitness, etc.)",
                "4. Select platform (Instagram, YouTube, TikTok)",
                "5. Set your goal (Followers, Leads, Sales)",
                "6. Adjust time per day slider",
                "7. Click 'Generate Challenge'",
                "8. View daily content plan",
                "9. Download CSV calendar"
            ],
            "includes": [
                "Daily hooks and CTAs",
                "Platform-optimized hashtags",
                "Posting time recommendations",
                "Content complexity guidance"
            ]
        },
        
        "tone_switcher": {
            "title": "Tone Switcher",
            "description": "Transform text into different emotional tones without AI costs.",
            "icon": "wand",
            "creditCost": "1-5 credits",
            "howToUse": [
                "1. Navigate to Tone Switcher",
                "2. Paste your original text",
                "3. Choose target tone:",
                "   - Funny (adds humor and emojis)",
                "   - Aggressive (bold and direct)",
                "   - Calm (gentle and soothing)",
                "   - Luxury (elegant and premium)",
                "   - Motivational (inspiring and uplifting)",
                "4. Adjust intensity slider",
                "5. Select length preference",
                "6. Try 'Free Preview' first",
                "7. Generate variations (1, 5, or 10)",
                "8. Copy or download results"
            ],
            "tips": [
                "Higher intensity = more dramatic changes",
                "Free preview lets you test before committing credits",
                "Great for social media captions and scripts"
            ]
        },
        
        "coloring_book": {
            "title": "Kids Coloring Book Creator",
            "description": "Create personalized printable coloring books from your stories.",
            "icon": "palette",
            "creditCost": "5-8 credits",
            "howToUse": [
                "1. Navigate to Kids Coloring Book",
                "2. Select a story from your library",
                "3. Choose creation mode:",
                "   - DIY Mode: Empty frames with prompts",
                "   - Photo Mode: Upload images for outline conversion",
                "4. Configure export settings:",
                "   - Page count (8, 10, or 12)",
                "   - Paper size (A4 or US Letter)",
                "   - Activity pages (optional)",
                "   - Personalized cover (add child's name)",
                "5. Click 'Export PDF'",
                "6. PDF downloads automatically"
            ],
            "privacyNote": "Images are processed locally in your browser. We never upload or store them.",
            "includes": [
                "Cover page with title",
                "Scene pages with illustrations",
                "Activity pages (optional)",
                "Moral/lesson page",
                "Completion certificate"
            ]
        },
        
        "creator_tools": {
            "title": "Creator Tools",
            "description": "15+ AI-powered tools for content creators.",
            "icon": "tools",
            "creditCost": "Varies by tool",
            "tools": [
                {
                    "name": "30-Day Content Calendar",
                    "description": "Generate a full month of content ideas"
                },
                {
                    "name": "Carousel Generator",
                    "description": "Create swipeable carousel content"
                },
                {
                    "name": "Hashtag Bank",
                    "description": "Generate niche-specific hashtags"
                },
                {
                    "name": "Thumbnail Generator",
                    "description": "Create eye-catching thumbnails"
                },
                {
                    "name": "Trending Topics",
                    "description": "Find what's trending in your niche"
                }
            ]
        }
    },
    
    "account": {
        "credits": {
            "title": "Understanding Credits",
            "description": "Credits are the currency used for all AI generations.",
            "howItWorks": [
                "Each feature costs a certain number of credits",
                "Credits are deducted only after successful generation",
                "Failed generations don't cost credits",
                "Check your balance in the top navigation"
            ],
            "howToGetCredits": [
                "Subscribe to a plan (Weekly, Monthly, Quarterly)",
                "Purchase top-up credit packs",
                "Earn bonus credits through referrals"
            ]
        },
        "subscription": {
            "title": "Subscription Plans",
            "description": "Choose a plan that fits your needs.",
            "plans": [
                {"name": "Weekly", "price": "₹99 / $4.99", "credits": 30},
                {"name": "Monthly", "price": "₹299 / $9.99", "credits": 100},
                {"name": "Quarterly", "price": "₹699 / $24.99", "credits": 350}
            ],
            "howToManage": [
                "Go to Dashboard → View Plans",
                "View current subscription status",
                "Cancel or reactivate auto-renewal",
                "Upgrade to a higher plan anytime"
            ]
        },
        "payments": {
            "title": "Payments & Billing",
            "description": "Secure payments powered by Cashfree.",
            "supported": [
                "UPI (Google Pay, PhonePe, Paytm)",
                "Credit/Debit Cards",
                "Net Banking",
                "International Cards (USD → INR conversion)"
            ],
            "refunds": [
                "Request refund within 7 days of purchase",
                "Unused credits are refundable",
                "Refunds processed in 5-7 business days"
            ]
        }
    },
    
    "troubleshooting": {
        "common_issues": [
            {
                "issue": "Generation taking too long",
                "solution": "Video generation can take 2-5 minutes. Check job status in your dashboard."
            },
            {
                "issue": "Download not working",
                "solution": "Try right-clicking and 'Save As'. Check your browser's download settings."
            },
            {
                "issue": "Credits not deducted",
                "solution": "Credits are reserved during generation and captured on success."
            },
            {
                "issue": "Image not displaying",
                "solution": "Refresh the page. If issue persists, regenerate the content."
            },
            {
                "issue": "Payment failed",
                "solution": "Check card details or try a different payment method. Contact support if needed."
            }
        ],
        "contact": {
            "email": "support@creatorstudio.ai",
            "responseTime": "Within 24 hours"
        }
    }
}


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.get("/manual")
async def get_full_manual():
    """Get complete user manual"""
    return USER_MANUAL


@router.get("/manual/{section}")
async def get_manual_section(section: str):
    """Get specific section of user manual"""
    if section not in USER_MANUAL:
        raise HTTPException(status_code=404, detail="Section not found")
    return {section: USER_MANUAL[section]}


@router.get("/feature/{feature_id}")
async def get_feature_guide(feature_id: str):
    """Get guide for specific feature"""
    features = USER_MANUAL.get("features", {})
    
    if feature_id in features:
        return features[feature_id]
    
    # Check subfeatures
    for feature in features.values():
        if "subFeatures" in feature and feature_id in feature["subFeatures"]:
            return feature["subFeatures"][feature_id]
    
    raise HTTPException(status_code=404, detail="Feature guide not found")


@router.get("/search")
async def search_manual(q: str):
    """Search user manual"""
    results = []
    query = q.lower()
    
    def search_dict(d, path=""):
        for key, value in d.items():
            current_path = f"{path}/{key}" if path else key
            if isinstance(value, dict):
                search_dict(value, current_path)
            elif isinstance(value, str) and query in value.lower():
                results.append({
                    "path": current_path,
                    "content": value[:200],
                    "match": key
                })
            elif isinstance(value, list):
                for i, item in enumerate(value):
                    if isinstance(item, str) and query in item.lower():
                        results.append({
                            "path": f"{current_path}[{i}]",
                            "content": item[:200],
                            "match": key
                        })
    
    search_dict(USER_MANUAL)
    return {"results": results[:20], "query": q}


@router.get("/quick-start")
async def get_quick_start():
    """Get quick start guide"""
    return {
        "title": "Quick Start Guide",
        "steps": [
            {
                "step": 1,
                "title": "Create Your Account",
                "description": "Sign up with email or Google",
                "link": "/signup"
            },
            {
                "step": 2,
                "title": "Get Credits",
                "description": "Subscribe or purchase credits",
                "link": "/app/billing"
            },
            {
                "step": 3,
                "title": "Choose a Feature",
                "description": "Pick from our suite of AI tools",
                "link": "/app"
            },
            {
                "step": 4,
                "title": "Create & Download",
                "description": "Generate content and download",
                "link": None
            }
        ],
        "popularFeatures": [
            {"name": "Kids Story Generator", "link": "/app/stories"},
            {"name": "Reel Script Generator", "link": "/app/reel"},
            {"name": "Text to Image", "link": "/app/gen-studio/text-to-image"},
            {"name": "Tone Switcher", "link": "/app/tone-switcher"}
        ]
    }
