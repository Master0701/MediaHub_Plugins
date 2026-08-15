from services.batch_ai_review_bridge import BatchAIReviewBridge


class BatchProvider:
    name = "MediaHub KI-Assistent"

    def analyze_rename_batch_review(self, payload):
        return {
            "provider": self.name,
            "available": True,
            "items": [{"source_path": "a.mkv"}],
        }


class SingleOnlyProvider:
    name = "Single only"

    def analyze_rename_review(self, payload):
        return {"available": True}


class Registry:
    def __init__(self, values):
        self.values = dict(values)

    def resolve_capability(self, capability):
        return self.values.get(capability)


def test_direct_batch_capability_is_preferred():
    provider = BatchProvider()
    bridge = BatchAIReviewBridge(
        Registry({
            "ai.rename_batch_review": provider,
            "ai.rename_review": provider,
        })
    )
    status = bridge.status()
    assert status["available"] is True
    assert status["resolved_via"] == "ai.rename_batch_review"
    assert status["fallback_used"] is False


def test_single_capability_provider_is_valid_fallback_when_it_has_batch_method():
    provider = BatchProvider()
    bridge = BatchAIReviewBridge(
        Registry({"ai.rename_review": provider})
    )
    status = bridge.status()
    assert status["available"] is True
    assert status["provider"] == "MediaHub KI-Assistent"
    assert status["resolved_via"] == "ai.rename_review"
    assert status["fallback_used"] is True

    result = bridge.analyze({"items": [{"source_path": "a.mkv"}]})
    assert result["available"] is True
    assert len(result["items"]) == 1
    assert result["execution_allowed"] is False
    assert result["metadata_write_allowed"] is False


def test_fallback_does_not_enable_batch_for_single_only_provider():
    bridge = BatchAIReviewBridge(
        Registry({"ai.rename_review": SingleOnlyProvider()})
    )
    assert bridge.status()["available"] is False


def test_missing_provider_remains_unavailable():
    bridge = BatchAIReviewBridge(Registry({}))
    assert bridge.status()["available"] is False
