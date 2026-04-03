"""
Rewrite Service — Orchestrator for the Safe Rewrite Engine.
detect -> rewrite -> continue. Never block for ordinary trademark/copyright.
"""
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass, field

from .rule_rewriter import rewrite_text, has_risky_terms

logger = logging.getLogger("rewrite_engine")


@dataclass
class RewriteResult:
    """Result of a safe rewrite operation."""
    original_text: str
    rewritten_text: str
    was_rewritten: bool
    changes: List[Dict] = field(default_factory=list)
    user_note: str = ""

    def to_dict(self) -> Dict:
        return {
            "original_text": self.original_text,
            "rewritten_text": self.rewritten_text,
            "was_rewritten": self.was_rewritten,
            "changes_count": len(self.changes),
            "user_note": self.user_note,
        }


def safe_rewrite(text: str) -> RewriteResult:
    """
    Core entry point: rewrite risky terms in text.
    NEVER raises an exception for trademark/copyright content.
    Always returns usable text.
    """
    if not text or not text.strip():
        return RewriteResult(
            original_text=text or "",
            rewritten_text=text or "",
            was_rewritten=False,
        )

    rewritten, changes = rewrite_text(text)

    was_rewritten = len(changes) > 0
    user_note = ""
    if was_rewritten:
        user_note = "We adjusted a few words to keep your story original and generation-ready."
        logger.info(
            f"[REWRITE] Rewrote {len(changes)} term(s): "
            + ", ".join(f"'{c['original']}' -> '{c['replacement']}'" for c in changes[:5])
        )

    return RewriteResult(
        original_text=text,
        rewritten_text=rewritten,
        was_rewritten=was_rewritten,
        changes=changes,
        user_note=user_note,
    )


def safe_rewrite_fields(**fields: str) -> Dict[str, RewriteResult]:
    """
    Rewrite multiple named text fields at once.
    Returns dict of field_name -> RewriteResult.
    Usage: results = safe_rewrite_fields(title="My Marvel Story", story="...")
    """
    return {name: safe_rewrite(text) for name, text in fields.items()}
