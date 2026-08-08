from __future__ import annotations

from pathlib import Path

from plugin import MediaHubSmartRenamerPlugin
from services.optional_integrations import OptionalIntegrationManager


class FakeMetadataProvider:
    name = "Fake Metadata Editor"

    def get_metadata_for_path(self, path: str):
        return {
            "titel": "Metadata-Titel",
            "jahr": "2025",
            "source_marker": path,
        }


class FakeHostAPI:
    def __init__(self, provider=None):
        self.provider = provider

    def resolve_capability(self, capability: str):
        if capability == "metadata_preview":
            return self.provider
        return None


def test_smart_renamer_runs_without_metadata_editor():
    manager = OptionalIntegrationManager(None)

    items, status = manager.enrich_items([
        {"path": "C:/Film.mkv", "metadata": {"titel": "Lokal"}}
    ])

    assert status.active is False
    assert status.available is False
    assert items[0]["metadata"]["titel"] == "Lokal"


def test_metadata_provider_is_only_active_when_present():
    manager = OptionalIntegrationManager()
    manager.attach_provider("metadata_preview", FakeMetadataProvider())

    status = manager.metadata_status()

    assert status.active is True
    assert status.available is True
    assert status.capability == "metadata_preview"


def test_existing_metadata_overrides_optional_provider():
    manager = OptionalIntegrationManager()
    manager.attach_provider("metadata_preview", FakeMetadataProvider())

    items, status = manager.enrich_items([
        {
            "path": "C:/Film.mkv",
            "metadata": {
                "titel": "Manueller Titel",
            },
        }
    ])

    assert status.active is True
    assert items[0]["metadata"]["titel"] == "Manueller Titel"
    assert items[0]["metadata"]["jahr"] == "2025"


def test_host_capability_resolution_is_optional():
    provider = FakeMetadataProvider()
    manager = OptionalIntegrationManager(FakeHostAPI(provider))

    status = manager.metadata_status()

    assert status.active is True
    assert status.provider_name == "Fake Metadata Editor"


def test_missing_host_capability_falls_back_cleanly():
    manager = OptionalIntegrationManager(FakeHostAPI(None))

    status = manager.metadata_status()

    assert status.active is False
    assert "interne Vorschau" in status.reason


def test_plugin_preview_reports_integration_status(tmp_path: Path):
    source = tmp_path / "Film 2024.mkv"
    source.write_text("x", encoding="utf-8")

    plugin = MediaHubSmartRenamerPlugin(
        plugin_path=Path(__file__).resolve().parents[1],
    )
    plugin.attach_optional_provider(
        "metadata_preview",
        FakeMetadataProvider(),
    )

    result = plugin.preview_rename(
        [{"path": str(source)}],
        [{"type": "schema", "template": "[titel] ([jahr])"}],
    )

    integration = result["optional_integrations"]["metadata_editor"]
    assert integration["active"] is True
    assert integration["available"] is True


def test_provider_failure_does_not_break_smart_renamer():
    class BrokenProvider:
        def get_metadata_for_path(self, path: str):
            raise RuntimeError("kaputt")

    manager = OptionalIntegrationManager()
    manager.attach_provider("metadata_preview", BrokenProvider())

    items, status = manager.enrich_items([{"path": "C:/Film.mkv"}])

    assert status.active is True
    assert items == [{"path": "C:/Film.mkv"}]
