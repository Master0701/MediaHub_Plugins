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


CATEGORY_BY_ID = {
    "mediahub.web_remote": "Fernsteuerung",
    "mediahub.mobile_dashboard": "Mobil",
    "mediahub.metadata_editor": "Metadaten",
    "mediahub.ai_assistant": "KI und Analyse",
    "mediahub.smart_renamer": "Dateien und Umbenennung",
    "mediahub.audiobook_manager": "Hörbücher",
    "mediahub.list_exporter": "Listen und Export",
}

CATALOG_PATH = ROOT / "catalog" / "plugin_catalog.json"
CATALOG_SCHEMA_VERSION = 2
CATALOG_REPOSITORY = "Master0701/MediaHub_Plugins"


def _catalog_status(manifest: dict, version: str) -> str:
    return "planned" if version == "0.0.0" else "available"


def _catalog_project_page(plugin_key: str, catalog: dict) -> str:
    configured = str(catalog.get("project_page") or "").strip()
    if configured:
        return configured
    return (
        "https://github.com/Master0701/MediaHub_Plugins/"
        f"tree/main/plugins/{plugin_key}"
    )


def update_catalog(plugins: dict[str, Path]) -> Path:
    """Erzeugt den einzigen verbindlichen MediaHub-Plugin-Store-Katalog."""
    items: list[dict] = []

    for key, source in sorted(plugins.items()):
        manifest = read_manifest(source)
        catalog = manifest.get("catalog") or {}

        if not bool(catalog.get("visible", True)):
            continue

        plugin_id = str(manifest["id"])
        version = str(manifest["version"])
        minimum = str(
            manifest.get("minimum_mediahub_version")
            or manifest.get("minimum_mediahub")
            or ""
        )
        status = _catalog_status(manifest, version)
        publishable = version != "0.0.0"
        package_name = safe_package_name(manifest, key)
        release_asset = f"MediaHub_{package_name}_v{version}.mhplugin"

        auto_install = bool(catalog.get("auto_install", publishable))
        manual_only = bool(catalog.get("manual_only", False))
        manual_message = str(catalog.get("manual_install_message") or "").strip()

        if not publishable:
            auto_install = False
            if not manual_message:
                manual_message = (
                    "Für diese Version ist derzeit noch kein installierbares "
                    "Release-Paket verfügbar."
                )

        items.append(
            {
                "id": plugin_id,
                "name": str(manifest["name"]),
                "version": version,
                "status": status,
                "category": str(
                    catalog.get("category")
                    or CATEGORY_BY_ID.get(plugin_id, "Erweiterung")
                ),
                "visible": True,
                "auto_install": auto_install,
                "manual_only": manual_only,
                "description": str(manifest.get("description", "")),
                "minimum_mediahub_version": minimum,
                "project_page": _catalog_project_page(key, catalog),
                "manual_install_message": manual_message,
                "release_asset": release_asset,
                "sha256_asset": release_asset + ".sha256",
            }
        )

    payload = {
        "schema_version": CATALOG_SCHEMA_VERSION,
        "repository": CATALOG_REPOSITORY,
        "generated_for": "MediaHub Plugin-Store",
        "plugins": items,
    }

    CATALOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CATALOG_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    raw = CATALOG_PATH.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        raise RuntimeError(
            f"Plugin-Katalog wurde unerwartet mit UTF-8-BOM geschrieben: "
            f"{CATALOG_PATH}"
        )

    print(f"Plugin-Store-Katalog aktualisiert: {CATALOG_PATH}")
    return CATALOG_PATH


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
    shutil.copytree(source, target, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo", ".pytest_cache"))

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
    update_catalog(plugins)
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
