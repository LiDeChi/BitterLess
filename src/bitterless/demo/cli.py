"""CLI demo: run research cycles, show focus/resolution, compression ladder, fork."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from bitterless.institute.cycle import ResearchCycle, run_smoke_cycle
from bitterless.institute.researcher import ResearchThread
from bitterless.models.types import InterventionKind
from bitterless.seed.eastern_zhou import build_seed_world


def _banner(title: str) -> None:
    print()
    print("=" * 72)
    print(title)
    print("=" * 72)


def _pp(data: Any) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2, default=str))


def run_demo(
    *,
    cycles: int = 1,
    challenge: str | None = None,
    change_focus: str | None = None,
    fork: bool = True,
    remanifest_id: str | None = None,
    show_json: bool = False,
) -> int:
    world = build_seed_world()
    thread = ResearchThread()

    _banner("BitterLess · 东周实验室 Phase 1 demo")
    print(f"Seed tick={world.tick} people={list(world.people)}")
    print(f"Institution: {list(world.institutions)}")
    print(f"Channels: {[c.name for c in world.channels.values()]}")
    print(f"Budget remaining: {world.budget.remaining():.1f}/{world.budget.capacity}")

    interventions: list[tuple[InterventionKind, str]] = []
    if challenge:
        interventions.append((InterventionKind.CHALLENGE_HYPOTHESIS, challenge))
    if change_focus:
        interventions.append((InterventionKind.CHANGE_FOCUS, change_focus))

    last_result = None
    for i in range(cycles):
        _banner(f"Research cycle {i + 1}")
        cycle = ResearchCycle(world=world, thread=thread)
        for kind, content in interventions if i == 0 else []:
            cycle.queue_intervention(kind, content)
            print(f"  player intervention: {kind.value} → {content}")
        result = cycle.run(fork_experiment=(fork and i == 0))
        last_result = result

        print(f"\n  tick now: {result.world_tick}")
        print(f"  steps: {' → '.join(result.steps_run)}")
        print(f"  focus: {result.focus}")
        print(f"  new problem: {result.new_problem}")
        if result.mechanism:
            print(f"  mechanism: {result.mechanism['name']} (conf={result.mechanism['confidence']:.2f})")
            print(f"    outcome: {result.mechanism['outcome']}")
        if result.fork_timeline_id:
            print(f"  forked experimental timeline: {result.fork_timeline_id}")

        print("\n  — compression ladder (active counts) —")
        for pid, snap in result.compression_snapshot.items():
            print(f"    {snap['name']}: {snap['tiers']} residual={snap['residual_media']}")

        print("\n  — resolution budget (sample) —")
        for pid, dr in list(world.budget.allocations.items())[:4]:
            print(f"    {pid}: {dr.to_dict()}")
        print(f"    spent={world.budget.spent:.1f} remaining={world.budget.remaining():.1f}")

        print("\n  — research thread (last 4 steps) —")
        for step in thread.steps[-4:]:
            print(f"    [{step.phase}] {step.content[:100]}")

    if remanifest_id:
        _banner(f"复显 remanifest: {remanifest_id}")
        if remanifest_id not in world.people:
            # allow name lookup
            match = next((p for p in world.people.values() if p.name == remanifest_id), None)
            if not match:
                print(f"  unknown person {remanifest_id}", file=sys.stderr)
                return 2
            remanifest_id = match.id
        recon = world.remanifest(remanifest_id)
        print(f"  provenance: {recon['provenance']}")
        print(f"  current_detail: {recon['current_detail']}")
        print(f"  forbidden: {recon['forbidden']}")

    _banner("Canonical History (append-only)")
    for ev in world.timelines.canonical.events:
        print(f"  t{ev.tick:03d} [{ev.kind}] {ev.summary}")

    if world.timelines.experimental:
        _banner("Experimental Branches")
        for br in world.timelines.experimental:
            print(f"  {br.name} id={br.id} fork_tick={br.fork_tick} events={len(br.events)}")

    if show_json and last_result:
        _banner("CycleResult JSON")
        _pp(last_result.to_dict())

    _banner("Done")
    print("One-command research cycle demo complete.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="bitterless",
        description="BitterLess Eastern Zhou Lab — Phase 1 research-cycle demo",
    )
    p.add_argument("--cycles", type=int, default=1, help="number of research cycles (default 1)")
    p.add_argument(
        "--challenge",
        type=str,
        default=None,
        help="player intervention: challenge current hypothesis with this text",
    )
    p.add_argument(
        "--change-focus",
        type=str,
        default=None,
        help="player intervention: change focus dims, e.g. 'medium,institution'",
    )
    p.add_argument("--no-fork", action="store_true", help="skip experimental branch fork")
    p.add_argument(
        "--remanifest",
        type=str,
        default=None,
        help="after cycles, remanifest person by id or name",
    )
    p.add_argument("--json", action="store_true", help="print last CycleResult as JSON")
    p.add_argument(
        "--smoke",
        action="store_true",
        help="minimal smoke: one cycle, no extras (for scripts/CI)",
    )
    return p


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    if args.smoke:
        world = build_seed_world()
        result = run_smoke_cycle(world, fork_experiment=True)
        print("SMOKE_OK", "→".join(result.steps_run), f"tick={result.world_tick}")
        sys.exit(0)
    code = run_demo(
        cycles=args.cycles,
        challenge=args.challenge,
        change_focus=args.change_focus,
        fork=not args.no_fork,
        remanifest_id=args.remanifest,
        show_json=args.json,
    )
    sys.exit(code)


if __name__ == "__main__":
    main()
