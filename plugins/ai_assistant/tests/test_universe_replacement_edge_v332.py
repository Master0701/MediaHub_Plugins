import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.universe_franchise_builder import UniverseFranchiseBuilder


def test_replaced_by_uses_normalized_node_keys():
    result = UniverseFranchiseBuilder().build(
        main_node={
            "node_type": "movie",
            "title": "Aquaman: Lost Kingdom",
            "confidence": 0.89,
            "metadata": {},
        },
        text=(
            "Es ist der letzte Film des DC Extended Universe, "
            "das 2024 durch das DC Universe ersetzt wurde."
        ),
        source={"id": "wiki"},
    )

    keys = {node["key"] for node in result["nodes"]}

    assert "universe:dc extended universe" in keys
    assert "universe:dc universe" in keys
    assert "universe:der letzte film des dc extended universe" not in keys

    assert any(
        edge["edge_type"] == "replaced_by"
        and edge["source_node_key"] == "universe:dc extended universe"
        and edge["target_node_key"] == "universe:dc universe"
        for edge in result["edges"]
    )


def test_transition_year_remains_on_both_nodes():
    result = UniverseFranchiseBuilder().build(
        main_node={
            "node_type": "movie",
            "title": "Aquaman: Lost Kingdom",
            "confidence": 0.89,
            "metadata": {},
        },
        text=(
            "Es ist der letzte Film des DC Extended Universe, "
            "das 2024 durch das DC Universe ersetzt wurde."
        ),
        source={"id": "wiki"},
    )

    universes = {
        node["key"]: node
        for node in result["nodes"]
        if node["node_type"] == "universe"
    }

    assert (
        universes["universe:dc extended universe"]["metadata"][
            "transition_year"
        ]
        == 2024
    )
    assert (
        universes["universe:dc universe"]["metadata"]["transition_year"]
        == 2024
    )
