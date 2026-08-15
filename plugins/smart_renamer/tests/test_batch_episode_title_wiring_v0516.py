from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def test_local_review_is_added_as_batch_fallback():
    text=(ROOT/"plugin.py").read_text(encoding="utf-8")
    assert 'item["local_review"] = self.analyze_review_with_ai(item)' in text
