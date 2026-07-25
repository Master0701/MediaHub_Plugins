from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
if not (ROOT / "plugins").is_dir():
    # Das Skript liegt normalerweise im entpackten Unterordner.
    candidate = ROOT.parent
    if (candidate / "plugins").is_dir():
        ROOT = candidate
    else:
        raise SystemExit(
            "FEHLER: Der Ordner 'plugins' wurde nicht gefunden. "
            "Das Skript muss im Hauptordner von MediaHub-Plugins ausgeführt werden."
        )

PLUGINS_DIR = ROOT / "plugins"
RELEASE_DIR = ROOT / "release"
CATALOG_DIR = ROOT / "catalog"
OUTPUT = CATALOG_DIR / "plugin_catalog.json"
AI_OUTPUT = CATALOG_DIR / "ai_plugin_catalog.json"

SPECIAL_NAMES = {
    "ai_assistant": "MediaHub KI-Assistent",
    "audiobook_manager": "MediaHub Hörbuchverwaltung",
    "list_exporter": "MediaHub Listen & Export",
    "metadata_editor": "MediaHub Metadata Editor",
    "mobile_dashboard": "MediaHub Mobile Dashboard",
    "smart_renamer": "MediaHub Smart Renamer",
    "web_remote": "MediaHub WebRemote",
}

PACKAGE_NAMES = {
    "ai_assistant": "MediaHub_KI-Assistent_v{version}.mhplugin",
    "audiobook_manager": "MediaHub_Hoerbuchverwaltung_v{version}.mhplugin",
    "list_exporter": "MediaHub_ListenExport_v{version}.mhplugin",
    "metadata_editor": "MediaHub_MetadataEditor_v{version}.mhplugin",
    "mobile_dashboard": "MediaHub_MobileDashboard_v{version}.mhplugin",
    "smart_renamer": "MediaHub_SmartRenamer_v{version}.mhplugin",
    "web_remote": "MediaHub_WebRemote_v{version}.mhplugin",
}

CATEGORIES = {
    "ai_assistant": "KI und Analyse",
    "audiobook_manager": "Hörbücher",
    "list_exporter": "Listen und Export",
    "metadata_editor": "Metadaten",
    "mobile_dashboard": "Mobil",
    "smart_renamer": "Dateien und Umbenennung",
    "web_remote": "Fernsteuerung",
}

DESCRIPTIONS = {
    "audiobook_manager": (
        "Vorbereitetes Hörbuch-Plugin für Erkennung, Verwaltung, "
        "Metadaten, Cover und spätere Quellenanbindung."
    ),
    "list_exporter": (
        "Erstellt frei konfigurierbare Medienlisten und exportiert "
        "sie später in verschiedene Ausgabeformate."
    ),
    "smart_renamer": (
        "Universelles Umbenennungs-Plugin mit Vorschau, frei "
        "definierbaren Namensschemata und Zusammenarbeit mit "
        "KI-Assistent und Metadata Editor."
    ),
}


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as error:
        raise SystemExit(f"FEHLER in {path}: {error}") from error

    if not isinstance(value, dict):
        raise SystemExit(f"FEHLER: {path} enthält kein JSON-Objekt.")
    return value


def first_text(data: dict[str, Any], *keys: str, default: str = "") -> str:
    for key in keys:
        value = data.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return default


def minimum_mediahub(data: dict[str, Any]) -> str:
    return first_text(
        data,
        "minimum_mediahub_version",
        "minimum_mediahub",
        "min_mediahub_version",
        default="",
    )


def package_exists(template: str, version: str) -> bool:
    package_name = template.format(version=version)
    return (RELEASE_DIR / package_name).is_file()


def build_entry(folder: Path) -> dict[str, Any]:
    manifest_path = folder / "plugin.json"
    manifest = read_json(manifest_path)

    folder_name = folder.name
    plugin_id = first_text(
        manifest,
        "id",
        "plugin_id",
        default=f"mediahub.{folder_name}",
    )
    version = first_text(manifest, "version", default="0.0.0")
    name = first_text(
        manifest,
        "name",
        "display_name",
        default=SPECIAL_NAMES.get(folder_name, folder_name),
    )
    description = first_text(
        manifest,
        "description",
        default=DESCRIPTIONS.get(
            folder_name,
            f"MediaHub-Plugin: {name}",
        ),
    )

    package_template = PACKAGE_NAMES.get(
        folder_name,
        f"{folder_name}_v{{version}}.mhplugin",
    )
    is_ai_assistant = folder_name == "ai_assistant"
    is_placeholder = version in {"", "0.0.0", "current", "dev", "development"}
    has_release = package_exists(package_template, version)

    if is_ai_assistant:
        status = "development"
        auto_install = False
        manual_only = True
        availability_message = (
            "Der MediaHub-KI-Assistent läuft direkt in MediaHub und "
            "wird nicht automatisch installiert. Lade die aktuelle "
            ".mhplugin-Datei manuell von seiner GitHub-Projektseite."
        )
    elif is_placeholder or not has_release:
        status = "planned" if is_placeholder else "package_missing"
        auto_install = False
        manual_only = False
        availability_message = (
            "Für diese Version ist derzeit noch kein installierbares "
            "Release-Paket verfügbar."
        )
    else:
        status = "available"
        auto_install = True
        manual_only = False
        availability_message = ""

    entry: dict[str, Any] = {
        "id": plugin_id,
        "name": name,
        "version": version,
        "status": status,
        "category": CATEGORIES.get(folder_name, "Erweiterung"),
        "visible": True,
        "auto_install": auto_install,
        "manual_only": manual_only,
        "description": description,
        "minimum_mediahub_version": minimum_mediahub(manifest),
        "project_page": (
            "https://github.com/Master0701/MediaHub_Plugins/"
            f"tree/main/plugins/{folder_name}"
        ),
        "manual_install_message": availability_message,
    }

    if not is_ai_assistant:
        entry["release_asset"] = package_template
        entry["sha256_asset"] = package_template + ".sha256"

    return entry


def main() -> None:
    plugin_folders = sorted(
        path
        for path in PLUGINS_DIR.iterdir()
        if path.is_dir() and (path / "plugin.json").is_file()
    )

    if not plugin_folders:
        raise SystemExit("FEHLER: Keine Plugins mit plugin.json gefunden.")

    entries = [build_entry(folder) for folder in plugin_folders]

    catalog = {
        "schema_version": 2,
        "repository": "Master0701/MediaHub_Plugins",
        "generated_for": "MediaHub Plugin-Store",
        "plugins": entries,
    }

    CATALOG_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(catalog, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    ai_catalog = {
        "schema_version": 1,
        "repository": "Master0701/MediaHub_Plugins",
        "generated_for": "MediaHub AI-Plugin-Store",
        "package_extension": ".mhaiplugin",
        "plugins": [],
    }
    AI_OUTPUT.write_text(
        json.dumps(ai_catalog, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    print(f"Katalog aktualisiert: {OUTPUT}")
    print(f"AI-Katalog aktualisiert: {AI_OUTPUT}")
    print(f"Plugins eingetragen: {len(entries)}")
    print("AI-Plugins eingetragen: 0")
    print()

    for entry in entries:
        mode = (
            "automatisch installierbar"
            if entry["auto_install"]
            else (
                "manuelle Installation"
                if entry["manual_only"]
                else "noch nicht installierbar"
            )
        )
        print(
            f"- {entry['name']} v{entry['version']} "
            f"[{entry['status']}; {mode}]"
        )


if __name__ == "__main__":
    main()
