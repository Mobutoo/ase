"""
Phase 5 model definitions — AI Copilot via n8n / OpenClaw.

AISuggestion is defined directly in app.models (colocated with the rest of the
domain models). This module re-exports it so that Phase 5 code can import from
a single, self-describing location:

    from app.models_phase5 import AISuggestion

Both import paths resolve to the same class — no duplication.
"""
from app.models import AISuggestion, AI_SUGGESTION_TYPE_CHOICES  # noqa: F401

__all__ = ["AISuggestion", "AI_SUGGESTION_TYPE_CHOICES"]
