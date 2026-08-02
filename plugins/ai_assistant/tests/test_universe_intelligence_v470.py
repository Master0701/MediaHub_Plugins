import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from services.universe_intelligence import UniverseIntelligence


def _analyze(text: str):
    return UniverseIntelligence.analyze(
        main_node={"key": "movie:aquaman-lost-kingdom", "node_type": "movie", "title": "Aquaman: Lost Kingdom"},
        text=text,
        source={"id": "source-1"},
    )


def test_detects_explicit_universe_membership():
    result = _analyze("Es ist der 15. und letzte Film des DC Extended Universe, das 2024 ersetzt wurde.")
    assert any(n["node_type"] == "universe" and n["title"] == "DC Extended Universe" for n in result["nodes"])
    assert any(e["edge_type"] == "belongs_to_universe" for e in result["edges"])


def test_detects_timeline_and_canon():
    result = _analyze("Der Film gehört zur Kelvin Timeline und ist kanonisch.")
    assert {e["edge_type"] for e in result["edges"]} >= {"belongs_to_timeline", "part_of_canon"}


def test_detects_non_canon_before_canon():
    result = _analyze("Die Produktion ist nicht kanonisch und gehört nicht zum Kanon.")
    types = {e["edge_type"] for e in result["edges"]}
    assert "non_canon" in types
    assert "part_of_canon" not in types


def test_detects_reboot_relationship():
    result = _analyze("Die Serie ist ein Reboot von Battlestar Galactica.")
    assert any(e["edge_type"] == "reboot_of" for e in result["edges"])
    assert result["automatic_import"] is False
    assert result["requires_confirmation"] is True

