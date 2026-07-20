from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGINS = ROOT / "plugins"
OUTPUT = ROOT / "catalog" / "plugin_catalog.generated.json"

def main() -> None:
    items = []
    for manifest_path in sorted(PLUGINS.glob("*/plugin.json")):
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        catalog = data.get("catalog") or {}
        if not catalog.get("visible", True):
            continue
        version = str(data.get("version") or "0.0.0")
        slug = manifest_path.parent.name
        items.append({
            "id": data.get("id"),
            "name": data.get("name"),
            "version": version,
            "status": data.get("development_status", "available"),
            "visible": True,
            "auto_install": bool(catalog.get("auto_install", True)),
            "description": data.get("description", ""),
            "release_asset": f"MediaHub_{slug}_v{version}.mhplugin",
            "sha256_asset": f"MediaHub_{slug}_v{version}.mhplugin.sha256",
        })
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps({"schema_version": 1, "plugins": items}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Erstellt: {OUTPUT}")

if __name__ == "__main__":
    main()
