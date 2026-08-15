from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEXT = (ROOT / "plugin.py").read_text(encoding="utf-8")


def _block():
    start = TEXT.index("    def _edit_description_dialog(self):")
    end = TEXT.find("\n    def ", start + 10)
    return TEXT[start:end if end != -1 else None]


def test_dialog_imports_qt():
    block = _block()
    assert "from PySide6.QtCore import Qt" in block


def test_dialog_imports_all_used_widgets():
    block = _block()
    for name in ("QDialog", "QDialogButtonBox", "QLabel", "QTextEdit", "QVBoxLayout"):
        assert name in block


def test_dialog_scrollbar_dependencies_are_resolved():
    block = _block()
    assert "Qt.ScrollBarPolicy.ScrollBarAsNeeded" in block
    assert "Qt.ScrollBarPolicy.ScrollBarAlwaysOff" in block
    assert "QTextEdit.LineWrapMode.WidgetWidth" in block


def test_dialog_accept_flow_is_present():
    block = _block()
    assert "dialog.exec() == QDialog.DialogCode.Accepted" in block
    assert "self.description_edit.setPlainText(editor.toPlainText())" in block
    assert "self._sync_description_preview()" in block
    assert "self._update_diff()" in block
