from pathlib import Path

from plugin import MediaHubSmartRenamerPlugin


def test_main_plugin_exposes_gui_review_facade():
    plugin = MediaHubSmartRenamerPlugin(
        plugin_path=Path(__file__).resolve().parents[1]
    )

    for name in (
        "ai_review_status",
        "analyze_review_with_ai",
        "fuse_review_decision",
        "build_decision_evidence",
        "analyze_and_fuse_review",
        "classify_preview_review",
        "set_preview_decision",
    ):
        assert callable(getattr(plugin, name, None)), name


def test_ai_review_status_is_safe_without_provider():
    plugin = MediaHubSmartRenamerPlugin(
        plugin_path=Path(__file__).resolve().parents[1]
    )
    status = plugin.ai_review_status()
    assert status["capability"] == "ai.rename_review"
    assert status["available"] is False
    assert status["execution_allowed"] is False
    assert status["human_confirmation_required"] is True


def test_decision_fusion_facade_remains_locked():
    plugin = MediaHubSmartRenamerPlugin(
        plugin_path=Path(__file__).resolve().parents[1]
    )
    result = plugin.fuse_review_decision(
        {
            "relation_type": "single",
            "confidence": 0.95,
            "review_required": False,
        }
    )
    assert result["execution_allowed"] is False
    assert result["human_confirmation_required"] is True
