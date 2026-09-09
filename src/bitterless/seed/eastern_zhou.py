"""Tiny Eastern Zhou seed: few people, media channels, one forming institution."""

from __future__ import annotations

from bitterless.models.resources import ResolutionBudget
from bitterless.models.timeline import HistoryEvent, TimelineStore
from bitterless.models.types import FocusDim, ProvenanceKind, ResolutionLevel
from bitterless.models.world import (
    Institution,
    MediumChannel,
    Person,
    Relation,
    WorldState,
)


def build_seed_world(*, budget_capacity: float = 48.0) -> WorldState:
    """
    A minimal Eastern Zhou slice around a small settlement (邑):
    - 4 people (scribe, merchant-in-debt, elder, youth)
    - 2 media channels (oral courtyard, bamboo slip)
    - 1 forming institution (里社 / local ritual-mutual-aid assembly)
    """
    budget = ResolutionBudget(capacity=budget_capacity)
    timelines = TimelineStore()

    people = {
        "p_shang": Person(
            id="p_shang",
            name="商氏",
            role_hint="行商（负债）",
            hard_facts=[
                "商氏自西邑贩盐入此",
                "对里中长老负粮债",
            ],
            coarse_history=["arrived with salt; borrowed grain from elder"],
            location="东门近市",
            economy={"grain": 0.4, "debt": 1.5},
        ),
        "p_lao": Person(
            id="p_lao",
            name="里老",
            role_hint="长老",
            hard_facts=[
                "里老主持季节祭祀",
                "曾借粮给商氏",
            ],
            coarse_history=["lent grain; watches courtyard talk"],
            location="里中",
            economy={"grain": 2.0, "debt": 0.0},
        ),
        "p_shi": Person(
            id="p_shi",
            name="史小",
            role_hint="书手",
            hard_facts=[
                "能书简",
                "记录里中约言",
            ],
            coarse_history=["keeps bamboo slips of oral agreements"],
            location="里中",
            economy={"grain": 1.0, "debt": 0.2},
        ),
        "p_qing": Person(
            id="p_qing",
            name="青",
            role_hint="少年",
            hard_facts=[
                "里老之族侄",
                "常在庭中听闻传言",
            ],
            coarse_history=["listens in courtyard; carries messages"],
            location="庭中",
            economy={"grain": 0.8, "debt": 0.0},
        ),
    }

    for pid in people:
        budget.ensure(pid)
        # Default all dims low
        for dim in FocusDim:
            budget.allocations[pid].set(dim, ResolutionLevel.LOW)

    relations = [
        Relation("p_shang", "p_lao", "debt", strength=0.8, notes="grain debt"),
        Relation("p_lao", "p_qing", "kin", strength=0.7, notes="clan nephew"),
        Relation("p_shi", "p_lao", "service", strength=0.5, notes="records elder's words"),
        Relation("p_qing", "p_shang", "acquaintance", strength=0.3, notes="heard of merchant"),
    ]

    courtyard = MediumChannel(
        id="ch_courtyard",
        name="庭中口传",
        kind="oral",
        reach=["p_shang", "p_lao", "p_shi", "p_qing"],
    )
    slips = MediumChannel(
        id="ch_slips",
        name="书简",
        kind="bamboo_slip",
        reach=["p_shi", "p_lao"],
    )
    channels = {courtyard.id: courtyard, slips.id: slips}

    institution = Institution(
        id="inst_lishe",
        name="里社",
        forming=True,
        norms=["季节共祭", "约言须有见证"],
        member_ids=["p_lao", "p_shi", "p_qing"],
        stage="nascent",
    )

    world = WorldState(
        tick=0,
        people=people,
        relations=relations,
        channels=channels,
        institutions={institution.id: institution},
        budget=budget,
        timelines=timelines,
        low_res_summary={
            "tick": 0,
            "place": "东周小邑（种子）",
            "alive": [p.name for p in people.values()],
            "institutions": [institution.name],
        },
    )

    # Seed media into streams (computed at t=0)
    engine = world.compression
    people["p_shang"].ingest(
        engine,
        "庭中: 有人低声说东门近日查验行人",
        0,
        surprise=0.9,
        social_weight=0.6,
        related_ids=["p_qing"],
        provenance=ProvenanceKind.COMPUTED,
    )
    people["p_shang"].ingest(
        engine,
        "里老派人催问粮债",
        0,
        surprise=0.7,
        social_weight=0.9,
        related_ids=["p_lao"],
    )
    people["p_lao"].ingest(
        engine,
        "商氏仍未还粮",
        0,
        surprise=0.5,
        social_weight=0.7,
        related_ids=["p_shang"],
    )
    people["p_shi"].ingest(
        engine,
        "书简: 记「商氏负里老粮」",
        0,
        surprise=0.3,
        social_weight=0.8,
        related_ids=["p_shang", "p_lao"],
    )
    people["p_qing"].ingest(
        engine,
        "庭中: 听见东门传言",
        0,
        surprise=0.6,
        social_weight=0.4,
        related_ids=["p_shang"],
    )

    # Publish on channels
    courtyard.publish(0, "东门近日或有查验", author_id="p_qing")
    slips.publish(0, "约：商氏负里老粮，待还", author_id="p_shi")

    # Canonical seed event
    timelines.canonical.append(
        HistoryEvent.new(
            0,
            "seed",
            "Eastern Zhou micro-seed loaded: 4 people, 2 channels, 1 forming 里社",
            payload={"people": list(people.keys()), "institution": institution.id},
            actor_ids=list(people.keys()),
        )
    )

    # Register institution & channels sparsely (not full 7-dim low — saves budget)
    budget.ensure(institution.id)
    for dim in FocusDim:
        budget.allocations[institution.id].set(dim, ResolutionLevel.NONE)
    budget.allocations[institution.id].set(FocusDim.INSTITUTION, ResolutionLevel.LOW)
    for cid in channels:
        budget.ensure(cid)
        for dim in FocusDim:
            budget.allocations[cid].set(dim, ResolutionLevel.NONE)
        budget.allocations[cid].set(FocusDim.MEDIUM, ResolutionLevel.LOW)
    budget._recompute()

    return world
