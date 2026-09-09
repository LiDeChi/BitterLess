"""Smoke tests for the full research cycle against the seed world."""

from bitterless.institute.cycle import ResearchCycle, run_smoke_cycle
from bitterless.institute.researcher import PHASES, ResearchThread
from bitterless.models.types import InterventionKind
from bitterless.seed.eastern_zhou import build_seed_world


def test_seed_world_shape():
    world = build_seed_world()
    assert len(world.people) == 4
    assert len(world.channels) == 2
    assert len(world.institutions) == 1
    assert world.timelines.canonical.events
    assert world.timelines.canonical.events[0].kind == "seed"


def test_full_research_cycle_phases():
    world = build_seed_world()
    result = run_smoke_cycle(world, fork_experiment=True)
    assert result.steps_run == [
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
    assert result.world_tick >= 1
    assert result.focus
    assert result.new_problem
    assert result.fork_timeline_id
    assert len(world.timelines.experimental) == 1
    # Canonical grew append-only
    kinds = [e.kind for e in world.timelines.canonical.events]
    assert "seed" in kinds
    assert "low_res_tick" in kinds


def test_player_challenge_hypothesis_without_remote_control():
    world = build_seed_world()
    thread = ResearchThread()
    cycle = ResearchCycle(world=world, thread=thread)
    cycle.queue_intervention(
        InterventionKind.CHALLENGE_HYPOTHESIS,
        "或许关键的是媒介重复频率而非债务本身",
    )
    result = cycle.run()
    assert any(i.kind == InterventionKind.CHALLENGE_HYPOTHESIS for i in thread.interventions)
    assert thread.current_hypothesis and "CHALLENGED" in thread.current_hypothesis
    assert result.steps_run[0] == "problem"
    # Still ran full autonomous cycle — not step-by-step remote control
    assert set(PHASES).issubset(set(result.steps_run) | {"note"})


def test_player_change_focus():
    world = build_seed_world()
    thread = ResearchThread()
    cycle = ResearchCycle(world=world, thread=thread)
    cycle.queue_intervention(InterventionKind.CHANGE_FOCUS, "medium,institution")
    result = cycle.run()
    dims = result.focus.get("dims", [])
    assert "medium" in dims
    assert "institution" in dims


def test_high_res_updates_low_res_via_mechanism():
    world = build_seed_world()
    # Ensure debt condition present
    assert world.people["p_shang"].economy["debt"] >= 1.0
    result = run_smoke_cycle(world)
    # May or may not learn mechanism depending on focus targets; force focus path
    if result.mechanism is None:
        # Run again with economy focus via intervention
        cycle = ResearchCycle(world=world)
        cycle.queue_intervention(InterventionKind.CHANGE_FOCUS, "economy,relation,person")
        result = cycle.run()
    # After focusing on indebted merchant, mechanism should appear
    assert any(m.name == "debt_kin_mediation" for m in world.mechanisms) or result.mechanism
    # Stereotype-free
    for m in world.mechanisms:
        assert "greedy" not in m.outcome.lower()


def test_phases_constant_matches_architecture():
    assert PHASES == [
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
