import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.relationship_identity_map_builder import (
    RelationshipIdentityMapBuilder,
)


def test_event_and_cast_maps_are_fused():
    result = RelationshipIdentityMapBuilder.build(
        event_intelligence={
            "identity_resolution": {
                "alias_map": {
                    "arthur": "Arthur Curry",
                    "david": "David Kane",
                }
            }
        },
        cast_resolution={
            "nodes": [
                {
                    "node_type": "character",
                    "title": "Orm Marius",
                    "metadata": {
                        "raw_role_name": "Orm Marius",
                    },
                }
            ]
        },
    )

    assert result["arthur"] == "Arthur Curry"
    assert result["david"] == "David Kane"
    assert result["orm"] == "Orm Marius"


def test_cast_identity_overrides_weaker_event_guess():
    result = RelationshipIdentityMapBuilder.build(
        event_intelligence={
            "identity_resolution": {
                "alias_map": {
                    "orm": "Wilsons Orm",
                }
            }
        },
        cast_resolution={
            "nodes": [
                {
                    "node_type": "character",
                    "title": "Orm Marius",
                    "metadata": {
                        "raw_role_name": "Orm Marius",
                    },
                }
            ]
        },
    )

    assert result["orm"] == "Orm Marius"


def test_unsafe_event_aliases_are_filtered():
    result = RelationshipIdentityMapBuilder.build(
        event_intelligence={
            "identity_resolution": {
                "alias_map": {
                    "titel": "Titel Aquaman",
                    "in": "In Necrus",
                    "warner": "Warner Bros",
                    "stab": "Stab Regie",
                    "arthur": "Arthur Curry",
                }
            }
        },
        cast_resolution={},
    )

    assert result == {"arthur": "Arthur Curry"}


def test_role_alias_is_added_from_cast_metadata():
    result = RelationshipIdentityMapBuilder.build(
        event_intelligence={},
        cast_resolution={
            "nodes": [
                {
                    "node_type": "character",
                    "title": "Arthur Curry",
                    "metadata": {
                        "raw_role_name": "Arthur Curry / Aquaman",
                    },
                }
            ]
        },
    )

    assert result["arthur"] == "Arthur Curry"
    assert result["aquaman"] == "Arthur Curry"
