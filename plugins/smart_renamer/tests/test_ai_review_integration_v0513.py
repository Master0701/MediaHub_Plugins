from pathlib import Path
import json

from services.ai_review_bridge import AIReviewBridge
from services.optional_integrations import OptionalIntegrationManager


class Provider:
    name = "Mock KI"
    def analyze_rename_review(self, payload):
        return {
            "recommendation": "review_name",
            "suggested_name": "Serie - S01E01.mkv",
            "confidence": 0.91,
            "rationale": "Staffel und Episode sind eindeutig.",
            "warnings": ["Nur Vorschlag"],
        }


def test_provider_attached_through_existing_integration_manager():
    manager = OptionalIntegrationManager()
    bridge = AIReviewBridge(manager)
    assert bridge.status()["available"] is False
    manager.attach_provider("ai.rename_review", Provider())
    status = bridge.status()
    assert status["available"] is True
    assert status["provider"] == "Mock KI"


def test_backwards_compatible_dict_provider():
    bridge = AIReviewBridge({
        "ai.rename_review": lambda payload: {
            "provider": "mock",
            "recommendation": "multi_episode",
            "confidence": 0.88,
        }
    })
    result = bridge.analyze({})
    assert result["available"] is True
    assert result["provider"] == "mock"
    assert result["requires_human_confirmation"] is True


def test_ai_review_never_grants_execution():
    manager = OptionalIntegrationManager()
    manager.attach_provider("ai.rename_review", Provider())
    result = AIReviewBridge(manager).analyze({"current_name": "x.mkv"})
    assert result["confidence"] == 0.91
    assert result["execution_allowed"] is False
    assert result["requires_human_confirmation"] is True
    assert result["human_confirmation_required"] is True


def test_missing_provider_safe_fallback():
    result = AIReviewBridge(OptionalIntegrationManager()).analyze({})
    assert result["available"] is False
    assert result["execution_allowed"] is False
    assert result["requires_human_confirmation"] is True


def test_web_ai_routes_present():
    plugin = (Path(__file__).resolve().parents[1] / "plugin.py").read_text(encoding="utf-8")
    assert '"/smart-renamer/api/ai-review/status"' in plugin
    assert '"/smart-renamer/api/ai-review/analyze"' in plugin


def test_web_ui_ai_controls_present():
    root = Path(__file__).resolve().parents[1]
    html = (root / "index.html").read_text(encoding="utf-8")
    js = (root / "assets" / "js" / "interactive_preview.js").read_text(encoding="utf-8")
    assert "KI-Review" in html
    assert "ai.rename_review" in html
    assert 'id="mh-ai-review-run"' in html
    assert "runAIReview" in js
    assert "Benutzerbestätigung erforderlich" in js


def test_desktop_ai_controls_present():
    plugin = (Path(__file__).resolve().parents[1] / "plugin.py").read_text(encoding="utf-8")
    assert 'QPushButton("KI prüfen")' in plugin
    assert "self.ai_review_status_label" in plugin
    assert "_run_ai_review_for_selection" in plugin
    assert "Keine Datei wurde verändert." in plugin


def test_version_0513():
    root = Path(__file__).resolve().parents[1]
    data = json.loads((root / "plugin.json").read_text(encoding="utf-8"))
    assert data["version"] == "0.5.13"
