import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.character_role_intelligence import CharacterRoleIntelligence


def test_detects_actor_character_and_media_edges():
    result = CharacterRoleIntelligence.analyze(
        main_node={"key": "movie:aquaman lost kingdom", "node_type": "movie", "title": "Aquaman Lost Kingdom"},
        text="Jason Momoa: Arthur Curry / Aquaman\nPatrick Wilson: Orm Marius",
        source={"id": "source-1"},
    )
    edge_types = {item["edge_type"] for item in result["edges"]}
    titles = {item["title"] for item in result["nodes"]}
    assert {"portrays", "appears_in", "alias_of"} <= edge_types
    assert {"Jason Momoa", "Arthur Curry", "Aquaman", "Patrick Wilson", "Orm Marius"} <= titles
    assert result["automatic_import"] is False
    assert result["requires_confirmation"] is True


def test_detects_german_sentence_form():
    result = CharacterRoleIntelligence.analyze(
        main_node={"key": "series:ncis", "node_type": "series", "title": "NCIS"},
        text="Mark Harmon spielt die Rolle von Leroy Jethro Gibbs.",
        source={"id": "source-2"},
    )
    assert any(item["edge_type"] == "portrays" for item in result["edges"])
