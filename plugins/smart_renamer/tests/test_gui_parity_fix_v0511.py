from pathlib import Path
from types import SimpleNamespace
import json

from services.web_picker_service import WindowsWebPathPicker


def test_picker_uses_helper_script(monkeypatch, tmp_path: Path):
    helper = tmp_path / "picker.ps1"
    helper.write_text("# test", encoding="utf-8")
    calls = []

    def runner(args, **kwargs):
        calls.append((args, kwargs))
        return SimpleNamespace(returncode=0, stdout='["C:\\\\Film.mkv"]')

    picker = WindowsWebPathPicker(helper, runner=runner)
    monkeypatch.setattr("services.web_picker_service.os.name", "nt")

    assert picker.pick_files() == [r"C:\Film.mkv"]
    args = calls[0][0]
    assert "-STA" in args
    assert "-File" in args
    assert str(helper) in args
    assert "files" in args


def test_picker_compatibility_with_injected_runner(monkeypatch):
    fake = SimpleNamespace(returncode=0, stdout='["C:\\\\A.mkv","D:\\\\B.mkv"]')
    picker = WindowsWebPathPicker(runner=lambda *a, **k: fake)
    monkeypatch.setattr("services.web_picker_service.os.name", "nt")
    assert picker.pick_files() == [r"C:\A.mkv", r"D:\B.mkv"]


def test_picker_helper_is_topmost():
    root = Path(__file__).resolve().parents[1]
    helper = (root / "tools" / "web_path_picker.ps1").read_text(encoding="utf-8-sig")
    assert "$owner.TopMost = $true" in helper
    assert "OpenFileDialog" in helper
    assert "FolderBrowserDialog" in helper


def test_desktop_layout_moves_preview_left_and_preserves_right():
    plugin = (Path(__file__).resolve().parents[1] / "plugin.py").read_text(encoding="utf-8")
    assert "left.setMinimumWidth(145)" in plugin
    assert "right.setMinimumWidth(310)" in plugin
    assert "outer.setSizes([160, 850, 360])" in plugin
    assert "outer.setStretchFactor(2,3)" in plugin


def test_desktop_has_more_web_features():
    plugin = (Path(__file__).resolve().parents[1] / "plugin.py").read_text(encoding="utf-8")
    for text in (
        "self.preview_search",
        "self.preview_status_filter",
        "self.preview_sort",
        "Auswahl übernehmen",
        "Auswahl ignorieren",
        "Auswahl prüfen",
        "self.preview_details",
        "Keine Datei wurde verändert.",
    ):
        assert text in plugin


def test_web_picker_gives_visible_feedback():
    html = (Path(__file__).resolve().parents[1] / "index.html").read_text(encoding="utf-8")
    assert "Auswahl abgebrochen oder kein Pfad gewählt." in html
    assert "Dateiauswahl" in html
    assert "Ordnerauswahl" in html


def test_plugin_version_stays_0510():
    data = json.loads((Path(__file__).resolve().parents[1] / "plugin.json").read_text(encoding="utf-8"))
    assert data["version"] == "0.5.11"
