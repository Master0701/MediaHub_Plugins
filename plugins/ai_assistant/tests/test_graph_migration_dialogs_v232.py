from pathlib import Path


PLUGIN_FILE = Path(__file__).resolve().parents[1] / "plugin.py"


def test_long_dialogs_use_scrollable_text_window():
    text = PLUGIN_FILE.read_text(encoding="utf-8")

    assert "def show_scrollable_text_dialog(" in text
    assert "QPlainTextEdit(dialog)" in text
    assert "dialog.resize(width, height)" in text
    assert 'self.show_scrollable_text_dialog(\n            "Knowledge-Graph-Status"' in text
    assert 'self.show_scrollable_text_dialog(\n            "Lernstatus"' in text


def test_existing_learning_is_migrated_to_graph():
    text = PLUGIN_FILE.read_text(encoding="utf-8")

    assert "def migrate_learned_identities_to_graph(self):" in text
    assert "self.knowledge_learning.export_snapshot()" in text
    assert 'source="learning_database_migration"' in text
    assert '"migration": migration' in text


def test_graph_view_reports_migration_counts():
    text = PLUGIN_FILE.read_text(encoding="utf-8")

    assert "Gelernte Identitäten geprüft:" in text
    assert "Davon neu in den Graph übernommen:" in text
