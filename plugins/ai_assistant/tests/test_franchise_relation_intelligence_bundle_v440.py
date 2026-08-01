import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.franchise_relation_intelligence import (
    FranchiseRelationIntelligence,
)


SOURCE = {"id": "wiki"}
MAIN = {
    "key": "movie:example sequel:2024",
    "node_type": "movie",
    "title": "Example Sequel",
    "year": 2024,
}


def analyze(text, main=None, relationship=None, franchise=None):
    return FranchiseRelationIntelligence.analyze(
        main_node=main or MAIN,
        text=text,
        source=SOURCE,
        relationship_proposal=relationship or {"edges": []},
        franchise_collection=franchise or {},
    )


def edge_types(result):
    return {
        edge["edge_type"]
        for edge in result["edges"]
    }


def test_sequel_relation():
    result = analyze(
        "Der Film ist die Fortsetzung von Example aus dem Jahr 2020."
    )

    assert "sequel_of" in edge_types(result)
    assert any(
        node["key"] == "movie:example:2020"
        for node in result["nodes"]
    )


def test_prequel_relation():
    result = analyze(
        "Der Film ist ein Prequel zu Example."
    )

    assert "prequel_of" in edge_types(result)


def test_midquel_relation():
    result = analyze(
        "Der Film ist ein Midquel zu Example."
    )

    assert "midquel_of" in edge_types(result)


def test_spin_off_relation():
    result = analyze(
        "Die Serie ist ein Spin-off von Example."
    )

    assert "spin_off_of" in edge_types(result)


def test_crossover_relation():
    result = analyze(
        "Der Film ist ein Crossover mit Other Series."
    )

    assert "crossover_with" in edge_types(result)


def test_reboot_relation():
    result = analyze(
        "Der Film ist ein Reboot von Example."
    )

    assert "reboot_of" in edge_types(result)


def test_soft_reboot_relation():
    result = analyze(
        "Der Film ist ein Soft-Reboot von Example."
    )

    assert "soft_reboot_of" in edge_types(result)


def test_remake_relation():
    result = analyze(
        "Der Film ist ein Remake von Example."
    )

    assert "remake_of" in edge_types(result)


def test_directors_cut_relation_from_title():
    result = analyze(
        "",
        main={
            "key": "movie:example directors cut:2020",
            "node_type": "movie",
            "title": "Example: Director's Cut",
            "year": 2020,
        },
    )

    assert "directors_cut_of" in edge_types(result)


def test_extended_cut_relation():
    result = analyze(
        "Dies ist der Extended Cut.",
        main={
            "key": "movie:example extended:2020",
            "node_type": "movie",
            "title": "Example: Extended Cut",
            "year": 2020,
        },
    )

    assert "extended_cut_of" in edge_types(result)


def test_uncut_relation():
    result = analyze(
        "Die ungekürzte Veröffentlichung wird als Uncut bezeichnet.",
        main={
            "key": "movie:example uncut:2020",
            "node_type": "movie",
            "title": "Example: Uncut",
            "year": 2020,
        },
    )

    assert "uncut_version_of" in edge_types(result)


def test_remaster_relation():
    result = analyze(
        "Eine remastered Fassung wurde veröffentlicht.",
        main={
            "key": "movie:example remastered:2020",
            "node_type": "movie",
            "title": "Example: Remastered",
            "year": 2020,
        },
    )

    assert "remaster_of" in edge_types(result)


def test_canon_status():
    result = analyze(
        "Die Geschichte gilt als kanonisch."
    )

    assert "has_canon_status" in edge_types(result)
    assert any(
        node["key"] == "canon:canon"
        for node in result["nodes"]
    )


def test_non_canon_status():
    result = analyze(
        "Die Geschichte ist non-canon."
    )

    assert any(
        node["key"] == "canon:non-canon"
        for node in result["nodes"]
    )


def test_alternate_timeline():
    result = analyze(
        "Die Handlung spielt in einer alternative Zeitlinie."
    )

    assert "belongs_to_timeline" in edge_types(result)
    assert any(
        node["key"] == "timeline:alternate-timeline"
        for node in result["nodes"]
    )


def test_parallel_universe():
    result = analyze(
        "Die Geschichte spielt in einem parallelen Universum."
    )

    assert any(
        node["key"] == "timeline:parallel-universe"
        for node in result["nodes"]
    )


def test_prime_timeline():
    result = analyze(
        "Die Serie gehört zur Prime Timeline."
    )

    assert any(
        node["key"] == "timeline:prime-timeline"
        for node in result["nodes"]
    )


def test_kelvin_timeline():
    result = analyze(
        "Der Film spielt in der Kelvin Timeline."
    )

    assert any(
        node["key"] == "timeline:kelvin-timeline"
        for node in result["nodes"]
    )


def test_existing_relationship_is_preserved():
    result = analyze(
        "",
        relationship={
            "edges": [{
                "edge_type": "sequel_of",
                "source_node_key": MAIN["key"],
                "target_node_key": "movie:example:2020",
            }]
        },
    )

    assert "sequel_of" in edge_types(result)


def test_franchise_membership_is_inherited():
    result = analyze(
        "",
        franchise={"franchise_key": "franchise:example"},
    )

    assert any(
        edge["edge_type"] == "installment_of"
        and edge["target_node_key"] == "franchise:example"
        for edge in result["edges"]
    )


def test_duplicate_relations_are_removed():
    result = analyze(
        "Der Film ist die Fortsetzung von Example aus dem Jahr 2020. "
        "Der Film ist die Fortsetzung von Example aus dem Jahr 2020."
    )

    sequel_edges = [
        edge
        for edge in result["edges"]
        if edge["edge_type"] == "sequel_of"
    ]

    assert len(sequel_edges) == 1


def test_no_automatic_import():
    result = analyze("Der Film ist ein Remake von Example.")

    assert result["automatic_import"] is False
    assert result["requires_confirmation"] is True
    assert all(
        edge["requires_confirmation"] is True
        for edge in result["edges"]
    )


def test_strategy_and_counts():
    result = analyze(
        "Der Film ist ein Reboot von Example. "
        "Die Geschichte ist non-canon."
    )

    assert result["strategy"].startswith(
        "franchise_relation_intelligence_v"
    )
    assert result["edge_count"] >= 2
    assert result["node_count"] >= 2
