from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_browser_uses_direct_profiles_before_api_fallback():
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    assert "Array.isArray(window.__SMART_RENAMER_PROFILES__)" in html
    assert "if(!profiles.length)" in html
    assert "cache:'no-store'" in html
