from pathlib import Path


PLUGIN = Path(__file__).resolve().parents[1] / "plugin.py"


def test_source_selection_is_clearly_labeled_and_connected():
    text = PLUGIN.read_text(encoding="utf-8")

    assert '"Vorhandene Quelle auswählen:"' in text
    assert "self.source_select.currentIndexChanged.connect(" in text
    assert "self.load_selected_source_gui" in text


def test_selected_source_populates_form():
    text = PLUGIN.read_text(encoding="utf-8")

    assert "def load_selected_source_gui(self, _index=None):" in text
    assert "self.source_url.setText(" in text
    assert "self.source_category.setText(" in text
    assert "self.source_enabled.setChecked(" in text


def test_source_management_actions_exist():
    text = PLUGIN.read_text(encoding="utf-8")

    assert 'QPushButton("Neue Quelle")' in text
    assert 'QPushButton("Änderungen speichern")' in text
    assert 'QPushButton("Ausgewählte Quelle löschen")' in text
    assert "def save_selected_source_gui(self):" in text
    assert "def delete_selected_source_gui(self):" in text


def test_system_sources_are_protected_from_delete():
    text = PLUGIN.read_text(encoding="utf-8")

    assert "Vordefinierte Quellen können nicht gelöscht werden" in text
    assert "self.plugin.remove_source(source_id)" in text
