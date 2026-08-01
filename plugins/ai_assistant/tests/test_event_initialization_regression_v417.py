import ast
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN_PATH = ROOT / "plugin.py"


def _text() -> str:
    return PLUGIN_PATH.read_text(encoding="utf-8")


def _version_tuple() -> tuple[int, int, int]:
    match = re.search(
        r'^\s*VERSION\s*=\s*"(\d+)\.(\d+)\.(\d+)"',
        _text(),
        flags=re.MULTILINE,
    )
    assert match is not None
    return tuple(int(item) for item in match.groups())


def test_event_intelligence_is_initialized_before_identity_fusion():
    text = _text()

    event_position = text.index(
        "event_intelligence = self.event_intelligence.analyze("
    )
    fusion_position = text.index(
        "relationship_identity_map = ("
    )

    assert event_position < fusion_position


def test_identity_fusion_uses_event_and_cast_results():
    text = _text()

    assert "RelationshipIdentityMapBuilder.build(" in text
    assert "event_intelligence=event_intelligence" in text
    assert "cast_resolution=cast_resolution" in text


def test_relationship_engine_receives_fused_identity_map():
    text = _text()

    assert "identity_map=relationship_identity_map" in text


def test_plugin_syntax_and_compatible_version():
    text = _text()

    ast.parse(text)
    assert _version_tuple() >= (4, 1, 0)
