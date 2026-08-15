from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def test_combined_online_details_helper_exists():
    text=(ROOT/"services"/"metadata_review_provider.py").read_text(encoding="utf-8")
    assert "def _online_metadata_details(" in text
    assert '"description": description' in text
    assert '"published_at": published_at' in text

def test_description_is_mapped_into_metadata_fields():
    text=(ROOT/"services"/"metadata_review_provider.py").read_text(encoding="utf-8")
    assert 'fields["description"] = online_details["description"]' in text

def test_release_date_is_mapped_into_metadata_fields():
    text=(ROOT/"services"/"metadata_review_provider.py").read_text(encoding="utf-8")
    assert 'fields["published_at"] = online_details["published_at"]' in text

def test_tvdb_preserves_description_and_release_evidence():
    text=(ROOT/"services"/"providers"/"tvdb_provider.py").read_text(encoding="utf-8")
    assert '"overview": str(' in text
    assert 'found.get("description")' in text
    assert 'found.get("summary")' in text
    assert 'found.get("firstAired")' in text
