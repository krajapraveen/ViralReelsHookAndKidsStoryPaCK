"""
Model Router — Config-driven tiered routing for comic generation.
Decides which model tier to use based on input risk and failure classification.
Tier = logical routing abstraction, NOT hardcoded provider identity.
"""
import logging
from typing import List, Optional

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from enums.pipeline_enums import (
    FailureType, ModelTier, RepairMode, RepairStrategy, RiskBucket,
    ValidationResult, FailureClass,
    MODEL_TIER_MAPPING, RISK_BUCKET_ROUTING, FAILURE_REPAIR_ROUTING,
    REPAIR_TRIGGER_SEVERITY, FALLBACK_TRIGGER_SEVERITY,
)

logger = logging.getLogger("creatorstudio.comic_pipeline.model_router")


class ModelRouter:
    """
    Routes panel generation to the appropriate model tier.
    All decisions are config-driven and explainable.
    """

    def choose_initial_tier(self, risk_bucket: RiskBucket) -> ModelTier:
        """Choose the initial model tier based on input risk classification."""
        tier = RISK_BUCKET_ROUTING.get(risk_bucket, ModelTier.TIER1_QUALITY)
        logger.info(f"[ROUTER] Initial tier for risk={risk_bucket.value}: {tier.value}")
        return tier

    def choose_repair_strategy(
        self,
        validation: ValidationResult,
        risk_bucket: RiskBucket = RiskBucket.MEDIUM,
    ) -> RepairStrategy:
        """
        Choose repair strategy based on validation result.
        Decision logic:
          1. Hard failure → R4 degraded fallback
          2. Severity >= 0.85 → R4 degraded fallback
          3. Structural failure → R3 structural repair
          4. Soft failure with specific type → look up FAILURE_REPAIR_ROUTING
          5. Default → R2 prompt + model
        """
        # Hard failures go straight to fallback
        if validation.failure_class == FailureClass.HARD:
            logger.info("[ROUTER] Hard failure detected → R4 degraded fallback")
            return RepairStrategy(
                repair_mode=RepairMode.R4_DEGRADED_FALLBACK,
                model_tier=ModelTier.TIER4_SAFE_DEGRADED,
                degraded=True,
            )

        # Very high severity → fallback
        if validation.severity >= FALLBACK_TRIGGER_SEVERITY:
            logger.info(f"[ROUTER] Severity {validation.severity} >= {FALLBACK_TRIGGER_SEVERITY} → R4 fallback")
            return RepairStrategy(
                repair_mode=RepairMode.R4_DEGRADED_FALLBACK,
                model_tier=ModelTier.TIER4_SAFE_DEGRADED,
                degraded=True,
            )

        # Structural failures
        if validation.failure_class == FailureClass.STRUCTURAL:
            logger.info("[ROUTER] Structural failure → R3 structural repair with Tier 3")
            return RepairStrategy(
                repair_mode=RepairMode.R3_STRUCTURAL_REPAIR,
                model_tier=ModelTier.TIER3_DETERMINISTIC,
            )

        # Soft failures — route by most critical failure type
        priority_order = [
            FailureType.FACE_DRIFT,
            FailureType.LOW_SOURCE_SIMILARITY,
            FailureType.STYLE_DRIFT,
            FailureType.STORY_MISMATCH,
            FailureType.CONTINUITY_BREAK,
            FailureType.COMPOSITION_CLUTTER,
        ]

        for ft in priority_order:
            if ft in validation.failure_types:
                strategy = FAILURE_REPAIR_ROUTING.get(ft)
                if strategy:
                    logger.info(f"[ROUTER] {ft.value} detected → {strategy.repair_mode.value} with {strategy.model_tier.value}")
                    return strategy

        # Default: prompt + model repair
        logger.info("[ROUTER] Default repair → R2 with Tier 2")
        return RepairStrategy(
            repair_mode=RepairMode.R2_PROMPT_PLUS_MODEL,
            model_tier=ModelTier.TIER2_STABLE_CHARACTER,
        )

    def get_provider_config(self, tier: ModelTier) -> dict:
        """Get the actual provider/model config for a logical tier."""
        config = MODEL_TIER_MAPPING.get(tier, MODEL_TIER_MAPPING[ModelTier.TIER1_QUALITY])
        return {
            "provider": config["provider"],
            "model": config["model"],
            "tier": tier.value,
            "description": config["description"],
        }

    def explain_routing_decision(
        self,
        tier_chosen: ModelTier,
        reason: str,
        failure_types: Optional[List[FailureType]] = None,
        risk_bucket: Optional[RiskBucket] = None,
    ) -> str:
        """Generate a human-readable routing explanation for admin diagnostics."""
        config = self.get_provider_config(tier_chosen)
        parts = [
            f"Routed to {tier_chosen.value} ({config['model']})",
            f"Reason: {reason}",
        ]
        if failure_types:
            parts.append(f"Failure types: {[ft.value for ft in failure_types]}")
        if risk_bucket:
            parts.append(f"Input risk: {risk_bucket.value}")
        return " | ".join(parts)
