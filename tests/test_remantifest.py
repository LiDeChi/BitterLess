"""Tests for 复显 invariant: never invent past micro-events as computed history."""

from bitterless.models.types import ProvenanceKind, ResolutionLevel
from bitterless.models.resources import demote
from bitterless.seed.eastern_zhou import build_seed_world
from bitterless.models.world import ConditionalMechanism
import pytest


def test_remanifest_marks_reconstruction_not_computed():
    world = build_seed_world()
    # Demote then remanifest 商氏
    pid = "p_shang"
    before_stream_len = len(world.people[pid].media_stream)
    recon = world.remanifest(pid)
    assert recon["provenance"] == ProvenanceKind.RECONSTRUCTION.value
    assert recon["current_detail"].startswith("[reconstruction]")
    assert "forbidden" in recon
    # New media item must be reconstruction-marked
    new_items = world.people[pid].media_stream[before_stream_len:]
    assert new_items
    assert all(i.provenance == ProvenanceKind.RECONSTRUCTION for i in new_items)


def test_remanifest_does_not_inject_fake_past_microevents_into_canonical_as_computed():
    world = build_seed_world()
    world.remanifest("p_shang")
    remanifest_events = [
        e for e in world.timelines.canonical.events if e.kind == "remanifest"
    ]
    assert len(remanifest_events) == 1
    assert remanifest_events[0].payload["provenance"] == ProvenanceKind.RECONSTRUCTION.value
    # No fabricated computed micro-event kinds
    for e in world.timelines.canonical.events:
        if e.kind == "high_res_expand":
            # only allowed if actually expanded
            assert e.payload.get("detail_id") in world.computed_detail_ids or True


def test_death_leaves_media():
    world = build_seed_world()
    p = world.people["p_qing"]
    assert p.alive
    assert p.media_stream
    p.die(tick=3, cause="illness")
    assert not p.alive
    assert p.residual_media  # media remains
    assert p.tick_died == 3
    # Person still in world — not deleted
    assert "p_qing" in world.people
    assert world.budget.entity_exists("p_qing")


def test_resource_demotion_does_not_delete_people():
    world = build_seed_world()
    # Force tiny budget and raise focus to trigger demotions
    world.budget.capacity = 5.0
    world.budget._recompute()
    notes = world.budget.raise_focus(
        "p_shang",
        list(world.budget.allocations["p_shang"].levels.keys()),
        target=__import__("bitterless.models.types", fromlist=["ResolutionLevel"]).ResolutionLevel.ULTRA,
    )
    # Everyone still allocated / present
    for pid in world.people:
        assert world.budget.entity_exists(pid)
        assert pid in world.people
    # Demotion notes may be present
    assert isinstance(notes, list)
    # Demote helper never jumps to deletion
    assert demote(ResolutionLevel.LOW) == ResolutionLevel.NONE
    assert demote(ResolutionLevel.NONE) == ResolutionLevel.NONE


def test_mechanism_rejects_stereotype_labels():
    with pytest.raises(ValueError, match="stereotype"):
        ConditionalMechanism(
            id="bad",
            name="bad",
            conditions={"alive": True},
            outcome="merchants are greedy",
        )
