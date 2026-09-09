"""Multi-scale Eastern Zhou world: people as media streams, institutions, mechanisms."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from bitterless.models.compression import CompressionEngine, MediaItem
from bitterless.models.resources import ResolutionBudget
from bitterless.models.timeline import HistoryEvent, TimelineStore
from bitterless.models.types import (
    FocusDim,
    ProvenanceKind,
    ResolutionLevel,
)


@dataclass
class Relation:
    source_id: str
    target_id: str
    label: str  # e.g. kinship, debt, trust — descriptive, not stereotype
    strength: float = 0.5
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "target_id": self.target_id,
            "label": self.label,
            "strength": self.strength,
            "notes": self.notes,
        }


@dataclass
class MediumChannel:
    """A media channel in the world (speech, bamboo slip, notice board, prices…)."""

    id: str
    name: str
    kind: str
    reach: list[str] = field(default_factory=list)  # person ids who can access
    messages: list[dict[str, Any]] = field(default_factory=list)

    def publish(self, tick: int, content: str, author_id: str | None = None) -> dict[str, Any]:
        msg = {
            "id": str(uuid4()),
            "tick": tick,
            "content": content,
            "author_id": author_id,
        }
        self.messages.append(msg)
        return msg

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "kind": self.kind,
            "reach": list(self.reach),
            "messages": list(self.messages),
        }


@dataclass
class Institution:
    """A forming institution — not a finished bureaucracy."""

    id: str
    name: str
    forming: bool = True
    norms: list[str] = field(default_factory=list)
    member_ids: list[str] = field(default_factory=list)
    stage: str = "nascent"  # nascent → contested → stabilizing

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "forming": self.forming,
            "norms": list(self.norms),
            "member_ids": list(self.member_ids),
            "stage": self.stage,
        }


@dataclass
class ConditionalMechanism:
    """
    Learned conditional mechanism — NEVER a stereotype label.

    Example: IF credit_low AND debt_high AND kin_present THEN seek_kin_mediation
    NOT: merchant = greedy
    """

    id: str
    name: str
    conditions: dict[str, Any]
    outcome: str
    confidence: float = 0.5
    evidence_ids: list[str] = field(default_factory=list)
    banned_labels: tuple[str, ...] = ("greedy", "忠诚", "奸商", "野蛮")

    def __post_init__(self) -> None:
        lowered = self.outcome.lower()
        for bad in self.banned_labels:
            if bad.lower() in lowered:
                raise ValueError(
                    f"Mechanism outcome looks like a stereotype label ({bad!r}); "
                    "migrate conditional mechanisms only"
                )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "conditions": dict(self.conditions),
            "outcome": self.outcome,
            "confidence": self.confidence,
            "evidence_ids": list(self.evidence_ids),
        }


@dataclass
class Person:
    """A character as a continuous media stream — not a personality card."""

    id: str
    name: str
    role_hint: str  # descriptive occupation hint for seed, not stereotype engine
    alive: bool = True
    tick_born: int = 0
    tick_died: int | None = None
    hard_facts: list[str] = field(default_factory=list)
    coarse_history: list[str] = field(default_factory=list)
    media_stream: list[MediaItem] = field(default_factory=list)
    # Left-behind media after death
    residual_media: list[dict[str, Any]] = field(default_factory=list)
    location: str = "邑"
    economy: dict[str, float] = field(default_factory=lambda: {"grain": 1.0, "debt": 0.0})
    # Tracks whether current detail was remanifested
    remanifest_generation: int = 0

    def ingest(
        self,
        engine: CompressionEngine,
        content: str,
        tick: int,
        *,
        surprise: float = 0.0,
        social_weight: float = 0.0,
        related_ids: list[str] | None = None,
        provenance: ProvenanceKind = ProvenanceKind.COMPUTED,
    ) -> MediaItem | None:
        if not self.alive:
            return None
        return engine.ingest_raw(
            self.media_stream,
            content,
            tick,
            surprise=surprise,
            social_weight=social_weight,
            related_ids=related_ids,
            provenance=provenance,
        )

    def die(self, tick: int, cause: str = "unknown") -> None:
        """Agent stops; media remains."""
        self.alive = False
        self.tick_died = tick
        self.coarse_history.append(f"died@{tick}: {cause}")
        # Freeze residual copies of active media
        self.residual_media = [m.to_dict() for m in self.media_stream if m.active]

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "role_hint": self.role_hint,
            "alive": self.alive,
            "tick_born": self.tick_born,
            "tick_died": self.tick_died,
            "hard_facts": list(self.hard_facts),
            "coarse_history": list(self.coarse_history),
            "media_stream": [m.to_dict() for m in self.media_stream],
            "residual_media": list(self.residual_media),
            "location": self.location,
            "economy": dict(self.economy),
            "remanifest_generation": self.remanifest_generation,
        }


@dataclass
class WorldState:
    """Low-res approximate whole + optional high-res expansions under its boundaries."""

    tick: int = 0
    people: dict[str, Person] = field(default_factory=dict)
    relations: list[Relation] = field(default_factory=list)
    channels: dict[str, MediumChannel] = field(default_factory=dict)
    institutions: dict[str, Institution] = field(default_factory=dict)
    mechanisms: list[ConditionalMechanism] = field(default_factory=list)
    low_res_summary: dict[str, Any] = field(default_factory=dict)
    focus: dict[str, Any] = field(default_factory=dict)  # current high-res focus
    budget: ResolutionBudget = field(default_factory=ResolutionBudget)
    timelines: TimelineStore = field(default_factory=TimelineStore)
    compression: CompressionEngine = field(default_factory=CompressionEngine)
    # High-res expansion log (what was actually computed)
    computed_detail_ids: set[str] = field(default_factory=set)

    def person(self, pid: str) -> Person:
        return self.people[pid]

    def advance_low_res(self) -> HistoryEvent:
        """Advance the whole world one low-resolution tick."""
        self.tick += 1
        # Simple low-res economy drift under known mechanisms
        for p in self.people.values():
            if not p.alive:
                continue
            p.economy["grain"] = max(0.0, p.economy.get("grain", 1.0) - 0.05)
            # Apply conditional mechanisms if conditions match (no stereotypes)
            for mech in self.mechanisms:
                if self._conditions_match(p, mech.conditions):
                    p.coarse_history.append(
                        f"t{self.tick}: mechanism[{mech.name}] → {mech.outcome}"
                    )
        # Compress media streams
        for p in self.people.values():
            if p.alive:
                self.compression.compress(p.media_stream, self.tick)

        summary = f"low-res tick {self.tick}: {sum(1 for p in self.people.values() if p.alive)} alive"
        self.low_res_summary = {
            "tick": self.tick,
            "alive": [p.name for p in self.people.values() if p.alive],
            "institutions": [i.name for i in self.institutions.values()],
            "mechanism_count": len(self.mechanisms),
        }
        ev = HistoryEvent.new(self.tick, "low_res_tick", summary, payload=dict(self.low_res_summary))
        self.timelines.canonical.append(ev)
        return ev

    def _conditions_match(self, person: Person, conditions: dict[str, Any]) -> bool:
        for key, expected in conditions.items():
            if key.startswith("economy."):
                field_name = key.split(".", 1)[1]
                actual = person.economy.get(field_name)
                if actual is None:
                    return False
                if isinstance(expected, dict):
                    if "gte" in expected and not (actual >= expected["gte"]):
                        return False
                    if "lte" in expected and not (actual <= expected["lte"]):
                        return False
                elif actual != expected:
                    return False
            elif key == "alive":
                if person.alive != expected:
                    return False
            elif key == "location":
                if person.location != expected:
                    return False
        return True

    def set_focus(
        self,
        dims: list[FocusDim],
        target_ids: list[str],
        level: ResolutionLevel = ResolutionLevel.HIGH,
        reason: str = "",
    ) -> list[str]:
        notes: list[str] = []
        self.focus = {
            "dims": [d.value for d in dims],
            "target_ids": list(target_ids),
            "level": level.value,
            "reason": reason,
            "tick": self.tick,
        }
        for tid in target_ids:
            if tid in self.people:
                notes.extend(self.budget.raise_focus(tid, dims, level))
            elif tid in self.institutions or tid in self.channels:
                notes.extend(self.budget.raise_focus(tid, dims, level))
            else:
                # relation / abstract focus still consumes budget under a synthetic id
                notes.extend(self.budget.raise_focus(tid, dims, level))
        return notes

    def expand_high_res(self) -> list[dict[str, Any]]:
        """
        Expand high-res under low-res boundaries for current focus.
        Only generates CURRENT state detail; past micro-events not previously
        computed are marked reconstruction (via remanifest), never as computed history.
        """
        details: list[dict[str, Any]] = []
        if not self.focus:
            return details
        target_ids = self.focus.get("target_ids", [])
        dims = self.focus.get("dims", [])
        for tid in target_ids:
            if tid not in self.people:
                continue
            person = self.people[tid]
            if not person.alive:
                continue
            # High-res under low-res boundary: use coarse location/economy as bounds
            detail_id = f"hr-{tid}-t{self.tick}-{'-'.join(dims)}"
            detail = {
                "id": detail_id,
                "person_id": tid,
                "tick": self.tick,
                "dims": dims,
                "provenance": ProvenanceKind.COMPUTED.value,
                "bounds": {
                    "location": person.location,
                    "economy": dict(person.economy),
                    "low_res_tick": self.tick,
                },
                "observations": self._high_res_observations(person, dims),
            }
            self.computed_detail_ids.add(detail_id)
            details.append(detail)
            # Feed observations into media stream
            for obs in detail["observations"]:
                person.ingest(
                    self.compression,
                    obs,
                    self.tick,
                    surprise=0.4,
                    social_weight=0.3,
                    related_ids=[tid],
                )
            ev = HistoryEvent.new(
                self.tick,
                "high_res_expand",
                f"expanded {person.name} on {dims}",
                payload={"detail_id": detail_id},
                actor_ids=[tid],
            )
            self.timelines.canonical.append(ev)
        return details

    def _high_res_observations(self, person: Person, dims: list[str]) -> list[str]:
        obs: list[str] = []
        if FocusDim.PERSON.value in dims or FocusDim.BEHAVIOR.value in dims:
            obs.append(f"{person.name} acts under grain={person.economy.get('grain', 0):.2f}")
        if FocusDim.MEDIUM.value in dims:
            accessible = [
                ch.name for ch in self.channels.values() if person.id in ch.reach
            ]
            obs.append(f"{person.name} accesses media: {', '.join(accessible) or 'none'}")
        if FocusDim.RELATION.value in dims:
            rels = [
                r
                for r in self.relations
                if r.source_id == person.id or r.target_id == person.id
            ]
            obs.append(f"{person.name} relations: " + "; ".join(f"{r.label}:{r.strength:.1f}" for r in rels))
        if FocusDim.ECONOMY.value in dims:
            obs.append(f"{person.name} economy snapshot {person.economy}")
        if FocusDim.INSTITUTION.value in dims:
            memberships = [
                i.name for i in self.institutions.values() if person.id in i.member_ids
            ]
            obs.append(f"{person.name} institutions: {', '.join(memberships) or 'none'}")
        if FocusDim.TIME.value in dims:
            obs.append(f"{person.name} coarse_history_len={len(person.coarse_history)}")
        if not obs:
            obs.append(f"{person.name} present at {person.location}")
        return obs

    def update_low_res_from_high_res(self, details: list[dict[str, Any]]) -> ConditionalMechanism | None:
        """Migrate conditional mechanisms — never stereotype labels."""
        if not details:
            return None
        # Learn a simple conditional mechanism from observed debt/grain pressure
        indebted = [
            self.people[d["person_id"]]
            for d in details
            if d["person_id"] in self.people
            and self.people[d["person_id"]].economy.get("debt", 0) >= 1.0
        ]
        if not indebted:
            return None
        mech = ConditionalMechanism(
            id=str(uuid4()),
            name="debt_kin_mediation",
            conditions={"economy.debt": {"gte": 1.0}, "alive": True},
            outcome="seek_kin_or_peer_mediation_when_debt_high",
            confidence=0.4 + 0.1 * len(indebted),
            evidence_ids=[d["id"] for d in details],
        )
        # Avoid duplicates by name
        if any(m.name == mech.name for m in self.mechanisms):
            existing = next(m for m in self.mechanisms if m.name == mech.name)
            existing.confidence = min(1.0, existing.confidence + 0.05)
            existing.evidence_ids.extend(mech.evidence_ids)
            return existing
        self.mechanisms.append(mech)
        self.low_res_summary["last_mechanism"] = mech.name
        ev = HistoryEvent.new(
            self.tick,
            "mechanism_update",
            f"learned mechanism {mech.name}",
            payload=mech.to_dict(),
        )
        self.timelines.canonical.append(ev)
        return mech

    def remanifest(self, person_id: str) -> dict[str, Any]:
        """
        复显: rebuild current detail from hard facts + coarse history + current state.
        Never invent past micro-events as computed history.
        """
        person = self.people[person_id]
        person.remanifest_generation += 1
        # Raise resolution budget
        self.budget.raise_focus(
            person_id,
            [FocusDim.PERSON, FocusDim.BEHAVIOR],
            ResolutionLevel.HIGH,
        )
        reconstruction = {
            "person_id": person_id,
            "generation": person.remanifest_generation,
            "hard_facts": list(person.hard_facts),
            "coarse_history": list(person.coarse_history),
            "current_state": {
                "alive": person.alive,
                "location": person.location,
                "economy": dict(person.economy),
            },
            # Explicitly marked — not computed history
            "provenance": ProvenanceKind.RECONSTRUCTION.value,
            "current_detail": (
                f"[reconstruction] {person.name} at {person.location}, "
                f"economy={person.economy}, facts={person.hard_facts}"
            ),
            "forbidden": "past micro-events not previously computed must not appear as history",
        }
        # Only inject reconstruction-marked media for CURRENT state
        if person.alive:
            item = MediaItem.new(
                tier=__import__(
                    "bitterless.models.types", fromlist=["CompressionTier"]
                ).CompressionTier.EVENT,
                content=reconstruction["current_detail"],
                tick=self.tick,
                provenance=ProvenanceKind.RECONSTRUCTION,
            )
            person.media_stream.append(item)
        ev = HistoryEvent.new(
            self.tick,
            "remanifest",
            f"remanifested {person.name} (gen {person.remanifest_generation})",
            payload={
                "person_id": person_id,
                "provenance": ProvenanceKind.RECONSTRUCTION.value,
            },
            actor_ids=[person_id],
        )
        self.timelines.canonical.append(ev)
        return reconstruction

    def was_computed(self, detail_id: str) -> bool:
        return detail_id in self.computed_detail_ids

    def to_dict(self) -> dict[str, Any]:
        return {
            "tick": self.tick,
            "people": {pid: p.to_dict() for pid, p in self.people.items()},
            "relations": [r.to_dict() for r in self.relations],
            "channels": {cid: c.to_dict() for cid, c in self.channels.items()},
            "institutions": {iid: i.to_dict() for iid, i in self.institutions.items()},
            "mechanisms": [m.to_dict() for m in self.mechanisms],
            "low_res_summary": dict(self.low_res_summary),
            "focus": dict(self.focus),
            "budget": self.budget.to_dict(),
            "timelines": self.timelines.to_dict(),
            "computed_detail_count": len(self.computed_detail_ids),
        }
