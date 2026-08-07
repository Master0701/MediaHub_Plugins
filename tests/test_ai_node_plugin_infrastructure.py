from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AI_ROOT = ROOT / "ai_node_plugins"
AI_CATALOG = ROOT / "catalog" / "ai_plugin_catalog.json"


def test_ai_node_source_area_exists():
    assert AI_ROOT.is_dir()
    assert any(AI_ROOT.glob("*/plugin.json"))


def test_ai_catalog_is_utf8_without_bom_and_schema_1():
    raw = AI_CATALOG.read_bytes()
    assert not raw.startswith(b"\xef\xbb\xbf")

    data = json.loads(raw.decode("utf-8"))
    assert data["schema_version"] == 1
    assert data["package_extension"] == ".mhaiplugin"
    assert isinstance(data["plugins"], list)


def test_ai_catalog_matches_ai_node_manifests():
    data = json.loads(AI_CATALOG.read_text(encoding="utf-8"))
    by_id = {item["id"]: item for item in data["plugins"]}

    for manifest_path in AI_ROOT.glob("*/plugin.json"):
        manifest = json.loads(
            manifest_path.read_text(encoding="utf-8")
        )
        item = by_id[manifest["id"]]

        assert item["version"] == manifest["version"]
        assert item["package_asset"].endswith(".mhaiplugin")
        assert (
            item["sha256_asset"]
            == item["package_asset"] + ".sha256"
        )
