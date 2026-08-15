import json
from pathlib import Path


def test_update_provider_settings_persists_enabled_and_reloads():
    text = (Path(__file__).resolve().parents[1] / "services" / "source_manager.py").read_text(encoding="utf-8")
    assert 'target["enabled"] = bool(enabled)' in text
    assert 'json.dump(data, handle, ensure_ascii=False, indent=2)' in text
    assert "self.reload()" in text
    assert '"persisted_enabled"' in text


def test_credentials_stay_outside_sources_json():
    text = (Path(__file__).resolve().parents[1] / "services" / "source_manager.py").read_text(encoding="utf-8")
    start = text.index("    def update_provider_settings(")
    end = text.find("\n    def ", start + 10)
    block = text[start:end if end != -1 else None]
    assert "self.credential_store.set(provider_id" in block
    assert 'target["api_key"]' not in block
    assert 'target["subscriber_pin"]' not in block
