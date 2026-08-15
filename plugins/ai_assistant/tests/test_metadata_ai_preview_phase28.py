from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def test_ai_metadata_capability_is_published():
    text=(ROOT/'plugin.py').read_text(encoding='utf-8')
    assert '"ai.metadata_review"' in text
    assert 'def analyze_metadata_review(' in text
    assert 'MetadataAIReviewProvider' in text

def test_capability_manager_knows_metadata_review():
    text=(ROOT/'services'/'capability_manager.py').read_text(encoding='utf-8')
    assert '"ai.metadata_review": ()' in text

def test_metadata_provider_is_read_only():
    text=(ROOT/'services'/'metadata_review_provider.py').read_text(encoding='utf-8')
    assert '"metadata_write_allowed": False' in text
    assert '"automatic_apply_allowed": False' in text
