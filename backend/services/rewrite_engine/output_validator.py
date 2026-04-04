"""
Output Validator — post-generation safety check.

Scans generated text (titles, captions, narration scripts) for
trademark/IP terms that may have leaked through the generation model
despite clean prompts. Re-rewrites if found.
"""
import logging
from typing import Dict, Optional
from dataclasses import dataclass, field

from .rule_rewriter import rewrite_text, has_risky_terms

logger = logging.getLogger("safety.output_validator")


@dataclass
class ValidationResult:
    """Result of output validation."""
    is_clean: bool
    original_output: str
    validated_output: str
    leaked_terms: int = 0
    changes: list = field(default_factory=list)
    action_taken: str = "none"  # "none", "rewritten", "flagged"

    def to_dict(self):
        return {
            "is_clean": self.is_clean,
            "leaked_terms": self.leaked_terms,
            "action_taken": self.action_taken,
            "changes_count": len(self.changes),
        }


def validate_output(text: str) -> ValidationResult:
    """
    Validate a single generated output for leaked IP/trademark terms.
    If found, re-rewrite them. Never block — always deliver usable output.
    """
    if not text or not text.strip():
        return ValidationResult(
            is_clean=True,
            original_output=text or "",
            validated_output=text or "",
        )

    if not has_risky_terms(text):
        return ValidationResult(
            is_clean=True,
            original_output=text,
            validated_output=text,
        )

    # Found leaked terms — re-rewrite
    rewritten, changes = rewrite_text(text)
    logger.info(
        f"[OUTPUT VALIDATION] Re-rewrote {len(changes)} leaked term(s) in output: "
        + ", ".join(f"'{c['original']}'" for c in changes[:5])
    )

    return ValidationResult(
        is_clean=False,
        original_output=text,
        validated_output=rewritten,
        leaked_terms=len(changes),
        changes=changes,
        action_taken="rewritten",
    )


def validate_output_fields(**fields: str) -> Dict[str, ValidationResult]:
    """
    Validate multiple output fields at once.
    Usage: results = validate_output_fields(title="...", narration="...")
    """
    return {name: validate_output(text) for name, text in fields.items()}


def validate_and_clean(text: str) -> str:
    """
    Convenience: validate and return clean text directly.
    For use in pipelines where you just need the cleaned output string.
    """
    result = validate_output(text)
    return result.validated_output
