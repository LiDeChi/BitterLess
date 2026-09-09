"""Shared types and enums for the Eastern Zhou lab kernel."""

from __future__ import annotations

from enum import Enum
from typing import Any


class FocusDim(str, Enum):
    """Dimensions along which the institute may raise resolution."""

    PERSON = "person"
    RELATION = "relation"
    MEDIUM = "medium"
    BEHAVIOR = "behavior"
    INSTITUTION = "institution"
    TIME = "time"
    ECONOMY = "economy"


class ResolutionLevel(str, Enum):
    """Resolution ladder. Demotion never deletes people."""

    NONE = "none"  # lifecycle stub only
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    ULTRA = "ultra"


class CompressionTier(str, Enum):
    """Character-internal media compression ladder."""

    RAW = "raw"
    EVENT = "event"
    EPISODE = "episode"
    PATTERN = "pattern"
    BELIEF = "belief"


class TimelineKind(str, Enum):
    CANONICAL = "canonical"
    EXPERIMENTAL = "experimental"
    SANDBOX = "sandbox"


class ProvenanceKind(str, Enum):
    """How a detail entered the record."""

    COMPUTED = "computed"  # actually simulated at the time
    HARD_FACT = "hard_fact"  # seed / canonical constraint
    RECONSTRUCTION = "reconstruction"  # remanifested; must be marked
    HYPOTHESIS = "hypothesis"  # institute speculation, not world fact


class InterventionKind(str, Enum):
    CHALLENGE_HYPOTHESIS = "challenge_hypothesis"
    CHANGE_FOCUS = "change_focus"
    NOTE = "note"


def as_dict(obj: Any) -> dict[str, Any]:
    if hasattr(obj, "to_dict"):
        return obj.to_dict()
    if isinstance(obj, Enum):
        return {"value": obj.value}
    raise TypeError(f"Cannot serialize {type(obj)}")
