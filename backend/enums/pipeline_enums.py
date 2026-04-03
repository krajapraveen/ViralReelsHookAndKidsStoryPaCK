"""
Pipeline Enums & Shared Contracts for Photo-to-Comic Smart Repair System.
These are the canonical types that every module in the pipeline imports.
"""
from enum import Enum
from pydantic import BaseModel, Field
from typing import List, Optional, Dict


# ══════════════════════════════════════════════════════════════════════════════
# ENUMS
# ══════════════════════════════════════════════════════════════════════════════

class FailureClass(str, Enum):
    HARD = "HARD"
    SOFT = "SOFT"
    STRUCTURAL = "STRUCTURAL"


class FailureType(str, Enum):
    # Hard failures
    HARD_FAIL = "hard_fail"
    EMPTY_OUTPUT = "empty_output"
    CORRUPT_ASSET = "corrupt_asset"
    PROVIDER_TIMEOUT = "provider_timeout"
    SAFETY_BLOCK = "safety_block"

    # Soft failures
    FACE_DRIFT = "face_drift"
    STYLE_DRIFT = "style_drift"
    LOW_SOURCE_SIMILARITY = "low_source_similarity"
    COMPOSITION_CLUTTER = "composition_clutter"
    ANATOMY_DISTORTION = "anatomy_distortion"

    # Structural failures
    STORY_MISMATCH = "story_mismatch"
    CONTINUITY_BREAK = "continuity_break"
    CHARACTER_COUNT_MISMATCH = "character_count_mismatch"


class ModelTier(str, Enum):
    """Logical routing abstraction — NOT hardcoded provider identity."""
    TIER1_QUALITY = "tier1_quality"
    TIER2_STABLE_CHARACTER = "tier2_stable_character"
    TIER3_DETERMINISTIC = "tier3_deterministic"
    TIER4_SAFE_DEGRADED = "tier4_safe_degraded"


class RepairMode(str, Enum):
    R1_PROMPT_ONLY = "R1_PROMPT_ONLY"
    R2_PROMPT_PLUS_MODEL = "R2_PROMPT_PLUS_MODEL"
    R3_STRUCTURAL_REPAIR = "R3_STRUCTURAL_REPAIR"
    R4_DEGRADED_FALLBACK = "R4_DEGRADED_FALLBACK"


class PipelineState(str, Enum):
    INPUT_ANALYSIS = "INPUT_ANALYSIS"
    PLANNING = "PLANNING"
    GENERATING = "GENERATING"
    VALIDATING = "VALIDATING"
    REPAIRING = "REPAIRING"
    JOB_FALLBACK = "JOB_FALLBACK"
    FINALIZING = "FINALIZING"
    FINALIZED = "FINALIZED"


class PanelStatus(str, Enum):
    QUEUED = "QUEUED"
    GENERATING_PRIMARY = "GENERATING_PRIMARY"
    VALIDATING = "VALIDATING"
    PASSED = "PASSED"
    REPAIR_NEEDED = "REPAIR_NEEDED"
    REPAIRING = "REPAIRING"
    PASSED_REPAIRED = "PASSED_REPAIRED"
    FALLBACK_REQUIRED = "FALLBACK_REQUIRED"
    PASSED_DEGRADED = "PASSED_DEGRADED"
    FAILED = "FAILED"


