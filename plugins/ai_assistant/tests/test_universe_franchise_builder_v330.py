import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.universe_franchise_builder import UniverseFranchiseBuilder

def test_universe_and_replacement():
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
    keys = {n["key"] for n in result["nodes"]}
    types = {e["edge_type"] for e in result["edges"]}
    assert "universe:dc extended universe" in keys
    assert "universe:dc universe" in keys
    assert "belongs_to" in types
    assert "replaced_by" in types

def test_location_relation():
    result = UniverseFranchiseBuilder().build(
        main_node={
            "node_type": "character",
            "title": "Aquaman",
            "confidence": 0.8,
            "metadata": {},
        },
        text="Aquaman ist König von Atlantis.",
        source={"id": "wiki"},
    )
    assert any(e["edge_type"] == "located_in" for e in result["edges"])
