import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.character_cast_resolver import CharacterCastResolver

def test_alias_split_and_relations():
    result = CharacterCastResolver().resolve(
        main_node={
            "node_type": "movie",
            "title": "Aquaman: Lost Kingdom",
            "confidence": 0.89,
            "metadata": {},
        },
        text="Besetzung Jason Momoa : Arthur Curry / Aquaman Chronologie",
        source={"id": "wiki"},
    )
    keys = {n["key"] for n in result["nodes"]}
    types = {e["edge_type"] for e in result["edges"]}
    assert "person:jason momoa" in keys
    assert "character:arthur curry" in keys
    assert "character_alias:aquaman" in keys
    assert {"portrayed_by", "appears_in", "alias_of"} <= types

def test_simple_role_has_no_alias():
    result = CharacterCastResolver().resolve(
        main_node={
            "node_type": "movie",
            "title": "Aquaman: Lost Kingdom",
            "confidence": 0.89,
            "metadata": {},
        },
        text="Besetzung Patrick Wilson : Orm Marius Chronologie",
        source={"id": "wiki"},
    )
    assert not any(n["node_type"] == "character_alias" for n in result["nodes"])
