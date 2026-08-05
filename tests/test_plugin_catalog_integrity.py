from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "catalog" / "plugin_catalog.json"
BUILD_SCRIPT = ROOT / "build_plugins.py"


def _load_build_module():
    spec = importlib.util.spec_from_file_location(
        "mediahub_build_plugins_test",
        BUILD_SCRIPT,
    )
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_plugin_catalog_is_utf8_without_bom():
    raw = CATALOG.read_bytes()
    assert not raw.startswith(b"\xef\xbb\xbf")
    raw.decode("utf-8")


def test_plugin_catalog_schema_and_versions_match_manifests():
    data = json.loads(CATALOG.read_text(encoding="utf-8"))
    assert data["schema_version"] == 2
    assert data["repository"] == "Master0701/MediaHub_Plugins"

    by_id = {item["id"]: item for item in data["plugins"]}
    build = _load_build_module()

    for key, source in build.discover_plugins().items():
        manifest = build.read_manifest(source)
        catalog_settings = manifest.get("catalog") or {}

        if catalog_settings.get("visible", True) is False:
            continue

        item = by_id[manifest["id"]]
        version = str(manifest["version"])
        expected_asset = (
            f"MediaHub_{build.safe_package_name(manifest, key)}_"
            f"v{version}.mhplugin"
        )

        assert item["version"] == version
        assert item["release_asset"] == expected_asset
        assert item["sha256_asset"] == expected_asset + ".sha256"

        if version == "0.0.0":
            expected_status = "planned"
            expected_auto_install = False
        else:
            expected_status = "available"
            expected_auto_install = bool(
                catalog_settings.get("auto_install", True)
            )

        assert item["status"] == expected_status
        assert item["auto_install"] is expected_auto_install
