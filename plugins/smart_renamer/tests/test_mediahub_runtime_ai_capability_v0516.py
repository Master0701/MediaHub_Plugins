from services.ai_review_bridge import AIReviewBridge
from services.optional_integrations import OptionalIntegrationManager


class HostAPI:
    def __init__(self, provider):
        self.provider = provider

    def resolve_capability(self, capability):
        return self.provider if capability == "ai.rename_review" else None


class Provider:
    def analyze_rename_review(self, payload):
        return {
            "provider": "MediaHub KI-Assistent",
            "candidate_id": "c1",
            "confidence": 0.88,
            "rationale": "Test",
            "structured_recommendation": {
                "candidate_id": "c1",
                "candidate_valid": True,
                "fields": {"title": "Batman"},
                "confidence": 0.88,
            },
        }


def test_bridge_resolves_mediahub_runtime_capability_and_preserves_structured_result():
    integrations = OptionalIntegrationManager(HostAPI(Provider()))
    bridge = AIReviewBridge(integrations)
    status = bridge.status()
    assert status["available"] is True
    result = bridge.analyze({"candidates": [{"candidate_id": "c1"}]})
    assert result["available"] is True
    assert result["provider"] == "MediaHub KI-Assistent"
    assert result["candidate_id"] == "c1"
    assert result["structured_recommendation"]["fields"]["title"] == "Batman"
    assert result["execution_allowed"] is False
