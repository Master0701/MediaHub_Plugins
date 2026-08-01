import ast
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN_PATH = ROOT / "plugin.py"


def _text() -> str:
    return PLUGIN_PATH.read_text(encoding="utf-8")


def _version_tuple(text: str) -> tuple[int, int, int]:
    match = re.search(
        r'^\s*VERSION\s*=\s*"(\d+)\.(\d+)\.(\d+)"',
        text,
        flags=re.MULTILINE,
    )
    assert match is not None
    return tuple(int(item) for item in match.groups())


def test_event_intelligence_is_initialized_before_relationships():
    text = _text()

    event_position = text.index(
        "event_intelligence = self.event_intelligence.analyze("
    )
    relationship_position = text.index(
        "character_relationships = ("
    )

    assert event_position < relationship_position


def test_relationship_engine_uses_initialized_identity_map():
    text = _text()

    assert "RelationshipIdentityMapBuilder.build(" in text
    assert "identity_map=relationship_identity_map" in text


def test_no_duplicate_event_initialization_in_scan_method():
    text = _text()
    start = text.index("    def execute_source_scan(")
    end = text.index(
        "    def get_missing_media_handoff_status(",
        start,
    )
    method = text[start:end]

    assert method.count(
        "event_intelligence = self.event_intelligence.analyze("
    ) == 1


def test_plugin_syntax_and_version():
    text = _text()

    ast.parse(text)
    assert _version_tuple(text) >= (4, 1, 0)
