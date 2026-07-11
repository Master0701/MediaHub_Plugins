from __future__ import annotations

import argparse
import json
import shutil
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PLUGINS_DIR = ROOT / "plugins"
SHARED_DIR = ROOT / "shared"
DIST_DIR = ROOT / "dist"

PLUGIN_MAP = {
    "web_remote": PLUGINS_DIR / "web_remote",
}


def build_plugin(key: str) -> Path:
    source = PLUGIN_MAP[key]
    manifest = json.loads((source / "plugin.json").read_text(encoding="utf-8"))
    version = manifest["version"]
    name = manifest["name"].replace("MediaHub ", "").replace(" ", "")
    output = DIST_DIR / f"MediaHub_{name}_v{version}.mhplugin"
    DIST_DIR.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        package_root = Path(tmp) / manifest["id"]
        shutil.copytree(source, package_root)
        shared_target = package_root / "shared"
        shutil.copytree(SHARED_DIR / "mediahub_web_core", shared_target / "mediahub_web_core")

        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
            for file in package_root.rglob("*"):
                if file.is_file():
                    archive.write(file, file.relative_to(Path(tmp)))

    print(f"Erstellt: {output}")
    return output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("plugin", choices=[*PLUGIN_MAP, "all"])
    args = parser.parse_args()

    keys = PLUGIN_MAP if args.plugin == "all" else [args.plugin]
    for key in keys:
        build_plugin(key)


if __name__ == "__main__":
    main()
