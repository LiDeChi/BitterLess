"""Persistent main researcher with a continuous Research Thread."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from bitterless.models.types import FocusDim, InterventionKind


@dataclass
class PlayerIntervention:
    kind: InterventionKind
    content: str
    tick: int
    id: str = field(default_factory=lambda: str(uuid4()))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind.value,
            "content": self.content,
            "tick": self.tick,
        }


@dataclass
class ResearchStep:
    phase: str  # problem|model|anomaly|hypothesis|focus|expand|evidence|revise|new_problem
    content: str
    tick: int
    data: dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid4()))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "phase": self.phase,
            "content": self.content,
            "tick": self.tick,
            "data": dict(self.data),
        }


PHASES = [
    "problem",
    "model",
    "anomaly",
    "hypothesis",
    "focus",
    "expand",
    "evidence",
    "revise",
    "new_problem",
]


@dataclass
class ResearchThread:
    """Continuous research mind — not a chat assistant, not an omniscient director."""

    researcher_name: str = "主研究员"
    steps: list[ResearchStep] = field(default_factory=list)
    interventions: list[PlayerIntervention] = field(default_factory=list)
    current_problem: str = "心智与秩序如何从局部经验中生成？"
    current_model_summary: str = "初始低分辨率东周近似：稀薄人口、口传媒介、制度萌芽"
    current_hypothesis: str | None = None
    current_focus_dims: list[FocusDim] = field(default_factory=list)
    current_focus_targets: list[str] = field(default_factory=list)
    anomalies: list[str] = field(default_factory=list)
    challenged: bool = False

    def record(self, phase: str, content: str, tick: int, **data: Any) -> ResearchStep:
        step = ResearchStep(phase=phase, content=content, tick=tick, data=dict(data))
        self.steps.append(step)
        return step

    def intervene(
        self,
        kind: InterventionKind,
        content: str,
        tick: int,
    ) -> PlayerIntervention:
        """Player may challenge hypothesis / change focus — not step-by-step remote control."""
        iv = PlayerIntervention(kind=kind, content=content, tick=tick)
        self.interventions.append(iv)
        if kind == InterventionKind.CHALLENGE_HYPOTHESIS:
            self.challenged = True
            self.record(
                "hypothesis",
                f"[player challenge] {content}",
                tick,
                intervention_id=iv.id,
            )
            # Force re-open hypothesis rather than obediently following remote steps
            prior = self.current_hypothesis or "(none yet)"
            self.current_hypothesis = f"CHALLENGED: {prior} | alt: {content}"
        elif kind == InterventionKind.CHANGE_FOCUS:
            # Parse focus dims from content tokens if present
            tokens = {t.strip().lower() for t in content.replace("，", ",").split(",")}
            dims: list[FocusDim] = []
            for d in FocusDim:
                if d.value in tokens or d.value in content.lower():
                    dims.append(d)
            if dims:
                self.current_focus_dims = dims
            self.record(
                "focus",
                f"[player change focus] {content}",
                tick,
                intervention_id=iv.id,
                dims=[d.value for d in self.current_focus_dims],
            )
        else:
            self.record("note", f"[player note] {content}", tick, intervention_id=iv.id)
        return iv

    def to_dict(self) -> dict[str, Any]:
        return {
            "researcher_name": self.researcher_name,
            "current_problem": self.current_problem,
            "current_model_summary": self.current_model_summary,
            "current_hypothesis": self.current_hypothesis,
            "current_focus_dims": [d.value for d in self.current_focus_dims],
            "current_focus_targets": list(self.current_focus_targets),
            "anomalies": list(self.anomalies),
            "challenged": self.challenged,
            "steps": [s.to_dict() for s in self.steps],
            "interventions": [i.to_dict() for i in self.interventions],
        }
