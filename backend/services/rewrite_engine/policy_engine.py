"""
Policy Engine — ALLOW / REWRITE / BLOCK decision logic.

Severity tiers:
  ALLOW   — nothing detected, pass through unchanged.
  REWRITE — trademark/IP/celebrity/franchise detected, rewrite to safe generic.
  BLOCK   — genuinely dangerous content (CSAM, graphic violence instructions,
             direct deepfake of real minors). Only blocks when rewrite is impossible.
"""
import re
import logging
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Optional

logger = logging.getLogger("safety.policy_engine")


class Decision(str, Enum):
    ALLOW = "ALLOW"
    REWRITE = "REWRITE"
    BLOCK = "BLOCK"


@dataclass
class PolicyResult:
    decision: Decision
    reason_codes: List[str] = field(default_factory=list)
    block_reason: str = ""
    triggered_rules: List[str] = field(default_factory=list)

    def to_dict(self):
        return {
            "decision": self.decision.value,
            "reason_codes": self.reason_codes,
            "block_reason": self.block_reason,
            "triggered_rules": self.triggered_rules,
        }


# ═══════════════════════════════════════════════════════════════
# HARD-BLOCK PATTERNS — genuinely dangerous, never rewritable.
# Keep this list tight. False positives kill UX.
# ═══════════════════════════════════════════════════════════════
_BLOCK_PATTERNS = [
    (re.compile(r"\b(child|kid|minor|underage|teen)\b.*\b(nude|naked|sexual|erotic|porn)", re.I),
     "CSAM_RISK", "Content involving minors in sexual context is not allowed."),
    (re.compile(r"\b(nude|naked|sexual|erotic|porn)\b.*\b(child|kid|minor|underage|teen)\b", re.I),
     "CSAM_RISK", "Content involving minors in sexual context is not allowed."),
    (re.compile(r"\b(how to|tutorial|guide|instructions)\b.*\b(make|build|create)\b.*\b(bomb|explosive|weapon|poison)\b", re.I),
     "VIOLENCE_INSTRUCT", "Instructions for creating weapons or explosives are not allowed."),
    (re.compile(r"\b(deepfake|face\s*swap)\b.*\b(real|actual)\b.*\b(person|child|kid|minor)\b", re.I),
     "DEEPFAKE_REAL_PERSON", "Creating deepfakes of real people is not allowed."),
]


def evaluate_policy(text: str, has_trademark_hits: bool = False) -> PolicyResult:
    """
    Evaluate a single text input against the policy engine.

    Args:
        text: The user-supplied text to evaluate.
        has_trademark_hits: Whether the rewrite engine found trademark/IP terms.

    Returns:
        PolicyResult with decision + metadata.
    """
    if not text or not text.strip():
        return PolicyResult(decision=Decision.ALLOW)

    # 1. Check hard-block patterns first
    for pattern, code, message in _BLOCK_PATTERNS:
        if pattern.search(text):
            logger.warning(f"[POLICY BLOCK] Rule={code} text={text[:80]!r}")
            return PolicyResult(
                decision=Decision.BLOCK,
                reason_codes=[code],
                block_reason=message,
                triggered_rules=[code],
            )

    # 2. If rewrite engine found trademark/IP → REWRITE
    if has_trademark_hits:
        return PolicyResult(
            decision=Decision.REWRITE,
            reason_codes=["TRADEMARK_IP"],
            triggered_rules=["TRADEMARK_IP"],
        )

    # 3. Clean — ALLOW
    return PolicyResult(decision=Decision.ALLOW)


def evaluate_policy_batch(texts: dict, trademark_flags: dict) -> PolicyResult:
    """
    Evaluate multiple text fields. Returns the strictest decision.
    If ANY field is BLOCK → overall BLOCK.
    If ANY field is REWRITE → overall REWRITE.
    """
    overall = PolicyResult(decision=Decision.ALLOW)

    for field_name, text in texts.items():
        has_tm = trademark_flags.get(field_name, False)
        result = evaluate_policy(text, has_tm)

        if result.decision == Decision.BLOCK:
            return result  # Immediate exit on BLOCK

        if result.decision == Decision.REWRITE:
            overall.decision = Decision.REWRITE
            overall.reason_codes.extend(result.reason_codes)
            overall.triggered_rules.extend(result.triggered_rules)

    return overall
