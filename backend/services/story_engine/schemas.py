"""
Story Universe Engine — Pydantic schemas for the entire pipeline.
Episode plans, scene motion plans, character continuity packages, cost estimation.
Structured error codes and per-stage failure states.
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


# ═══════════════════════════════════════════════════════════════
# STRUCTURED ERROR CODES — No vague text. Every failure is classified.
# ═══════════════════════════════════════════════════════════════

class ErrorCode(str, Enum):
    BUDGET_EXCEEDED_PRECHECK = "BUDGET_EXCEEDED_PRECHECK"
    BUDGET_EXCEEDED_RUNTIME = "BUDGET_EXCEEDED_RUNTIME"
    MODEL_TIMEOUT = "MODEL_TIMEOUT"
    MODEL_INVALID_RESPONSE = "MODEL_INVALID_RESPONSE"
    SCENE_GENERATION_FAILED = "SCENE_GENERATION_FAILED"
    IMAGE_GENERATION_FAILED = "IMAGE_GENERATION_FAILED"
    TTS_GENERATION_FAILED = "TTS_GENERATION_FAILED"
    RENDER_FAILED = "RENDER_FAILED"
    JOB_HEARTBEAT_EXPIRED = "JOB_HEARTBEAT_EXPIRED"
    WORKER_CRASH = "WORKER_CRASH"
    UNKNOWN_STAGE_FAILURE = "UNKNOWN_STAGE_FAILURE"
    CONTENT_VIOLATION = "CONTENT_VIOLATION"
    INSUFFICIENT_CREDITS = "INSUFFICIENT_CREDITS"
    INPUT_TOO_LARGE = "INPUT_TOO_LARGE"
    ASSET_MISSING = "ASSET_MISSING"
    RENDER_ASSET_NOT_FOUND = "RENDER_ASSET_NOT_FOUND"
    TIMELINE_BUILD_FAILED = "TIMELINE_BUILD_FAILED"


# ═══════════════════════════════════════════════════════════════
# JOB STATES — Per-stage failure states for recovery + honest UI
# ═══════════════════════════════════════════════════════════════

class JobState(str, Enum):
    INIT = "INIT"
    QUEUED = "QUEUED"
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
    # Per-stage terminal failure states
    FAILED_PLANNING = "FAILED_PLANNING"
    FAILED_IMAGES = "FAILED_IMAGES"
    FAILED_TTS = "FAILED_TTS"
    FAILED_RENDER = "FAILED_RENDER"
    # Lifecycle states
    FAILED_PERSISTENCE = "FAILED_PERSISTENCE"
    EXPIRED = "EXPIRED"
    # Generic/legacy terminal failure
    FAILED = "FAILED"


# Sets for quick membership checks
TERMINAL_STATES = {
    JobState.READY, JobState.PARTIAL_READY, JobState.FAILED,
    JobState.FAILED_PLANNING, JobState.FAILED_IMAGES,
    JobState.FAILED_TTS, JobState.FAILED_RENDER,
    JobState.FAILED_PERSISTENCE, JobState.EXPIRED,
}

SUCCESS_STATES = {JobState.READY, JobState.PARTIAL_READY}

ACTIVE_STATES = {
    JobState.INIT, JobState.PLANNING, JobState.BUILDING_CHARACTER_CONTEXT,
    JobState.PLANNING_SCENE_MOTION, JobState.GENERATING_KEYFRAMES,
    JobState.GENERATING_SCENE_CLIPS, JobState.GENERATING_AUDIO,
    JobState.ASSEMBLING_VIDEO, JobState.VALIDATING,
}

PER_STAGE_FAILURE_STATES = {
    JobState.FAILED_PLANNING, JobState.FAILED_IMAGES,
    JobState.FAILED_TTS, JobState.FAILED_RENDER,
}


# ═══════════════════════════════════════════════════════════════
# EPISODE PLAN — Strict structured planning, no free-form text
# ═══════════════════════════════════════════════════════════════

class CharacterArc(BaseModel):
    character_name: str
    role: str
    emotional_journey: str
    key_actions: List[str]
    appearance_description: str
    voice_tone: str = "neutral"


class SceneBreakdown(BaseModel):
    scene_number: int
    location: str
    time_of_day: str
    characters_present: List[str]
    action_summary: str
    dialogue: Optional[str] = None
    emotional_beat: str
    visual_style_notes: str
    estimated_duration_seconds: float = 5.0


class EpisodePlan(BaseModel):
    title: str
    episode_number: int = 1
    summary: str = Field(..., max_length=300)
    emotional_arc: str
    scene_breakdown: List[SceneBreakdown] = Field(..., min_length=1, max_length=12)
    character_arcs: List[CharacterArc] = Field(..., min_length=1)
    cliffhanger: str = Field(..., max_length=200)
    visual_style_constraints: List[str]
    negative_constraints: List[str]
    narration_style: str = "dramatic"
    target_total_duration_seconds: float = 30.0


# ═══════════════════════════════════════════════════════════════
# SCENE MOTION PLAN
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
    SUBTLE = "subtle"
    MODERATE = "moderate"
    DYNAMIC = "dynamic"
    INTENSE = "intense"


class SceneMotionPlan(BaseModel):
    scene_number: int
    action: str
    emotion: str
    camera_motion: CameraMotion
    transition_type: TransitionType = TransitionType.CROSSFADE
    motion_intensity: MotionIntensity = MotionIntensity.MODERATE
    clip_duration_seconds: float = Field(5.0, ge=2.0, le=15.0)
    movement_notes: str = ""
    keyframe_prompt: str = ""
    video_prompt: str = ""


# ═══════════════════════════════════════════════════════════════
# CHARACTER CONTINUITY PACKAGE
# ═══════════════════════════════════════════════════════════════

class CharacterAppearance(BaseModel):
    name: str
    gender: str
    age_range: str
    build: str
    hair: str
    eyes: str
    skin_tone: str
    clothing_default: str
    distinguishing_features: str
    reference_prompt: str
    reference_image_url: Optional[str] = None


class CharacterContinuityPackage(BaseModel):
    universe_id: str
    story_chain_id: str
    characters: List[CharacterAppearance]
    style_lock: str
    color_palette: List[str]
    environment_consistency: str
    locked_at: str


# ═══════════════════════════════════════════════════════════════
# COST ESTIMATION
# ═══════════════════════════════════════════════════════════════

class CostEstimate(BaseModel):
    total_credits_required: int
    breakdown: Dict[str, int]
    user_current_credits: int
    sufficient: bool
    shortfall: int = 0


# ═══════════════════════════════════════════════════════════════
# JOB DOCUMENT — Full pipeline job state
# ═══════════════════════════════════════════════════════════════

class StageResult(BaseModel):
    stage: str
    status: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_seconds: Optional[float] = None
    credits_consumed: int = 0
    error: Optional[str] = None
    error_code: Optional[str] = None
    attempt_number: int = 1
    model_used: Optional[str] = None
    output_artifacts: Dict[str, Any] = {}


class PipelineJob(BaseModel):
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
    # Reliability tracking
    retry_count: int = 0
    max_retries: int = 3
    last_heartbeat_at: Optional[str] = None
    last_error_code: Optional[str] = None
    last_error_message: Optional[str] = None
    last_error_stage: Optional[str] = None
    stage_retry_counts: Dict[str, int] = {}
    # Meta
    is_seed_content: bool = False
    public: bool = False
    slug: Optional[str] = None
    created_at: str = ""
    updated_at: str = ""
    completed_at: Optional[str] = None
    error_message: Optional[str] = None


# ═══════════════════════════════════════════════════════════════
# API REQUEST/RESPONSE MODELS
# ═══════════════════════════════════════════════════════════════

class CreateStoryRequest(BaseModel):
    story_text: str = Field(..., min_length=10, max_length=5000)
    title: Optional[str] = None
    style_id: str = "cartoon_2d"
    language: str = "en"
    age_group: str = "teens"
    parent_job_id: Optional[str] = None
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
    error_code: Optional[str] = None
    credits_consumed: int = 0
    credits_refunded: int = 0
    retry_count: int = 0
    can_retry: bool = False
