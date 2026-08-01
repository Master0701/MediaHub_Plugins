from pathlib import Path


PLUGIN_FILE = Path(__file__).resolve().parents[1] / "plugin.py"


def test_identity_confirmation_gui_contract():
    text = PLUGIN_FILE.read_text(encoding="utf-8")

    assert "Identität bestätigen und lernen" in text
    assert "def confirm_and_learn_identity(self):" in text
    assert "def show_learning_status(self):" in text
    assert "def reanalyze_current_file(self):" in text
    assert "self.plugin.confirm_and_learn_identity(" in text
    assert "self.plugin.get_learning_status()" in text
    assert "force=True" in text


def test_gui_supports_required_identity_fields():
    text = PLUGIN_FILE.read_text(encoding="utf-8")

    for field in (
        "self.identity_media_type",
        "self.identity_title",
        "self.identity_year",
        "self.identity_season",
        "self.identity_episode",
        "self.identity_edition",
    ):
        assert field in text
