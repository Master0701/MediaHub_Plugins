from services.batch_ai_review_bridge import BatchAIReviewBridge


class BatchProvider:
    name = "MediaHub KI-Assistent"

    def analyze_rename_batch_review(self, payload):
        return {
            "available": True,
            "provider": self.name,
            "items": list(payload.get("items") or []),
        }


class ResolveTupleRegistry:
    def __init__(self, provider):
        self.provider = provider

    def resolve(self, capability):
        if capability == "ai.rename_batch_review":
            return ("mediahub.ai_assistant", self.provider)
        return (None, None)


class ResolveProviderRegistry:
    def __init__(self, provider):
        self.provider = provider

    def resolve(self, capability):
        if capability == "ai.rename_batch_review":
            return self.provider
        return None


def test_batch_bridge_supports_resolve_tuple_like_single_ai_bridge():
    provider = BatchProvider()
    bridge = BatchAIReviewBridge(ResolveTupleRegistry(provider))
    status = bridge.status()

    assert status["available"] is True
    assert status["provider"] == "MediaHub KI-Assistent"
    assert status["resolved_via"] == "ai.rename_batch_review"


def test_batch_bridge_supports_resolve_returning_provider_directly():
    provider = BatchProvider()
    bridge = BatchAIReviewBridge(ResolveProviderRegistry(provider))
    assert bridge.status()["available"] is True


def test_batch_analysis_works_via_resolve_tuple():
    provider = BatchProvider()
    bridge = BatchAIReviewBridge(ResolveTupleRegistry(provider))
    result = bridge.analyze({"items": [{"source_path": "a.mkv"}]})

    assert result["available"] is True
    assert result["provider"] == "MediaHub KI-Assistent"
    assert len(result["items"]) == 1
    assert result["execution_allowed"] is False
    assert result["metadata_write_allowed"] is False
