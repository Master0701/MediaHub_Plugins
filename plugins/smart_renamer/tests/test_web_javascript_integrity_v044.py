from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_web_path_split_regex_is_not_broken():
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    assert r"split(/\r?\n/)" in html


def test_web_initialization_and_routes_are_present():
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    assert "Array.isArray(window.__SMART_RENAMER_PROFILES__)" in html
    assert "/smart-renamer/api/profiles" in html
    assert "/smart-renamer/api/backends" in html
    assert "active_preview_backend_id" in html
