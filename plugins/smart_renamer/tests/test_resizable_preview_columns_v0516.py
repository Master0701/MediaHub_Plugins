from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def test_desktop_columns():
    t=(ROOT/"plugin.py").read_text(encoding="utf-8")
    assert "QHeaderView.ResizeMode.Interactive" in t
    assert "setStretchLastSection(False)" in t
    assert "1:300" in t and "2:340" in t
def test_web_columns():
    h=(ROOT/"index.html").read_text(encoding="utf-8")
    c=(ROOT/"assets/css/mediahub.css").read_text(encoding="utf-8")
    assert h.count("preview-resizable") >= 2
    assert "enableResizableColumns" in h
    assert "mh-col-resizer" in h
    assert "cursor:col-resize" in c
