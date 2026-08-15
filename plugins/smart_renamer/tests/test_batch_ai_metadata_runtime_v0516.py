from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def test_phase2_gui_and_runtime_wiring_present():
    text=(ROOT/"plugin.py").read_text(encoding="utf-8")
    assert "BatchAIReviewBridge" in text
    assert "MetadataCapabilityBridge" in text
    assert "Als Referenz" in text
    assert "KI auf Auswahl" in text
    assert "def analyze_batch_with_ai" in text
    assert 'result["metadata_write_allowed"]=False' in text

def test_phase2_bridges_use_capabilities():
    batch=(ROOT/"services/batch_ai_review_bridge.py").read_text(encoding="utf-8")
    meta=(ROOT/"services/metadata_capability_bridge.py").read_text(encoding="utf-8")
    assert 'CAPABILITY="ai.rename_batch_review"' in batch
    assert 'metadata.read' in meta
    assert 'metadata.review' in meta
    assert 'metadata.write' in meta
