"""
Story Universe Engine — Pydantic schemas for the entire pipeline.
Episode plans, scene motion plans, character continuity packages, cost estimation.
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


# ═══════════════════════════════════════════════════════════════
# JOB STATES — Truth-based, no fake completion
# ═══════════════════════════════════════════════════════════════

class JobState(str, Enum):
    INIT = "INIT"
    PLANNING = "PLANNING"
    BUILDING_CHARACTER_CONTEXT = "BUILDING_CHARACTER_CONTEXT"
    PLANNING_SCENE_MOTION = "PLANNING_SCENE_MOTION"
    GENERATING_KEYFRAMES = "GENERATING_KEYFRAMES"
    GENERATING_SCENE_CLIPS = "GENERATING_SCENE_CLIPS"
    GENERATING_AUDIO = "GENERATING_AUDIO"
    ASSEMBLING_VIDEO = "ASSEMBLING_VIDEO"
    VALIDATING = "VALIDATING"
    READY = "READY"
    PARTIAL_READY = "PARTIAL_READY"
    FAILED = "FAILED"


# ═══════════════════════════════════════════════════════════════
# EPISODE PLAN — Strict structured planning, no free-form text
# ═══════════════════════════════════════════════════════════════

class CharacterArc(BaseModel):
    character_name: str
    role: str  # protagonist, antagonist, supporting, narrator
    emotional_journey: str  # e.g. "hopeful → desperate → determined"
    key_actions: List[str]
    appearance_description: str  # clothing, features, build — for continuity
    voice_tone: str = "neutral"  # for TTS styling


class SceneBreakdown(BaseModel):
    scene_number: int
    location: str
    time_of_day: str  # dawn, morning, afternoon, dusk, night
    characters_present: List[str]
    action_summary: str  # what happens in 1-2 sentences
    dialogue: Optional[str] = None
    emotional_beat: str  # e.g. "tension builds", "relief", "shock"
    visual_style_notes: str  # e.g. "warm tones", "dutch angle", "close-up"
    estimated_duration_seconds: float = 5.0


class EpisodePlan(BaseModel):
    """Mandatory structured episode plan. No free-form text."""
    title: str
    episode_number: int = 1
    summary: str = Field(..., max_length=300)
    emotional_arc: str  # e.g. "curiosity → fear → hope → cliffhanger"
    scene_breakdown: List[SceneBreakdown] = Field(..., min_length=1, max_length=12)
    character_arcs: List[CharacterArc] = Field(..., min_length=1)
    cliffhanger: str = Field(..., max_length=200)
    visual_style_constraints: List[str]  # e.g. ["watercolor palette", "soft shadows"]
    negative_constraints: List[str]  # e.g. ["no gore", "no real celebrities"]
    narration_style: str = "dramatic"  # dramatic, calm, mysterious, playful
    target_total_duration_seconds: float = 30.0


# ═══════════════════════════════════════════════════════════════
# SCENE MOTION PLAN — Per-scene motion direction for video gen
# ═══════════════════════════════════════════════════════════════

class CameraMotion(str, Enum):
    STATIC = "static"
    PAN_LEFT = "pan_left"
    PAN_RIGHT = "pan_right"
    TILT_UP = "tilt_up"
    TILT_DOWN = "tilt_down"
    ZOOM_IN = "zoom_in"
    ZOOM_OUT = "zoom_out"
    DOLLY_IN = "dolly_in"
    DOLLY_OUT = "dolly_out"
    TRACKING = "tracking"
    ORBIT = "orbit"
    CRANE_UP = "crane_up"
    CRANE_DOWN = "crane_down"


class TransitionType(str, Enum):
    CUT = "cut"
    FADE = "fade"
    CROSSFADE = "crossfade"
    WIPE = "wipe"
    DISSOLVE = "dissolve"


class MotionIntensity(str, Enum):
    SUBTLE = "subtle"  # gentle sway, breathing
    MODERATE = "moderate"  # walking, gestures
    DYNAMIC = "dynamic"  # running, action
    INTENSE = "intense"  # explosion, chase


class SceneMotionPlan(BaseModel):
    """Mandatory per-scene motion plan for video generation."""
    scene_number: int
    action: str  # e.g. "character walks through forest"
    emotion: str  # e.g. "anxious", "peaceful"
    camera_motion: CameraMotion
    transition_type: TransitionType = TransitionType.CROSSFADE
    motion_intensity: MotionIntensity = MotionIntensity.MODERATE
    clip_duration_seconds: float = Field(5.0, ge=2.0, le=15.0)
    movement_notes: str = ""  # e.g. "wind blows hair, leaves fall"
    keyframe_prompt: str = ""  # exact prompt for keyframe generation
    video_prompt: str = ""  # exact prompt for clip generation


# ═══════════════════════════════════════════════════════════════
# CHARACTER CONTINUITY PACKAGE
# ═══════════════════════════════════════════════════════════════

class CharacterAppearance(BaseModel):
    """Locked visual traits for a character across episodes."""
    name: str
    gender: str
    age_range: str  # e.g. "20s", "elderly"
    build: str  # e.g. "slim", "athletic"
    hair: str  # e.g. "long black hair"
    eyes: str  # e.g. "bright green"
    skin_tone: str
    clothing_default: str  # e.g. "dark leather jacket, white shirt"
    distinguishing_features: str  # e.g. "scar on left cheek"
    reference_prompt: str  # full prompt to regenerate this character consistently
    reference_image_url: Optional[str] = None


class CharacterContinuityPackage(BaseModel):
    """Full continuity package for all characters in a story universe."""
    universe_id: str
    story_chain_id: str
    characters: List[CharacterAppearance]
    style_lock: str  # e.g. "watercolor, soft lighting, 16:9"
    color_palette: List[str]  # e.g. ["#2A1B3D", "#44318D", "#E98074"]
    environment_consistency: str  # e.g. "medieval village, cobblestone streets"
    locked_at: str  # ISO timestamp when these traits were locked


# ═══════════════════════════════════════════════════════════════
# COST ESTIMATION
# ═══════════════════════════════════════════════════════════════

class CostEstimate(BaseModel):
    """Pre-flight cost estimation before generation starts."""
    total_credits_required: int
    breakdown: Dict[str, int]  # e.g. {"planning": 1, "keyframes": 5, "clips": 10, "audio": 2, "assembly": 2}
    user_current_credits: int
    sufficient: bool
    shortfall: int = 0  # how many more credits needed


# ═══════════════════════════════════════════════════════════════
# JOB DOCUMENT — Full pipeline job state
# ═══════════════════════════════════════════════════════════════

class StageResult(BaseModel):
    """Result of a single pipeline stage."""
    stage: str
    status: str  # success, failed, skipped
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_seconds: Optional[float] = None
    credits_consumed: int = 0
    error: Optional[str] = None
    output_artifacts: Dict[str, Any] = {}


class PipelineJob(BaseModel):
    """Full pipeline job document."""
    job_id: str
    user_id: str
    state: JobState = JobState.INIT
    # Input
    story_text: str
    title: str = "Untitled"
    style_id: str = "cartoon_2d"
    language: str = "en"
    age_group: str = "teens"
    # Chain info
    story_chain_id: Optional[str] = None
    parent_job_id: Optional[str] = None
    episode_number: int = 1
    # Plans
    episode_plan: Optional[Dict] = None
    character_continuity: Optional[Dict] = None
    scene_motion_plans: Optional[List[Dict]] = None
    # Outputs
    keyframe_urls: List[str] = []
    scene_clip_urls: List[str] = []
    narration_url: Optional[str] = None
    output_url: Optional[str] = None
    preview_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    # Cost tracking
    cost_estimate: Optional[Dict] = None
    total_credits_consumed: int = 0
    credits_refunded: int = 0
    # Stage results
    stage_results: List[Dict] = []
    # Meta
    is_seed_content: bool = False
    public: bool = False
    slug: Optional[str] = None
    created_at: str = ""
    updated_at: str = ""
    completed_at: Optional[str] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 2


# ═══════════════════════════════════════════════════════════════
# API REQUEST/RESPONSE MODELS
# ═══════════════════════════════════════════════════════════════

class CreateStoryRequest(BaseModel):
    story_text: str = Field(..., min_length=10, max_length=5000)
    title: Optional[str] = None
    style_id: str = "cartoon_2d"
    language: str = "en"
    age_group: str = "teens"
    parent_job_id: Optional[str] = None  # for continuations
    story_chain_id: Optional[str] = None


class CreditCheckResponse(BaseModel):
    sufficient: bool
    required: int
    current: int
    shortfall: int = 0


class JobStatusResponse(BaseModel):
    job_id: str
    state: str
    progress_percent: int = 0
    current_stage: str = ""
    stage_results: List[Dict] = []
    output_url: Optional[str] = None
    preview_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    error_message: Optional[str] = None
    credits_consumed: int = 0
