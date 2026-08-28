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
AI_NODE_PLUGINS_DIR = ROOT / "ai_node_plugins"
SHARED_DIR = ROOT / "shared"
RELEASE_DIR = ROOT / "release"

MEDIAHUB_CATALOG_PATH = ROOT / "catalog" / "plugin_catalog.json"
AI_NODE_CATALOG_PATH = ROOT / "catalog" / "ai_plugin_catalog.json"

CATALOG_REPOSITORY = "Master0701/MediaHub_Plugins"

CATEGORY_BY_ID = {
    "mediahub.web_remote": "Fernsteuerung",
    "mediahub.mobile_dashboard": "Mobil",
    "mediahub.metadata_editor": "Metadaten",
    "mediahub.ai_assistant": "KI und Analyse",
    "mediahub.smart_renamer": "Dateien und Umbenennung",
    "mediahub.audio_metadata_editor": "Hörbücher",
    "mediahub.list_exporter": "Listen und Export",
}


def discover_plugins() -> dict[str, Path]:
    """Bestehende MediaHub-Plugins unter plugins/."""
    plugins: dict[str, Path] = {}
    if not PLUGINS_DIR.exists():
        return plugins
    for manifest_path in sorted(PLUGINS_DIR.glob("*/plugin.json")):
        plugins[manifest_path.parent.name] = manifest_path.parent
    return plugins


def discover_ai_node_plugins() -> dict[str, Path]:
    """AI-Node-/Raspberry-Pi-Plugins unter ai_node_plugins/."""
    plugins: dict[str, Path] = {}
    if not AI_NODE_PLUGINS_DIR.exists():
        return plugins
    for manifest_path in sorted(AI_NODE_PLUGINS_DIR.glob("*/plugin.json")):
        plugins[manifest_path.parent.name] = manifest_path.parent
    return plugins


def read_manifest(source: Path) -> dict:
    return json.loads((source / "plugin.json").read_text(encoding="utf-8"))


def safe_package_name(manifest: dict, fallback: str) -> str:
    name = (
        str(manifest.get("name", fallback))
        .replace("MediaHub ", "")
        .replace(" ", "")
    )
    return "".join(c for c in name if c.isalnum() or c in "-_")


def safe_ai_package_name(manifest: dict, fallback: str) -> str:
    configured = str(manifest.get("package_name") or "").strip()
    if configured:
        name = configured
    else:
        name = str(manifest.get("name", fallback)).replace("MediaHub ", "")
    name = name.replace(" ", "")
    return "".join(c for c in name if c.isalnum() or c in "-_")


def create_sha256(file_path: Path) -> Path:
    digest = hashlib.sha256(file_path.read_bytes()).hexdigest()
    checksum_path = file_path.with_suffix(file_path.suffix + ".sha256")
    checksum_path.write_text(
        f"{digest} {file_path.name}\n",
        encoding="utf-8",
    )
    print(f"Prüfsumme erstellt: {checksum_path}")
    return checksum_path


def _catalog_status(version: str) -> str:
    return "planned" if version == "0.0.0" else "available"


def _mediahub_project_page(plugin_key: str, catalog: dict) -> str:
    configured = str(catalog.get("project_page") or "").strip()
    if configured:
        return configured
    return (
        "https://github.com/Master0701/MediaHub_Plugins/"
        f"tree/main/plugins/{plugin_key}"
    )


def _ai_project_page(plugin_key: str, manifest: dict) -> str:
    catalog = manifest.get("catalog") or {}
    configured = str(
        catalog.get("project_page")
        or manifest.get("project_page")
        or manifest.get("homepage")
        or ""
    ).strip()
    if configured:
        return configured
    return (
        "https://github.com/Master0701/MediaHub_Plugins/"
        f"tree/main/ai_node_plugins/{plugin_key}"
    )


def update_catalog(plugins: dict[str, Path]) -> Path:
    """Erzeugt den bestehenden MediaHub-Plugin-Store-Katalog (Schema 2)."""
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
        publishable = version != "0.0.0"
        package_name = safe_package_name(manifest, key)
        release_asset = f"MediaHub_{package_name}_v{version}.mhplugin"

        auto_install = bool(catalog.get("auto_install", publishable))
        manual_only = bool(catalog.get("manual_only", False))
        manual_message = str(
            catalog.get("manual_install_message") or ""
        ).strip()

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
                "status": _catalog_status(version),
                "category": str(
                    catalog.get("category")
                    or CATEGORY_BY_ID.get(plugin_id, "Erweiterung")
                ),
                "visible": True,
                "auto_install": auto_install,
                "manual_only": manual_only,
                "description": str(manifest.get("description", "")),
                "minimum_mediahub_version": minimum,
                "project_page": _mediahub_project_page(key, catalog),
                "manual_install_message": manual_message,
                "release_asset": release_asset,
                "sha256_asset": release_asset + ".sha256",
            }
        )

    payload = {
        "schema_version": 2,
        "repository": CATALOG_REPOSITORY,
        "generated_for": "MediaHub Plugin-Store",
        "plugins": items,
    }

    MEDIAHUB_CATALOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    MEDIAHUB_CATALOG_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    _assert_no_bom(MEDIAHUB_CATALOG_PATH)
    print(f"MediaHub-Plugin-Katalog aktualisiert: {MEDIAHUB_CATALOG_PATH}")
    return MEDIAHUB_CATALOG_PATH


