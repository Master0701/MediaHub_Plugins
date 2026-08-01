from pathlib import Path


PLUGIN_FILE = Path(__file__).resolve().parents[1] / "plugin.py"


def test_group_membership_proposals_are_supported():
    text = PLUGIN_FILE.read_text(encoding="utf-8")

    assert 'elif kind == "group_membership":' in text
    assert '"universe"' in text
    assert '"franchise"' in text
    assert "group_membership" in text


def test_group_entity_is_upserted_before_relation():
    text = PLUGIN_FILE.read_text(encoding="utf-8")

    upsert_pos = text.index(
        "group_result = self.knowledge_engine.upsert_identity("
    )
    connect_pos = text.index(
        "result = self.knowledge_engine.connect_confirmed(",
        upsert_pos,
    )

    assert upsert_pos < connect_pos
    assert 'source="proposal_queue"' in text
    assert "confirmed_by_user=True" in text
