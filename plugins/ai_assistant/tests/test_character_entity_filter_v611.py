import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.character_entity_filter import CharacterEntityFilter


def test_rejects_sentence_fragment_character():
    assert not CharacterEntityFilter.is_valid_character_name(
        "orm aus dem gefängnis. die beiden treffen sich mit kingfish"
    )


def test_rejects_verb_prefixed_fragment():
    assert not CharacterEntityFilter.is_valid_character_name(
        "befreit arthur"
    )


def test_keeps_valid_character_names():
    assert CharacterEntityFilter.is_valid_character_name(
        "Arthur Curry"
    )
    assert CharacterEntityFilter.is_valid_character_name(
        "Mera"
    )
    assert CharacterEntityFilter.is_valid_character_name(
        "David Kane"
    )


def test_filters_nodes_and_dependent_edges():
    payload = {
        "nodes": [
            {
                "id": "character:arthur-curry",
                "title": "Arthur Curry",
                "node_type": "character",
            },
            {
                "id": "character:befreit-arthur",
                "title": "befreit arthur",
                "node_type": "character",
            },
        ],
        "edges": [
            {
                "edge_type": "friend_of",
                "source_node_key": "character:arthur-curry",
                "target_node_key": "character:befreit-arthur",
            }
        ],
        "summary": {},
    }

    result = CharacterEntityFilter.filter_graph_payload(payload)

    assert len(result["nodes"]) == 1
    assert result["edges"] == []
    assert (
        result["filter_report"]["rejected_character_count"] == 1
    )
    assert result["automatic_import"] is False
