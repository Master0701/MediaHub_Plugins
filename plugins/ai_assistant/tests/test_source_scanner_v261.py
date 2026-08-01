import sys
from pathlib import Path

PLUGIN_DIR = Path(__file__).resolve().parents[1]
if str(PLUGIN_DIR) not in sys.path:
    sys.path.insert(0, str(PLUGIN_DIR))

from services.source_scanner import ControlledSourceScanner


def test_html_extraction_is_structured(tmp_path):
    scanner = ControlledSourceScanner(tmp_path / "cache")
    html = """
    <html>
      <head><title>Testserie</title></head>
      <body>
        <h1>Testserie Chronologie</h1>
        <p>Staffel 1, Folge 2, erschienen 2024.</p>
        <p>Spin-off und Prequel.</p>
      </body>
    </html>
    """
    scan = {
        "url": "https://example.com",
        "title": scanner._extract_title(html),
        "headings": scanner._extract_headings(html),
        "text_preview": scanner._strip_html(html),
    }

    preview = scanner.extract_structured_preview(scan)

    assert preview["source_title"] == "Testserie"
    assert preview["years"] == [2024]
    assert preview["season_mentions"] == ["1"]
    assert preview["episode_mentions"] == ["2"]
    assert "prequel" in preview["relation_terms"]
    assert preview["automatic_import"] is False


def test_invalid_url_is_rejected(tmp_path):
    scanner = ControlledSourceScanner(tmp_path / "cache")

    try:
        scanner.check_policy("not-a-url")
    except ValueError:
        pass
    else:
        raise AssertionError("Ungültige URL wurde akzeptiert.")


def test_cache_roundtrip(tmp_path):
    scanner = ControlledSourceScanner(tmp_path / "cache")
    payload = {
        "url": "https://example.com",
        "title": "Test",
    }
    scanner._save_cache(payload["url"], payload)

    loaded = scanner.load_cached(payload["url"])

    assert loaded["title"] == "Test"