def update_ai_node_catalog(plugins: dict[str, Path]) -> Path:
    """Erzeugt den von MediaHub bereits erwarteten AI-Node-Katalog."""
    items: list[dict] = []

    for key, source in sorted(plugins.items()):
        manifest = read_manifest(source)
        catalog = manifest.get("catalog") or {}

        if not bool(catalog.get("visible", True)):
            continue

        version = str(manifest["version"])
        package_name = safe_ai_package_name(manifest, key)
        release_asset = (
            f"MediaHub_{package_name}_v{version}.mhaiplugin"
        )

        items.append(
            {
                "id": str(manifest["id"]),
                "name": str(manifest["name"]),
                "version": version,
                "type": str(manifest.get("type") or ""),
                "api_version": str(manifest.get("api_version") or ""),
                "description": str(manifest.get("description") or ""),
                "visible": True,
                "project_page": _ai_project_page(key, manifest),
                "package_asset": release_asset,
                "release_asset": release_asset,
                "sha256_asset": release_asset + ".sha256",
                "targets": list(
                    manifest.get("targets") or [
                        "raspberry_pi"
                    ]
                ),
                "platforms": list(
                    manifest.get("platforms") or []
                ),
                "required_capabilities": list(
                    manifest.get(
                        "required_capabilities"
                    )
                    or []
                ),
            }
        )

    payload = {
        "schema_version": 1,
        "repository": CATALOG_REPOSITORY,
        "generated_for": "MediaHub AI-Plugin-Store",
        "package_extension": ".mhaiplugin",
        "plugins": items,
    }

    AI_NODE_CATALOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    AI_NODE_CATALOG_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    _assert_no_bom(AI_NODE_CATALOG_PATH)
    print(f"AI-Node-Plugin-Katalog aktualisiert: {AI_NODE_CATALOG_PATH}")
    return AI_NODE_CATALOG_PATH


def _assert_no_bom(path: Path) -> None:
    if path.read_bytes().startswith(b"\xef\xbb\xbf"):
        raise RuntimeError(f"Katalog enthält UTF-8-BOM: {path}")


def clean_release_directory() -> None:
    if RELEASE_DIR.exists():
        shutil.rmtree(RELEASE_DIR)
    RELEASE_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Release-Ordner bereinigt: {RELEASE_DIR}")


def copy_shared_runtime(package_root: Path, manifest: dict) -> None:
    shared_runtimes = manifest.get("shared_runtimes")

    if shared_runtimes is None:
        legacy_runtime = manifest.get("shared_runtime")
        shared_runtimes = [legacy_runtime] if legacy_runtime else []

    if isinstance(shared_runtimes, str):
        shared_runtimes = [shared_runtimes]

    if not isinstance(shared_runtimes, list):
        raise TypeError(
            "shared_runtimes muss eine Liste von Runtime-Namen sein."
        )

    for shared_runtime in shared_runtimes:
        if not isinstance(shared_runtime, str) or not shared_runtime.strip():
            raise ValueError(
                "Ungültiger Eintrag in shared_runtimes."
            )

        shared_runtime = shared_runtime.strip()

        source = SHARED_DIR / shared_runtime
        if not source.is_dir():
            raise FileNotFoundError(
                f"Gemeinsame Laufzeit fehlt: {source}"
            )

        target = package_root / "shared" / shared_runtime
        target.parent.mkdir(parents=True, exist_ok=True)

        shutil.copytree(
            source,
            target,
            ignore=shutil.ignore_patterns(
                "__pycache__",
                "*.pyc",
                "*.pyo",
                ".pytest_cache",
            ),
        )


