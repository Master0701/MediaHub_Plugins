from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PLUGINS_DIR = ROOT / "plugins"
SHARED_DIR = ROOT / "shared"
RELEASE_DIR = ROOT / "release"

def discover_plugins() -> dict[str, Path]:
    plugins: dict[str, Path] = {}
    if not PLUGINS_DIR.exists():
        return plugins
    for manifest_path in sorted(PLUGINS_DIR.glob("*/plugin.json")):
        plugins[manifest_path.parent.name] = manifest_path.parent
    return plugins

def clean_release_directory() -> None:
    if RELEASE_DIR.exists():
        shutil.rmtree(RELEASE_DIR)
    RELEASE_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Release-Ordner bereinigt: {RELEASE_DIR}")

def read_manifest(source: Path) -> dict:
    return json.loads((source / "plugin.json").read_text(encoding="utf-8"))

def safe_package_name(manifest: dict, fallback: str) -> str:
    name = str(manifest.get("name", fallback)).replace("MediaHub ", "").replace(" ", "")
    return "".join(c for c in name if c.isalnum() or c in "-_")

def create_sha256(file_path: Path) -> Path:
    digest = hashlib.sha256(file_path.read_bytes()).hexdigest()
    checksum_path = file_path.with_suffix(file_path.suffix + ".sha256")
    checksum_path.write_text(f"{digest} {file_path.name}\n", encoding="utf-8")
    print(f"Prüfsumme erstellt: {checksum_path}")
    return checksum_path

def copy_shared_runtime(package_root: Path, manifest: dict) -> None:
    shared_runtime = manifest.get("shared_runtime")
    if not shared_runtime:
        return
    source = SHARED_DIR / str(shared_runtime)
    if not source.exists():
        raise FileNotFoundError(f"Gemeinsame Laufzeit fehlt: {source}")
    target = package_root / "shared" / str(shared_runtime)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, target)

def build_plugin(key: str, source: Path) -> Path:
    manifest = read_manifest(source)
    for required in ("id", "name", "version", "entry", "minimum_mediahub", "permissions"):
        if required not in manifest:
            raise ValueError(f"Fehlendes Pflichtfeld '{required}' in {source / 'plugin.json'}")
    version = str(manifest["version"])
    plugin_id = str(manifest["id"])
    package_name = safe_package_name(manifest, key)
    RELEASE_DIR.mkdir(parents=True, exist_ok=True)
    output = RELEASE_DIR / f"MediaHub_{package_name}_v{version}.mhplugin"
    with tempfile.TemporaryDirectory() as tmp:
        temp_root = Path(tmp)
        package_root = temp_root / plugin_id
        shutil.copytree(source, package_root, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo", ".pytest_cache"))
        copy_shared_runtime(package_root, manifest)
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for file in sorted(package_root.rglob("*")):
                if file.is_file():
                    archive.write(file, file.relative_to(temp_root))
    create_sha256(output)
    print(f"Plugin erstellt: {output}")
    return output

def main() -> int:
    plugins = discover_plugins()
    if not plugins:
        print(f"FEHLER: Keine Plugins unter {PLUGINS_DIR} gefunden.")
        return 1
    parser = argparse.ArgumentParser(description="Erstellt installierbare MediaHub-Plugin-Pakete.")
    parser.add_argument("plugin", nargs="?", default="all", choices=[*plugins, "all"], help="Plugin-Ordnername oder 'all'. Standard: all")
    parser.add_argument("--clean", action="store_true", help="Leert vor dem Build den release-Ordner.")
    args = parser.parse_args()
    if args.clean:
        clean_release_directory()
    else:
        RELEASE_DIR.mkdir(parents=True, exist_ok=True)
    selected = plugins if args.plugin == "all" else {args.plugin: plugins[args.plugin]}
    for key, source in selected.items():
        build_plugin(key, source)
    print(f"Build abgeschlossen: {len(selected)} Plugin(s)")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
