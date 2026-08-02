from pathlib import Path


def test_character_relationship_graph_integrated_v600():
    root = Path(__file__).resolve().parents[1]
    text = (root / "plugin.py").read_text(encoding="utf-8")

    assert (
        "from services.character_relationship_graph "
        "import CharacterRelationshipGraph"
        in text
    )
    assert (
        "self.character_relationship_graph = "
        "CharacterRelationshipGraph()"
        in text
    )
    assert (
        "character_relationship_graph = "
        "self.character_relationship_graph.build("
        in text
    )
    assert (
        '"character_relationship_graph": '
        "character_relationship_graph"
        in text
    )
    assert (
        'context.document["character_relationship_graph"] = '
        "character_relationship_graph"
        in text
    )
