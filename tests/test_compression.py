"""Tests for media compression ladder: raw → event → episode → pattern → belief."""

from bitterless.models.compression import CompressionEngine, MediaItem
from bitterless.models.types import CompressionTier


def test_ingest_raw_appends_active_raw():
    engine = CompressionEngine()
    stream: list[MediaItem] = []
    item = engine.ingest_raw(stream, "张三进门低声提醒", tick=0, surprise=0.8)
    assert item.tier == CompressionTier.RAW
    assert item.active
    assert len(stream) == 1


def test_raw_promotes_to_event_when_aged():
    engine = CompressionEngine(age_thresholds={
        CompressionTier.RAW: 2,
        CompressionTier.EVENT: 5,
        CompressionTier.EPISODE: 12,
        CompressionTier.PATTERN: 30,
    })
    stream: list[MediaItem] = []
    engine.ingest_raw(stream, "msg-a", tick=0, surprise=0.2)
    created = engine.compress(stream, current_tick=2)
    assert len(created) == 1
    assert created[0].tier == CompressionTier.EVENT
    assert stream[0].active is False  # raw deactivated
    assert created[0].active is True


def test_multiple_events_compress_to_episode():
    engine = CompressionEngine(age_thresholds={
        CompressionTier.RAW: 1,
        CompressionTier.EVENT: 2,
        CompressionTier.EPISODE: 99,
        CompressionTier.PATTERN: 99,
    })
    stream: list[MediaItem] = []
    # Two related raws at t=0
    engine.ingest_raw(stream, "A: warn east gate", tick=0, surprise=0.2, related_ids=["p1"])
    engine.ingest_raw(stream, "A: warn again", tick=0, surprise=0.2, related_ids=["p1"])
    # First pass: raw → event
    engine.compress(stream, current_tick=1)
    events = [m for m in stream if m.active and m.tier == CompressionTier.EVENT]
    assert len(events) >= 1
    # Age events and compress again → episode
    created = engine.compress(stream, current_tick=4)
    episodes = [m for m in created if m.tier == CompressionTier.EPISODE]
    assert len(episodes) >= 1
    assert "episode" in episodes[0].content


def test_high_surprise_kept_alone():
    engine = CompressionEngine(keep_alone_threshold=1.5, age_thresholds={
        CompressionTier.RAW: 1,
        CompressionTier.EVENT: 99,
        CompressionTier.EPISODE: 99,
        CompressionTier.PATTERN: 99,
    })
    stream: list[MediaItem] = []
    engine.ingest_raw(stream, "shocking news", tick=0, surprise=2.0, social_weight=0.5)
    created = engine.compress(stream, current_tick=5)
    # Too important to auto-compress alone
    assert created == []
    assert stream[0].active and stream[0].tier == CompressionTier.RAW


def test_active_by_tier_counts():
    engine = CompressionEngine()
    stream: list[MediaItem] = []
    engine.ingest_raw(stream, "a", tick=0)
    engine.ingest_raw(stream, "b", tick=0)
    by = engine.active_by_tier(stream)
    assert by["raw"] == stream
    assert by["belief"] == []
