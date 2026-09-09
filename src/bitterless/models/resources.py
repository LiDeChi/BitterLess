"""Resolution budget: demote resolution, never delete people."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from bitterless.models.types import FocusDim, ResolutionLevel


RESOLUTION_COST: dict[ResolutionLevel, float] = {
    ResolutionLevel.NONE: 0.0,
    ResolutionLevel.LOW: 1.0,
    ResolutionLevel.MEDIUM: 2.0,
    ResolutionLevel.HIGH: 4.0,
    ResolutionLevel.ULTRA: 8.0,
}

RESOLUTION_ORDER = [
    ResolutionLevel.NONE,
    ResolutionLevel.LOW,
    ResolutionLevel.MEDIUM,
    ResolutionLevel.HIGH,
    ResolutionLevel.ULTRA,
]


def demote(level: ResolutionLevel) -> ResolutionLevel:
    idx = RESOLUTION_ORDER.index(level)
    return RESOLUTION_ORDER[max(0, idx - 1)]


def promote(level: ResolutionLevel) -> ResolutionLevel:
    idx = RESOLUTION_ORDER.index(level)
    return RESOLUTION_ORDER[min(len(RESOLUTION_ORDER) - 1, idx + 1)]


@dataclass
class DimResolution:
    """Per-dimension resolution for one entity."""

    levels: dict[FocusDim, ResolutionLevel] = field(default_factory=dict)

    def get(self, dim: FocusDim) -> ResolutionLevel:
        return self.levels.get(dim, ResolutionLevel.LOW)

    def set(self, dim: FocusDim, level: ResolutionLevel) -> None:
        self.levels[dim] = level

    def cost(self) -> float:
        return sum(RESOLUTION_COST[self.get(d)] for d in FocusDim)

    def to_dict(self) -> dict[str, str]:
        return {d.value: self.get(d).value for d in FocusDim}


@dataclass
class ResolutionBudget:
    """Global budget controlling how richly the world is retained."""

    capacity: float = 40.0
    spent: float = 0.0
    # entity_id -> DimResolution
    allocations: dict[str, DimResolution] = field(default_factory=dict)

    def remaining(self) -> float:
        return self.capacity - self.spent

    def ensure(self, entity_id: str) -> DimResolution:
        if entity_id not in self.allocations:
            # Start at NONE; callers/seed raise the dims they need.
            self.allocations[entity_id] = DimResolution(
                {d: ResolutionLevel.NONE for d in FocusDim}
            )
            self._recompute()
        return self.allocations[entity_id]

    def _recompute(self) -> None:
        self.spent = sum(dr.cost() for dr in self.allocations.values())

    def raise_focus(
        self,
        entity_id: str,
        dims: list[FocusDim],
        target: ResolutionLevel = ResolutionLevel.HIGH,
    ) -> list[str]:
        """Raise resolution on dims; demote others if over budget. Never deletes."""
        notes: list[str] = []
        dr = self.ensure(entity_id)
        for dim in dims:
            dr.set(dim, target)
        self._recompute()
        if self.spent > self.capacity:
            notes.extend(self._demote_until_fit(prefer_keep=entity_id))
        return notes

    def _demote_until_fit(self, prefer_keep: str) -> list[str]:
        notes: list[str] = []
        # Demote non-focused entities first, highest cost dims first.
        safety = 0
        while self.spent > self.capacity and safety < 500:
            safety += 1
            candidates: list[tuple[str, FocusDim, ResolutionLevel, float]] = []
            for eid, dr in self.allocations.items():
                if eid == prefer_keep:
                    continue
                for dim in FocusDim:
                    lvl = dr.get(dim)
                    if lvl != ResolutionLevel.NONE:
                        candidates.append((eid, dim, lvl, RESOLUTION_COST[lvl]))
            if not candidates:
                # Last resort: demote the focused entity's non-target dims gently.
                dr = self.allocations[prefer_keep]
                for dim in FocusDim:
                    lvl = dr.get(dim)
                    if lvl in (ResolutionLevel.ULTRA, ResolutionLevel.HIGH):
                        new_lvl = demote(lvl)
                        dr.set(dim, new_lvl)
                        notes.append(
                            f"demoted {prefer_keep}/{dim.value} {lvl.value}→{new_lvl.value}"
                        )
                        self._recompute()
                        break
                else:
                    break
                continue
            candidates.sort(key=lambda x: -x[3])
            eid, dim, lvl, _ = candidates[0]
            new_lvl = demote(lvl)
            self.allocations[eid].set(dim, new_lvl)
            notes.append(f"demoted {eid}/{dim.value} {lvl.value}→{new_lvl.value}")
            self._recompute()
        return notes

    def entity_exists(self, entity_id: str) -> bool:
        """People are never deleted by budget pressure."""
        return entity_id in self.allocations

    def to_dict(self) -> dict[str, Any]:
        return {
            "capacity": self.capacity,
            "spent": self.spent,
            "remaining": self.remaining(),
            "allocations": {eid: dr.to_dict() for eid, dr in self.allocations.items()},
        }
