from pathlib import Path


def test_plugin_integrates_pipeline_debug_monitor_v521():
    root = Path(__file__).resolve().parents[1]
    text = (root / "plugin.py").read_text(encoding="utf-8")

    assert (
        "from services.pipeline_debug_monitor import PipelineDebugMonitor"
        in text
    )
    assert "self.pipeline_debug_monitor = PipelineDebugMonitor()" in text
    assert "self.last_pipeline_debug_snapshot = None" in text
    assert "pipeline_debug = self.pipeline_debug_monitor.build(" in text
    assert "self.last_pipeline_debug_snapshot = pipeline_debug" in text
    assert '"pipeline_debug": pipeline_debug' in text
    assert 'context.document["pipeline_debug"] = pipeline_debug' in text
    assert "def get_pipeline_debug_snapshot(self):" in text
    assert "def get_pipeline_debug_text(self):" in text
