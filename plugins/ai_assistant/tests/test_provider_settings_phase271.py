from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_connection_test_applies_current_form_first():
    text = (ROOT / "plugin.py").read_text(encoding="utf-8")
    start = text.index("    def test_provider(self, provider_id):")
    end = text.index("    def refresh_status(self):", start)
    block = text[start:end]
    assert "self._apply_provider_form(provider_id)" in block
    assert block.index("self._apply_provider_form(provider_id)") < block.index(
        "self._source_manager().test_provider(provider_id)"
    )

def test_apply_form_persists_enabled_and_credentials():
    text = (ROOT / "plugin.py").read_text(encoding="utf-8")
    start = text.index("    def _apply_provider_form(self, provider_id):")
    end = text.index("    def test_provider(self, provider_id):", start)
    block = text[start:end]
    assert "enabled=self.tvdb_enabled.isChecked()" in block
    assert '"api_key": self.tvdb_api_key.text().strip()' in block
    assert "manager.update_provider_settings(" in block
