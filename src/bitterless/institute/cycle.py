"""Research cycle: problem→model→anomaly→hypothesis→focus→expand→evidence→revise→new problem."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from bitterless.institute.researcher import ResearchThread
from bitterless.models.types import FocusDim, InterventionKind, ResolutionLevel
from bitterless.models.world import WorldState


@dataclass
class CycleResult:
    steps_run: list[str] = field(default_factory=list)
    evidence: list[dict[str, Any]] = field(default_factory=list)
    mechanism: dict[str, Any] | None = None
    new_problem: str | None = None
    thread_snapshot: dict[str, Any] = field(default_factory=dict)
    world_tick: int = 0
    focus: dict[str, Any] = field(default_factory=dict)
    compression_snapshot: dict[str, Any] = field(default_factory=dict)
    fork_timeline_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "steps_run": list(self.steps_run),
            "evidence": list(self.evidence),
            "mechanism": self.mechanism,
            "new_problem": self.new_problem,
            "thread": self.thread_snapshot,
            "world_tick": self.world_tick,
            "focus": self.focus,
            "compression_snapshot": self.compression_snapshot,
            "fork_timeline_id": self.fork_timeline_id,
        }


@dataclass
class ResearchCycle:
    """One full pass of the institute research loop against the world."""

    world: WorldState
    thread: ResearchThread = field(default_factory=ResearchThread)
    # Optional player interventions queued before/during cycle (not remote control)
    pending_interventions: list[tuple[InterventionKind, str]] = field(default_factory=list)

    def queue_intervention(self, kind: InterventionKind, content: str) -> None:
        self.pending_interventions.append((kind, content))

    def run(self, *, fork_experiment: bool = False) -> CycleResult:
        result = CycleResult()
        w = self.world
        t = self.thread

        # Apply any pending player interventions at cycle start
        for kind, content in self.pending_interventions:
            t.intervene(kind, content, w.tick)
        self.pending_interventions.clear()

        # 1. problem
        t.record("problem", t.current_problem, w.tick)
        result.steps_run.append("problem")

        # 2. model
        t.record("model", t.current_model_summary, w.tick, mechanisms=len(w.mechanisms))
        result.steps_run.append("model")

        # 3. anomaly — look for mismatches between model and low-res world
        anomaly = self._detect_anomaly()
        t.anomalies.append(anomaly)
        t.record("anomaly", anomaly, w.tick)
        result.steps_run.append("anomaly")

        # 4. hypothesis
        if t.challenged and t.current_hypothesis and t.current_hypothesis.startswith("CHALLENGED"):
            # Absorb player challenge; optionally append institute's competing view
            proposed = self._propose_hypothesis(anomaly)
            if "| alt:" in t.current_hypothesis:
                hypothesis = t.current_hypothesis
            else:
                hypothesis = f"CHALLENGED: {proposed} | alt: (player)"
            t.current_hypothesis = hypothesis
        else:
            hypothesis = self._propose_hypothesis(anomaly)
            t.current_hypothesis = hypothesis
        t.record("hypothesis", hypothesis, w.tick)
        result.steps_run.append("hypothesis")

        # 5. focus — choose dims + targets (respect player change_focus if set)
        dims, targets = self._choose_focus(hypothesis)
        if t.current_focus_dims:
            dims = t.current_focus_dims
        t.current_focus_dims = dims
        t.current_focus_targets = targets
        notes = w.set_focus(dims, targets, ResolutionLevel.HIGH, reason=hypothesis)
        t.record(
            "focus",
            f"focus dims={[d.value for d in dims]} targets={targets}",
            w.tick,
            demotions=notes,
        )
        result.steps_run.append("focus")
        result.focus = dict(w.focus)

        # Optional: fork experimental branch before high-res expand
        if fork_experiment:
            branch = w.timelines.fork_experiment(
                f"exp-after-t{w.tick}",
                at_tick=w.tick,
            )
            result.fork_timeline_id = branch.id
            t.record("note", f"forked experimental branch {branch.name}", w.tick, branch_id=branch.id)

        # 6. high-res expand (under low-res boundaries)
        # Advance low-res once to move time, then expand
        w.advance_low_res()
        details = w.expand_high_res()
        t.record("expand", f"expanded {len(details)} high-res detail(s)", w.tick, count=len(details))
        result.steps_run.append("expand")

        # 7. evidence
        evidence = details
        result.evidence = evidence
        t.record("evidence", f"collected {len(evidence)} evidence items", w.tick)
        result.steps_run.append("evidence")

        # 8. revise model — update low-res via conditional mechanisms
        mech = w.update_low_res_from_high_res(details)
        if mech:
            t.current_model_summary = (
                f"revised model @t{w.tick}: +mechanism {mech.name} "
                f"(confidence={mech.confidence:.2f}); still no stereotype labels"
            )
            result.mechanism = mech.to_dict()
        else:
            t.current_model_summary = (
                f"revised model @t{w.tick}: no new mechanism; refined focus on {dims}"
            )
        t.record("revise", t.current_model_summary, w.tick)
        result.steps_run.append("revise")

        # 9. new problem
        new_problem = self._next_problem(hypothesis, evidence, mech)
        t.current_problem = new_problem
        t.challenged = False  # reset challenge latch after absorbing it
        t.record("new_problem", new_problem, w.tick)
        result.steps_run.append("new_problem")
        result.new_problem = new_problem

        result.world_tick = w.tick
        result.thread_snapshot = t.to_dict()
        result.compression_snapshot = self._compression_snapshot()
        return result

    def _detect_anomaly(self) -> str:
        w = self.world
        high_debt = [
            p.name
            for p in w.people.values()
            if p.alive and p.economy.get("debt", 0) >= 1.0
        ]
        if high_debt and not any(m.name == "debt_kin_mediation" for m in w.mechanisms):
            return (
                f"anomaly: {', '.join(high_debt)} carry high debt but low-res model "
                "has no conditional mediation mechanism"
            )
        # Media without institutional norm
        if w.channels and w.institutions:
            forming = [i for i in w.institutions.values() if i.forming]
            if forming:
                return (
                    f"anomaly: forming institution '{forming[0].name}' coexists with "
                    f"{len(w.channels)} media channels; unclear how norms stabilize via media"
                )
        return "anomaly: model under-explains how local trust forms under scarce media"

    def _propose_hypothesis(self, anomaly: str) -> str:
        if "debt" in anomaly:
            return (
                "hypothesis: under high debt + kin/peer presence, agents seek mediation "
                "rather than immediate default (conditional, not 'merchants=greedy')"
            )
        if "institution" in anomaly or "media" in anomaly:
            return (
                "hypothesis: forming norms stabilize when the same medium repeatedly "
                "carries consistent peer sanctions"
            )
        return "hypothesis: local trust accrues from repeated low-surprise media exchanges"

    def _choose_focus(self, hypothesis: str) -> tuple[list[FocusDim], list[str]]:
        w = self.world
        if "debt" in hypothesis or "mediation" in hypothesis:
            targets = [
                p.id
                for p in w.people.values()
                if p.alive and p.economy.get("debt", 0) >= 0.5
            ][:2]
            if not targets:
                targets = [next(iter(w.people))]
            return [FocusDim.ECONOMY, FocusDim.RELATION, FocusDim.PERSON], targets
        if "medium" in hypothesis or "norms" in hypothesis or "media" in hypothesis:
            targets = list(w.channels.keys())[:1] + [
                p.id for p in list(w.people.values())[:2] if p.alive
            ]
            return [FocusDim.MEDIUM, FocusDim.INSTITUTION, FocusDim.BEHAVIOR], targets
        targets = [p.id for p in list(w.people.values())[:2] if p.alive]
        return [FocusDim.PERSON, FocusDim.RELATION], targets

    def _next_problem(self, hypothesis: str, evidence: list, mech: Any) -> str:
        if mech:
            return (
                f"新问题: 机制 {mech.name} 在跨邑迁移时边界条件如何变化？"
            )
        if evidence:
            return "新问题: 高分辨率证据如何压缩回低分辨率而不丢失条件结构？"
        return f"新问题: 若假设被证伪（{hypothesis[:40]}…），下一步聚焦何处？"

    def _compression_snapshot(self) -> dict[str, Any]:
        snap: dict[str, Any] = {}
        for pid, person in self.world.people.items():
            by_tier = self.world.compression.active_by_tier(person.media_stream)
            snap[pid] = {
                "name": person.name,
                "alive": person.alive,
                "tiers": {k: len(v) for k, v in by_tier.items()},
                "residual_media": len(person.residual_media),
            }
        return snap


def run_smoke_cycle(
    world: WorldState,
    *,
    interventions: list[tuple[InterventionKind, str]] | None = None,
    fork_experiment: bool = False,
    thread: ResearchThread | None = None,
) -> CycleResult:
    cycle = ResearchCycle(world=world, thread=thread or ResearchThread())
    for kind, content in interventions or []:
        cycle.queue_intervention(kind, content)
    return cycle.run(fork_experiment=fork_experiment)
