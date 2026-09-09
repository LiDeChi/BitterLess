"""Timeline layers: Canonical (append-only), Experimental Branch, Sandbox."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from bitterless.models.types import TimelineKind


class AppendOnlyViolation(Exception):
    """Raised when Canonical History would be mutated non-append."""


@dataclass
class HistoryEvent:
    id: str
    tick: int
    kind: str
    summary: str
    payload: dict[str, Any] = field(default_factory=dict)
    actor_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "tick": self.tick,
            "kind": self.kind,
            "summary": self.summary,
            "payload": dict(self.payload),
            "actor_ids": list(self.actor_ids),
        }

    @staticmethod
    def new(
        tick: int,
        kind: str,
        summary: str,
        *,
        payload: dict[str, Any] | None = None,
        actor_ids: list[str] | None = None,
    ) -> HistoryEvent:
        return HistoryEvent(
            id=str(uuid4()),
            tick=tick,
            kind=kind,
            summary=summary,
            payload=dict(payload or {}),
            actor_ids=list(actor_ids or []),
        )


@dataclass
class Timeline:
    kind: TimelineKind
    name: str
    events: list[HistoryEvent] = field(default_factory=list)
    parent_id: str | None = None
    fork_tick: int | None = None
    id: str = field(default_factory=lambda: str(uuid4()))
    sealed: bool = False  # experimental/sandbox may seal; canonical never rewrites

    def append(self, event: HistoryEvent) -> HistoryEvent:
        if self.kind == TimelineKind.CANONICAL and self.sealed:
            raise AppendOnlyViolation("Canonical timeline is sealed against further append")
        # Canonical: never allow insert/replace — only append.
        if self.events and event.tick < self.events[-1].tick and self.kind == TimelineKind.CANONICAL:
            raise AppendOnlyViolation(
                f"Canonical History is append-only; cannot append tick {event.tick} "
                f"before last tick {self.events[-1].tick}"
            )
        self.events.append(event)
        return event

    def rewrite_forbidden(self, index: int, new_event: HistoryEvent) -> None:
        """Explicit guard used by tests and callers — always raises for canonical."""
        if self.kind == TimelineKind.CANONICAL:
            raise AppendOnlyViolation("Canonical History cannot be rewritten")
        self.events[index] = new_event

    def truncate_from(self, tick: int) -> None:
        """Allowed only on experimental/sandbox branches."""
        if self.kind == TimelineKind.CANONICAL:
            raise AppendOnlyViolation("Canonical History cannot truncate")
        self.events = [e for e in self.events if e.tick < tick]

    def snapshot_events(self) -> list[dict[str, Any]]:
        return [e.to_dict() for e in self.events]

    def fork(
        self,
        name: str,
        at_tick: int,
        *,
        kind: TimelineKind = TimelineKind.EXPERIMENTAL,
    ) -> Timeline:
        """Fork a new experimental (or sandbox) timeline from this one at `at_tick`."""
        if kind == TimelineKind.CANONICAL:
            raise ValueError("Cannot fork a new Canonical timeline")
        retained = [deepcopy(e) for e in self.events if e.tick <= at_tick]
        return Timeline(
            kind=kind,
            name=name,
            events=retained,
            parent_id=self.id,
            fork_tick=at_tick,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind.value,
            "name": self.name,
            "parent_id": self.parent_id,
            "fork_tick": self.fork_tick,
            "event_count": len(self.events),
            "events": self.snapshot_events(),
        }


@dataclass
class TimelineStore:
    """Holds the three timeline layers for a lab session."""

    canonical: Timeline = field(
        default_factory=lambda: Timeline(kind=TimelineKind.CANONICAL, name="正史")
    )
    experimental: list[Timeline] = field(default_factory=list)
    sandboxes: list[Timeline] = field(default_factory=list)

    def active_canonical(self) -> Timeline:
        return self.canonical

    def fork_experiment(self, name: str, at_tick: int) -> Timeline:
        branch = self.canonical.fork(name, at_tick, kind=TimelineKind.EXPERIMENTAL)
        self.experimental.append(branch)
        return branch

    def new_sandbox(self, name: str = "sandbox") -> Timeline:
        sb = Timeline(kind=TimelineKind.SANDBOX, name=name)
        self.sandboxes.append(sb)
        return sb

    def to_dict(self) -> dict[str, Any]:
        return {
            "canonical": self.canonical.to_dict(),
            "experimental": [t.to_dict() for t in self.experimental],
            "sandboxes": [t.to_dict() for t in self.sandboxes],
        }
