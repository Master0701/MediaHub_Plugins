from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEXT = (ROOT / "plugin.py").read_text(encoding="utf-8")


def _dialog_block():
    start = TEXT.index("    def _edit_description_dialog(self):")
    end = TEXT.find("\n    def ", start + 10)
    return TEXT[start:end if end != -1 else None]


def test_description_dialog_imports_every_local_widget():
    block = _dialog_block()
    for name in ("QDialog", "QDialogButtonBox", "QLabel", "QTextEdit", "QVBoxLayout"):
        assert name in block


def test_description_dialog_uses_qtextedit_after_import():
    block = _dialog_block()
    assert "editor = QTextEdit(dialog)" in block
    assert "editor.setPlainText(self.description_edit.toPlainText())" in block
