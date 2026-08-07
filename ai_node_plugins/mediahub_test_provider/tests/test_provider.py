from plugin import MediaHubAITestProvider


def test_health_and_test_provider():
    provider = MediaHubAITestProvider()

    health = provider.health()
    assert health["status"] == "online"
    assert health["plugin_id"] == "provider.mediahub_test"

    result = provider.test("MediaHub")
    assert result == {
        "ok": True,
        "provider": "provider.mediahub_test",
        "value": "MediaHub",
    }
