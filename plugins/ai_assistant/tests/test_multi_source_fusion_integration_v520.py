from pathlib import Path


def test_plugin_integrates_multi_source_fusion_v520():
    root = Path(__file__).resolve().parents[1]
    text = (root / "plugin.py").read_text(encoding="utf-8")

    assert "from services.multi_source_fusion import MultiSourceFusion" in text
    assert "self.multi_source_fusion = MultiSourceFusion()" in text
    assert "multi_source_fusion = self.multi_source_fusion.fuse" in text
    assert '"multi_source_fusion": multi_source_fusion' in text
    assert 'context.document["multi_source_fusion"] = multi_source_fusion' in text
