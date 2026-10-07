"""
NIA Agent package — OpenYabby-inspired agent architecture adapted for Android.

Inspired by:
  - OpenYabby's observe→plan→act→observe loop pattern (lib/agent-task-processor.js)
  - dejevu's Policy.decide() → validate → act sequence (dejevu/policy.py)

NOT copied from those projects. This is an Android-first Python adaptation.

Modules:
  planner   — intent classification and tool selection
  observer  — tool result validation and observation
  responder — final TTS-ready response generation
"""
from .planner import Planner, PlannerResult
from .observer import Observer, ObservationResult
from .responder import Responder

__all__ = [
    "Planner",
    "PlannerResult",
    "Observer",
    "ObservationResult",
    "Responder",
]
