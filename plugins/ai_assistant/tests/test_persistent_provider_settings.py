from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "services" / "source_manager.py"
TEXT = SOURCE.read_text(encoding="utf-8")


def test_source_manager_uses_persistent_sources_path():
    assert "self.default_config_path = self.plugin_path / \"config\" / \"sources.json\"" in TEXT
    assert '/ "plugin_data"' in TEXT
    assert '/ "ai_assistant"' in TEXT
    assert '/ "sources.json"' in TEXT
    assert "self._ensure_persistent_config()" in TEXT


def test_update_provider_settings_writes_persistent_config_path():
    assert 'with self.config_path.open("w", encoding="utf-8") as handle:' in TEXT
    assert 'target["enabled"] = bool(enabled)' in TEXT


def test_merge_preserves_user_values_and_new_defaults_without_importing_module():
    tree = ast.parse(TEXT)
    cls = next(
        node for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "SourceManager"
    )
    fn = next(
        node for node in cls.body
        if isinstance(node, ast.FunctionDef)
        and node.name == "_merge_source_configs"
    )
    module = ast.Module(body=[fn], type_ignores=[])
    ast.fix_missing_locations(module)

    namespace = {}
    exec(compile(module, str(SOURCE), "exec"), namespace)
    merge = namespace["_merge_source_configs"]

    defaults = {
        "schema_version": 4,
        "sources": [
            {
                "id": "tvdb",
                "enabled": False,
                "language": "de-DE",
                "priority": 90,
                "new_default_field": "x",
            },
            {
                "id": "new_provider",
                "enabled": True,
            },
        ],
    }
    persistent = {
        "schema_version": 3,
        "sources": [
            {
                "id": "tvdb",
                "enabled": True,
                "language": "de",
            },
            {
                "id": "my_custom",
                "type": "generic_web",
                "enabled": True,
            },
        ],
    }

    result = merge(defaults, persistent)
    by_id = {item["id"]: item for item in result["sources"]}

    assert by_id["tvdb"]["enabled"] is True
    assert by_id["tvdb"]["language"] == "de"
    assert by_id["tvdb"]["priority"] == 90
    assert by_id["tvdb"]["new_default_field"] == "x"
    assert "new_provider" in by_id
    assert "my_custom" in by_id
    assert result["schema_version"] == 4


def test_credentials_remain_separate():
    assert "self.credential_store = ProviderCredentialStore(self.plugin_path)" in TEXT
    assert "self.credential_store.set(provider_id, dict(credentials))" in TEXT