class RiskBucket(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    EXTREME = "EXTREME"


# ══════════════════════════════════════════════════════════════════════════════
# SHARED CONTRACTS (Data models used across modules)
# ══════════════════════════════════════════════════════════════════════════════

class PanelScores(BaseModel):
    """Per-panel validation scores, all 0-1 normalized."""
    source_similarity: float = 0.0
    face_consistency: float = 0.0
    style_consistency: float = 0.0
    story_alignment: float = 0.0
    visual_clarity: float = 0.0
    composition: float = 0.0


class InputRiskProfile(BaseModel):
    face_count: int = 0
    face_visibility: float = 0.0
    blur_score: float = 0.0
    lighting_score: float = 0.0
    occlusion_score: float = 0.0
    pose_extremity: float = 0.0
    background_noise: float = 0.0
    crop_quality: float = 0.0
    risk_bucket: RiskBucket = RiskBucket.MEDIUM


class ValidationResult(BaseModel):
    pass_status: bool = False
    fallback_acceptable: bool = False
    failure_types: List[FailureType] = Field(default_factory=list)
    failure_class: Optional[FailureClass] = None
    severity: float = 0.0
    scores: PanelScores = Field(default_factory=PanelScores)
    validator_summary: Dict[str, str] = Field(default_factory=dict)


class RepairStrategy(BaseModel):
    repair_mode: RepairMode
    model_tier: ModelTier
    max_attempts: int = 1
    degraded: bool = False


class PanelPlan(BaseModel):
    panel_index: int
    story_beat: str = ""
    action: str = ""
    emotion: str = ""
    camera_hint: Optional[str] = None
    environment_hint: Optional[str] = None


class AttemptPayload(BaseModel):
    """Structured payload for every generation/repair/fallback attempt."""
    job_id: str
    panel_index: int
    attempt_number: int
    stage: str  # PRIMARY, REPAIR_R1, REPAIR_R2, etc.
    attempt_type: str  # "primary", "repair", "fallback"
    trigger_reason: List[str] = Field(default_factory=list)
    model_tier: str = ""
    provider_model: str = ""
    prompt_hash: str = ""
    repair_mode: Optional[str] = None
    latency_ms: int = 0
    scores: Optional[PanelScores] = None
    failure_types_in: List[str] = Field(default_factory=list)
    failure_types_out: List[str] = Field(default_factory=list)
    severity_in: float = 0.0
    severity_out: float = 0.0
    accepted: bool = False
    asset_url: Optional[str] = None
    error_type: Optional[str] = None
    error_message: Optional[str] = None


class CharacterLock(BaseModel):
    """Lightweight character identity bundle."""
    source_face_detected: bool = False
    visual_traits: Dict[str, str] = Field(default_factory=dict)
    style_traits: Dict[str, str] = Field(default_factory=dict)
    approved_panels: List[int] = Field(default_factory=list)


# ══════════════════════════════════════════════════════════════════════════════
# THRESHOLDS (Centralized, config-driven)
# ══════════════════════════════════════════════════════════════════════════════

PASS_THRESHOLDS = {
    "source_similarity": 0.72,
    "face_consistency": 0.75,
    "style_consistency": 0.75,
    "story_alignment": 0.78,
    "visual_clarity": 0.70,
    "composition": 0.68,
}

FALLBACK_THRESHOLDS = {
    "source_similarity": 0.60,
    "face_consistency": 0.62,
    "style_consistency": 0.60,
    "story_alignment": 0.72,
    "visual_clarity": 0.70,
    "composition": 0.65,
}

REPAIR_TRIGGER_SEVERITY = 0.45
FALLBACK_TRIGGER_SEVERITY = 0.85

# Hard caps (non-negotiable)
MAX_PRIMARY_ATTEMPTS = 1
MAX_REPAIR_ATTEMPTS = 1
MAX_FALLBACK_ATTEMPTS = 1
MAX_TOTAL_ATTEMPTS_PER_PANEL = 3

# Model tier → provider mapping (logical abstraction, swappable)
MODEL_TIER_MAPPING = {
    ModelTier.TIER1_QUALITY: {
        "provider": "gemini",
        "model": "gemini-3-pro-image-preview",
        "description": "High aesthetic quality, premium feel",
    },
    ModelTier.TIER2_STABLE_CHARACTER: {
        "provider": "gemini",
        "model": "gemini-3-pro-image-preview",
        "description": "Same provider, face-anchored prompts for identity preservation",
    },
    ModelTier.TIER3_DETERMINISTIC: {
        "provider": "gemini",
        "model": "gemini-3.1-flash-image-preview",
        "description": "Faster, more deterministic, stronger instruction following",
    },
    ModelTier.TIER4_SAFE_DEGRADED: {
        "provider": "gemini",
        "model": "gemini-3.1-flash-image-preview",
        "description": "Simplified prompts, maximum continuity, minimal failure risk",
    },
}

# Risk bucket → initial tier mapping
RISK_BUCKET_ROUTING = {
    RiskBucket.LOW: ModelTier.TIER1_QUALITY,
    RiskBucket.MEDIUM: ModelTier.TIER1_QUALITY,
    RiskBucket.HIGH: ModelTier.TIER2_STABLE_CHARACTER,
    RiskBucket.EXTREME: ModelTier.TIER2_STABLE_CHARACTER,
}

# Failure type → repair routing
FAILURE_REPAIR_ROUTING = {
    FailureType.FACE_DRIFT: RepairStrategy(
        repair_mode=RepairMode.R2_PROMPT_PLUS_MODEL,
        model_tier=ModelTier.TIER2_STABLE_CHARACTER,
    ),
    FailureType.STYLE_DRIFT: RepairStrategy(
        repair_mode=RepairMode.R2_PROMPT_PLUS_MODEL,
        model_tier=ModelTier.TIER2_STABLE_CHARACTER,
    ),
    FailureType.LOW_SOURCE_SIMILARITY: RepairStrategy(
        repair_mode=RepairMode.R2_PROMPT_PLUS_MODEL,
        model_tier=ModelTier.TIER2_STABLE_CHARACTER,
    ),
    FailureType.STORY_MISMATCH: RepairStrategy(
        repair_mode=RepairMode.R3_STRUCTURAL_REPAIR,
        model_tier=ModelTier.TIER3_DETERMINISTIC,
    ),
    FailureType.CONTINUITY_BREAK: RepairStrategy(
        repair_mode=RepairMode.R3_STRUCTURAL_REPAIR,
        model_tier=ModelTier.TIER3_DETERMINISTIC,
    ),
    FailureType.COMPOSITION_CLUTTER: RepairStrategy(
        repair_mode=RepairMode.R1_PROMPT_ONLY,
        model_tier=ModelTier.TIER1_QUALITY,
    ),
    FailureType.HARD_FAIL: RepairStrategy(
        repair_mode=RepairMode.R4_DEGRADED_FALLBACK,
        model_tier=ModelTier.TIER4_SAFE_DEGRADED,
        degraded=True,
    ),
    FailureType.EMPTY_OUTPUT: RepairStrategy(
        repair_mode=RepairMode.R4_DEGRADED_FALLBACK,
        model_tier=ModelTier.TIER4_SAFE_DEGRADED,
        degraded=True,
    ),
    FailureType.PROVIDER_TIMEOUT: RepairStrategy(
        repair_mode=RepairMode.R4_DEGRADED_FALLBACK,
        model_tier=ModelTier.TIER3_DETERMINISTIC,
        degraded=True,
    ),
}

# User-facing pipeline state messaging (calm only)
PIPELINE_STATE_MESSAGES = {
    PipelineState.INPUT_ANALYSIS: "Analyzing your photo for the best comic result...",
    PipelineState.PLANNING: "Planning your comic story flow...",
    PipelineState.GENERATING: "Creating your comic panels...",
    PipelineState.VALIDATING: "Reviewing visual consistency...",
    PipelineState.REPAIRING: "Enhancing a few panels for smoother storytelling...",
    PipelineState.JOB_FALLBACK: "Optimizing your comic for a cleaner final result...",
    PipelineState.FINALIZING: "Finalizing your comic assets...",
    PipelineState.FINALIZED: "Your comic is ready!",
}
