from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def test_metadata_ai_returns_poster_candidate():
    text=(ROOT/"services"/"metadata_review_provider.py").read_text(encoding="utf-8")
    assert "def _poster_candidate(" in text
    assert '"poster_url": poster_url' in text

def test_tvdb_search_preserves_image_candidate():
    text=(ROOT/"services"/"providers"/"tvdb_provider.py").read_text(encoding="utf-8")
    assert '"image_url": (' in text
    assert 'item.get("image_url")' in text
