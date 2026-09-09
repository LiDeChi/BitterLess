"""Tests for append-only Canonical History and experimental forks."""

import pytest

from bitterless.models.timeline import AppendOnlyViolation, HistoryEvent, Timeline, TimelineStore
from bitterless.models.types import TimelineKind


def test_canonical_append_only_allows_forward_append():
    tl = Timeline(kind=TimelineKind.CANONICAL, name="正史")
    e1 = HistoryEvent.new(0, "seed", "start")
    e2 = HistoryEvent.new(1, "tick", "t1")
    tl.append(e1)
    tl.append(e2)
    assert len(tl.events) == 2


def test_canonical_rejects_backdated_append():
    tl = Timeline(kind=TimelineKind.CANONICAL, name="正史")
    tl.append(HistoryEvent.new(5, "tick", "t5"))
    with pytest.raises(AppendOnlyViolation):
        tl.append(HistoryEvent.new(3, "tick", "t3"))


def test_canonical_rejects_rewrite():
    tl = Timeline(kind=TimelineKind.CANONICAL, name="正史")
    tl.append(HistoryEvent.new(0, "seed", "start"))
    with pytest.raises(AppendOnlyViolation):
        tl.rewrite_forbidden(0, HistoryEvent.new(0, "seed", "rewritten"))


def test_canonical_rejects_truncate():
    tl = Timeline(kind=TimelineKind.CANONICAL, name="正史")
    tl.append(HistoryEvent.new(0, "seed", "start"))
    tl.append(HistoryEvent.new(1, "tick", "t1"))
    with pytest.raises(AppendOnlyViolation):
        tl.truncate_from(1)


def test_experimental_fork_copies_prefix():
    store = TimelineStore()
    store.canonical.append(HistoryEvent.new(0, "seed", "start"))
    store.canonical.append(HistoryEvent.new(1, "tick", "t1"))
    store.canonical.append(HistoryEvent.new(2, "tick", "t2"))
    branch = store.fork_experiment("exp-A", at_tick=1)
    assert branch.kind == TimelineKind.EXPERIMENTAL
    assert branch.fork_tick == 1
    assert len(branch.events) == 2
    assert [e.tick for e in branch.events] == [0, 1]
    # Mutating branch must not rewrite canonical
    branch.truncate_from(1)
    assert len(branch.events) == 1
    assert len(store.canonical.events) == 3


def test_sandbox_is_independent():
    store = TimelineStore()
    store.canonical.append(HistoryEvent.new(0, "seed", "start"))
    sb = store.new_sandbox("debug")
    sb.append(HistoryEvent.new(99, "debug", "probe"))
    assert len(store.canonical.events) == 1
    assert store.sandboxes[0].events[0].tick == 99
