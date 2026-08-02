from pathlib import Path


def test_character_entity_filter_integrated_v601():
    root = Path(__file__).resolve().parents[1]
    text = (root / "plugin.py").read_text(encoding="utf-8")

    assert (
        "from services.character_entity_filter "
        "import CharacterEntityFilter"
        in text
    )
    assert (
        "character_relationship_graph = "
        "CharacterEntityFilter.filter_graph_payload("
        in text
    )
