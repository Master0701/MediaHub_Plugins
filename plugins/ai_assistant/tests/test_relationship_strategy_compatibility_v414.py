import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.character_relationship_engine import CharacterRelationshipEngine


def test_current_relationship_strategy_is_v4_compatible():
    result = CharacterRelationshipEngine.analyze(
        text="Arthur heiratete Mera.",
        source={"id": "wiki"},
        identity_map={"arthur": "Arthur Curry"},
    )

    assert result["strategy"].startswith(
        "character_relationship_engine_v4"
    )


def test_productive_strategy_remains_v413():
    result = CharacterRelationshipEngine.analyze(
        text="Arthur heiratete Mera.",
        source={"id": "wiki"},
        identity_map={"arthur": "Arthur Curry"},
    )

    assert result["strategy"] == "character_relationship_engine_v413"