def build_plugin(key: str, source: Path) -> Path:
    manifest = read_manifest(source)
    for required in (
        "id",
        "name",
        "version",
        "entry",
        "minimum_mediahub",
        "permissions",
    ):
        if required not in manifest:
            raise ValueError(
                f"Fehlendes Pflichtfeld '{required}' in {source / 'plugin.json'}"
            )

    version = str(manifest["version"])
    plugin_id = str(manifest["id"])
    package_name = safe_package_name(manifest, key)

    RELEASE_DIR.mkdir(parents=True, exist_ok=True)
    output = (
        RELEASE_DIR
        / f"MediaHub_{package_name}_v{version}.mhplugin"
    )

    with tempfile.TemporaryDirectory() as tmp:
        temp_root = Path(tmp)
        package_root = temp_root / plugin_id

        shutil.copytree(
            source,
            package_root,
            ignore=shutil.ignore_patterns(
                "__pycache__",
                "*.pyc",
                "*.pyo",
                ".pytest_cache",
            ),
        )
        copy_shared_runtime(package_root, manifest)

        with zipfile.ZipFile(
            output,
            "w",
            compression=zipfile.ZIP_DEFLATED,
        ) as archive:
            for file in sorted(package_root.rglob("*")):
                if file.is_file():
                    archive.write(file, file.relative_to(temp_root))

    create_sha256(output)
    print(f"MediaHub-Plugin erstellt: {output}")
    return output


def build_ai_node_plugin(key: str, source: Path) -> Path:
    manifest = read_manifest(source)
    for required in (
        "id",
        "name",
        "version",
        "type",
        "entrypoint",
        "api_version",
    ):
        if not str(manifest.get(required, "")).strip():
            raise ValueError(
                f"Fehlendes Pflichtfeld '{required}' in {source / 'plugin.json'}"
            )

    version = str(manifest["version"])
    plugin_id = str(manifest["id"])
    package_name = safe_ai_package_name(manifest, key)

    RELEASE_DIR.mkdir(parents=True, exist_ok=True)
    output = (
        RELEASE_DIR
        / f"MediaHub_{package_name}_v{version}.mhaiplugin"
    )

    with tempfile.TemporaryDirectory() as tmp:
        temp_root = Path(tmp)
        package_root = temp_root / plugin_id

        shutil.copytree(
            source,
            package_root,
            ignore=shutil.ignore_patterns(
                "__pycache__",
                "*.pyc",
                "*.pyo",
                ".pytest_cache",
            ),
        )

        with zipfile.ZipFile(
            output,
            "w",
            compression=zipfile.ZIP_DEFLATED,
        ) as archive:
            for file in sorted(package_root.rglob("*")):
                if file.is_file():
                    archive.write(file, file.relative_to(temp_root))

    create_sha256(output)
    print(f"AI-Node-Plugin erstellt: {output}")
    return output


def _selector_maps(
    mediahub_plugins: dict[str, Path],
    ai_plugins: dict[str, Path],
) -> dict[str, tuple[str, str, Path]]:
    choices: dict[str, tuple[str, str, Path]] = {}

    for key, source in mediahub_plugins.items():
        choices[key] = ("mediahub", key, source)

    for key, source in ai_plugins.items():
        selector = key
        if selector in choices:
            selector = f"ai:{key}"
        choices[selector] = ("ai_node", key, source)

    return choices


def main() -> int:
    mediahub_plugins = discover_plugins()
    ai_plugins = discover_ai_node_plugins()

    if not mediahub_plugins and not ai_plugins:
        print("FEHLER: Keine Plugin-Quellen gefunden.")
        return 1

    update_catalog(mediahub_plugins)
    update_ai_node_catalog(ai_plugins)

    selectors = _selector_maps(mediahub_plugins, ai_plugins)

    parser = argparse.ArgumentParser(
        description=(
            "Erstellt MediaHub-.mhplugin- und "
            "AI-Node-.mhaiplugin-Pakete."
        )
    )
    parser.add_argument(
        "plugin",
        nargs="?",
        default="all",
        choices=[*selectors, "all", "mediahub", "ai_node"],
        help=(
            "Plugin-Ordnername, 'mediahub', 'ai_node' oder 'all'. "
            "Bei Namenskollisionen AI-Plugin als 'ai:<name>' wählen."
        ),
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Leert vor dem Build den release-Ordner.",
    )
    args = parser.parse_args()

    if args.clean:
        clean_release_directory()
    else:
        RELEASE_DIR.mkdir(parents=True, exist_ok=True)

    built = 0

    if args.plugin in ("all", "mediahub"):
        for key, source in mediahub_plugins.items():
            build_plugin(key, source)
            built += 1

    if args.plugin in ("all", "ai_node"):
        for key, source in ai_plugins.items():
            build_ai_node_plugin(key, source)
            built += 1

    if args.plugin not in ("all", "mediahub", "ai_node"):
        kind, key, source = selectors[args.plugin]
        if kind == "mediahub":
            build_plugin(key, source)
        else:
            build_ai_node_plugin(key, source)
        built += 1

    print(
        "Build abgeschlossen: "
        f"{built} Plugin(s) "
        f"({len(mediahub_plugins)} MediaHub, "
        f"{len(ai_plugins)} AI-Node erkannt)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
