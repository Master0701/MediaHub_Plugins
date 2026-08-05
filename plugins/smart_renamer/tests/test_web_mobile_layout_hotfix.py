from pathlib import Path

from plugin import MediaHubSmartRenamerPlugin


ROOT = Path(__file__).resolve().parents[1]


def test_original_layout_and_css_route_are_preserved():
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    assert 'href="/smart-renamer/assets/mediahub.css"' in html
    assert "function routeBase" not in html
    assert "apiFetch(" not in html
    assert "Array.isArray(window.__SMART_RENAMER_PROFILES__)" in html
    assert "fetch('/smart-renamer/api/preview'" in html


def test_server_embeds_profiles_without_fetch_override():
    plugin = MediaHubSmartRenamerPlugin(plugin_path=ROOT)
    status, content_type, body = plugin._index()
    html = body.decode("utf-8")

    assert status == 200
    assert content_type.startswith("text/html")
    assert "window.__SMART_RENAMER_PROFILES__=" in html
    assert '"name": "Plex"' in html
    assert '"name": "Hörbuch"' in html
    assert "originalFetch" not in html
    assert "window.fetch = function" not in html
    assert 'href="/smart-renamer/assets/mediahub.css"' in html


def test_stylesheet_route_reads_existing_css():
    plugin = MediaHubSmartRenamerPlugin(plugin_path=ROOT)
    status, content_type, body = plugin._stylesheet()
    assert status == 200
    assert content_type.startswith("text/css")
    assert b".app-shell" in body
