"""Media compression ladder: raw → event → episode → pattern → belief."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from bitterless.models.types import CompressionTier, ProvenanceKind


@dataclass
class MediaItem:
    """One item on a character's internal compression ladder."""

    id: str
    tier: CompressionTier
    content: str
    tick: int
    surprise: float = 0.0
    social_weight: float = 0.0
    related_ids: list[str] = field(default_factory=list)
    provenance: ProvenanceKind = ProvenanceKind.COMPUTED
    source_ids: list[str] = field(default_factory=list)  # lower-tier items compressed into this
    active: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "tier": self.tier.value,
            "content": self.content,
            "tick": self.tick,
            "surprise": self.surprise,
            "social_weight": self.social_weight,
            "related_ids": list(self.related_ids),
            "provenance": self.provenance.value,
            "source_ids": list(self.source_ids),
            "active": self.active,
        }

    @staticmethod
    def new(
        tier: CompressionTier,
        content: str,
        tick: int,
        *,
        surprise: float = 0.0,
        social_weight: float = 0.0,
        related_ids: list[str] | None = None,
        provenance: ProvenanceKind = ProvenanceKind.COMPUTED,
        source_ids: list[str] | None = None,
    ) -> MediaItem:
        return MediaItem(
            id=str(uuid4()),
            tier=tier,
            content=content,
            tick=tick,
            surprise=surprise,
            social_weight=social_weight,
            related_ids=list(related_ids or []),
            provenance=provenance,
            source_ids=list(source_ids or []),
        )


# Age thresholds (in ticks) before a tier is eligible for compression upward.
DEFAULT_AGE_THRESHOLDS: dict[CompressionTier, int] = {
    CompressionTier.RAW: 2,
    CompressionTier.EVENT: 5,
    CompressionTier.EPISODE: 12,
    CompressionTier.PATTERN: 30,
}

TIER_ORDER = [
    CompressionTier.RAW,
    CompressionTier.EVENT,
    CompressionTier.EPISODE,
    CompressionTier.PATTERN,
    CompressionTier.BELIEF,
]

NEXT_TIER = {
    CompressionTier.RAW: CompressionTier.EVENT,
    CompressionTier.EVENT: CompressionTier.EPISODE,
    CompressionTier.EPISODE: CompressionTier.PATTERN,
    CompressionTier.PATTERN: CompressionTier.BELIEF,
}


def _importance(item: MediaItem) -> float:
    return item.surprise + item.social_weight


def _summarize(items: list[MediaItem], next_tier: CompressionTier) -> str:
    """Deterministic compression summary — no invented micro-events."""
    texts = [i.content for i in items]
    if next_tier == CompressionTier.EVENT:
        return " / ".join(texts)
    if next_tier == CompressionTier.EPISODE:
        subjects = sorted({t.split(":")[0].strip() if ":" in t else t[:12] for t in texts})
        return f"episode involving {', '.join(subjects)} ({len(items)} events)"
    if next_tier == CompressionTier.PATTERN:
        return f"recurring pattern: {texts[0][:40]}… ×{len(items)}"
    # BELIEF
    return f"belief distilled from {len(items)} patterns: {texts[0][:48]}"


@dataclass
class CompressionEngine:
    """Compresses a character's media stream over time."""

    age_thresholds: dict[CompressionTier, int] = field(
        default_factory=lambda: dict(DEFAULT_AGE_THRESHOLDS)
    )
    # High-importance items stay at their tier longer / never auto-merge alone.
    keep_alone_threshold: float = 1.5

    def ingest_raw(
        self,
        stream: list[MediaItem],
        content: str,
        tick: int,
        *,
        surprise: float = 0.0,
        social_weight: float = 0.0,
        related_ids: list[str] | None = None,
        provenance: ProvenanceKind = ProvenanceKind.COMPUTED,
    ) -> MediaItem:
        item = MediaItem.new(
            CompressionTier.RAW,
            content,
            tick,
            surprise=surprise,
            social_weight=social_weight,
            related_ids=related_ids,
            provenance=provenance,
        )
        stream.append(item)
        return item

    def compress(self, stream: list[MediaItem], current_tick: int) -> list[MediaItem]:
        """Run one compression pass; returns newly created higher-tier items."""
        created: list[MediaItem] = []
        for tier in TIER_ORDER[:-1]:
            next_tier = NEXT_TIER[tier]
            threshold = self.age_thresholds.get(tier, 9999)
            candidates = [
                m
                for m in stream
                if m.active
                and m.tier == tier
                and (current_tick - m.tick) >= threshold
                and _importance(m) < self.keep_alone_threshold
            ]
            if not candidates:
                continue
            if tier != CompressionTier.RAW and len(candidates) < 2:
                # Need at least 2 to form episode/pattern/belief
                continue

            # raw→event: promote each item individually (preserve micro-detail).
            # Higher tiers: group by relatedness / chronological chunks.
            if tier == CompressionTier.RAW:
                groups = [[c] for c in candidates]
            else:
                groups = self._group(candidates)
            for group in groups:
                if tier == CompressionTier.RAW:
                    src = group[0]
                    higher = MediaItem.new(
                        next_tier,
                        src.content,
                        current_tick,
                        surprise=src.surprise,
                        social_weight=src.social_weight,
                        related_ids=src.related_ids,
                        provenance=src.provenance,
                        source_ids=[src.id],
                    )
                elif len(group) < 2:
                    continue
                else:
                    higher = MediaItem.new(
                        next_tier,
                        _summarize(group, next_tier),
                        current_tick,
                        surprise=max(g.surprise for g in group),
                        social_weight=max(g.social_weight for g in group),
                        related_ids=sorted({rid for g in group for rid in g.related_ids}),
                        provenance=ProvenanceKind.COMPUTED,
                        source_ids=[g.id for g in group],
                    )
                for g in group:
                    g.active = False
                stream.append(higher)
                created.append(higher)
        return created

    def _group(self, items: list[MediaItem]) -> list[list[MediaItem]]:
        """Simple greedy grouping by shared related_ids, else chronological chunks."""
        unused = list(items)
        groups: list[list[MediaItem]] = []
        while unused:
            seed = unused.pop(0)
            group = [seed]
            seed_rels = set(seed.related_ids)
            i = 0
            while i < len(unused):
                other = unused[i]
                if seed_rels and seed_rels.intersection(other.related_ids):
                    group.append(unused.pop(i))
                else:
                    i += 1
            # If no relatedness, take up to 3 chronological neighbors as a chunk.
            if len(group) == 1 and unused:
                extra = unused[:2]
                unused = unused[2:]
                group.extend(extra)
            groups.append(group)
        return groups

    def active_by_tier(self, stream: list[MediaItem]) -> dict[str, list[MediaItem]]:
        out: dict[str, list[MediaItem]] = {t.value: [] for t in CompressionTier}
        for m in stream:
            if m.active:
                out[m.tier.value].append(m)
        return out
