from pathlib import Path
import importlib.util

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "services" / "provider_credential_store.py"

spec = importlib.util.spec_from_file_location("provider_credential_store", MODULE)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
Store = mod.ProviderCredentialStore


def test_credentials_are_stored_outside_plugin_directory(tmp_path):
    base = tmp_path / "MediaHub"
    plugin = base / "plugins" / "mediahub.ai_assistant"
    plugin.mkdir(parents=True)

    store = Store(plugin)

    assert store.path == (
        base / "plugin_data" / "ai_assistant" / "provider_credentials.dat"
    )
    assert store.legacy_path == (
        plugin / "config" / "provider_credentials.dat"
    )


def test_legacy_file_is_migrated_once(tmp_path):
    base = tmp_path / "MediaHub"
    plugin = base / "plugins" / "mediahub.ai_assistant"
    legacy = plugin / "config" / "provider_credentials.dat"
    legacy.parent.mkdir(parents=True)
    legacy.write_bytes(b"legacy-encrypted-data")

    store = Store(plugin)

    assert store.path.exists()
    assert store.path.read_bytes() == b"legacy-encrypted-data"


def test_existing_persistent_file_wins_over_legacy(tmp_path):
    base = tmp_path / "MediaHub"
    plugin = base / "plugins" / "mediahub.ai_assistant"
    legacy = plugin / "config" / "provider_credentials.dat"
    legacy.parent.mkdir(parents=True)
    legacy.write_bytes(b"old")

    persistent = base / "plugin_data" / "ai_assistant" / "provider_credentials.dat"
    persistent.parent.mkdir(parents=True)
    persistent.write_bytes(b"new")

    store = Store(plugin)

    assert store.path.read_bytes() == b"new"


def test_source_manager_still_uses_plugin_path_constructor():
    text = (
        ROOT / "services" / "source_manager.py"
    ).read_text(encoding="utf-8")

    assert "ProviderCredentialStore(" in text
    assert "self.plugin_path," in text
    assert "data_base_dir=base_dir," in text
