from pathlib import Path
from types import SimpleNamespace

from services.preview_presentation import PreviewPresentationService
from services.web_picker_service import WindowsWebPathPicker


def test_preview_presentation_adds_relation_confidence_review():
    result = {
        "preview_rows": [{
            "source_path": r"C:\Serie\S01E01.mkv",
            "original_name": "S01E01.mkv",
            "proposed_name": "Show - S01E01.mkv",
        }],
        "media_items": [{
            "path": r"C:\Serie\S01E01.mkv",
            "media_type": "series",
            "season": "01",
            "episode": "01",
            "detection_data": {
                "media_relation": {
                    "relation_type": "single",
                    "confidence": 0.94,
                    "review_required": False,
                }
            },
        }],
    }
    row = PreviewPresentationService().enrich(result)["preview_rows"][0]
    assert row["relation_type"] == "single"
    assert row["confidence"] == 0.94
    assert row["review_required"] is False
    assert row["season"] == "01"


def test_preview_presentation_marks_review():
    result = {
        "preview_rows": [{"source_path": "/tmp/x.mkv"}],
        "media_items": [{
            "path": "/tmp/x.mkv",
            "detection_data": {
                "decision": {"confidence": 0.55, "review_required": True}
            },
        }],
    }
    row = PreviewPresentationService().enrich(result)["preview_rows"][0]
    assert row["review_required"] is True
    assert row["confidence"] == 0.55


def test_web_picker_parser_accepts_json_list(monkeypatch):
    fake = SimpleNamespace(returncode=0, stdout='["C:\\\\A.mkv","D:\\\\B.mkv"]')
    picker = WindowsWebPathPicker(runner=lambda *a, **k: fake)
    monkeypatch.setattr("services.web_picker_service.os.name", "nt")
    assert picker.pick_files() == [r"C:\A.mkv", r"D:\B.mkv"]


def test_web_picker_cancel_returns_empty(monkeypatch):
    fake = SimpleNamespace(returncode=0, stdout="[]")
    picker = WindowsWebPathPicker(runner=lambda *a, **k: fake)
    monkeypatch.setattr("services.web_picker_service.os.name", "nt")
    assert picker.pick_folder() == []


def test_web_ui_has_file_and_folder_buttons():
    root = Path(__file__).resolve().parents[1]
    html = (root / "index.html").read_text(encoding="utf-8")
    assert 'id="pickFiles"' in html
    assert 'id="pickFolder"' in html
    assert "Dateien auswählen" in html
    assert "Ordner auswählen" in html
    assert 'id="paths"' in html


def test_web_preview_has_parity_columns_and_long_name_tooltips():
    root = Path(__file__).resolve().parents[1]
    html = (root / "index.html").read_text(encoding="utf-8")
    css = (root / "assets" / "css" / "mediahub.css").read_text(encoding="utf-8")
    assert ">Relation<" in html
    assert ">Confidence<" in html
    assert ">Review<" in html
    assert 'class="filename-cell" title=' in html
    assert "min-width:320px" in css


def test_desktop_gui_has_relation_confidence_review_and_wider_center():
    plugin = (Path(__file__).resolve().parents[1] / "plugin.py").read_text(encoding="utf-8")
    assert '"Relation", "Confidence", "Review"' in plugin
    assert "outer.setStretchFactor(1,8)" in plugin
    assert "outer.setStretchFactor(2,3)" in plugin
    assert "outer.setSizes([160, 850, 360])" in plugin
    assert "cell.setToolTip" in plugin


def test_explicit_js_routes_registered():
    plugin = (Path(__file__).resolve().parents[1] / "plugin.py").read_text(encoding="utf-8")
    assert '"/smart-renamer/assets/interactive_preview.js"' in plugin
    assert '"/smart-renamer/assets/gui_wiring.js"' in plugin


def test_picker_routes_are_read_only_selection():
    plugin = (Path(__file__).resolve().parents[1] / "plugin.py").read_text(encoding="utf-8")
    assert '"/smart-renamer/api/picker/files"' in plugin
    assert '"/smart-renamer/api/picker/folder"' in plugin
    assert '"read_only_selection": True' in plugin
