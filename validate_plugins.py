from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MEDIAHUB_ROOT = ROOT / "plugins"
AI_NODE_ROOT = ROOT / "ai_node_plugins"

MEDIAHUB_REQUIRED = (
    "id",
    "name",
    "version",
    "entry",
    "minimum_mediahub",
)

AI_NODE_REQUIRED = (
    "id",
    "name",
    "version",
    "type",
    "entrypoint",
    "api_version",
)

INVALID_LICENSE_VALUES = {
    "",
    "tbd",
    "todo",
    "unknown",
    "none",
    "n/a",
    "not specified",
}


def _load_manifest(path: Path, errors: list[str]) -> dict | None:
    try:
        raw = path.read_bytes()

        if raw.startswith(b"\xef\xbb\xbf"):
            errors.append(
                f"{path}: UTF-8-BOM ist nicht erlaubt"
            )
            return None

        return json.loads(raw.decode("utf-8"))

    except Exception as exc:
        errors.append(
            f"{path}: ungültiges JSON: {exc}"
        )
        return None


def _invalid_license(value) -> bool:
    return (
        str(value or "")
        .strip()
        .casefold()
        in INVALID_LICENSE_VALUES
    )


def _validate_third_party_license(
    manifest: Path,
    entry,
    index: int,
    errors: list[str],
) -> None:

    if not isinstance(entry, dict):
        errors.append(
            f"{manifest}: third_party_licenses[{index}] "
            "muss ein Objekt sein"
        )
        return

    required = (
        "name",
        "vendor",
        "usage",
        "bundled",
        "homepage",
        "license",
    )

    missing = []

    for key in required:
        if key not in entry:
            missing.append(key)
            continue

        if key != "bundled":
            if not str(entry.get(key) or "").strip():
                missing.append(key)

    if missing:
        errors.append(
            f"{manifest}: third_party_licenses[{index}] "
            f"unvollständig: {', '.join(missing)}"
        )

    if not isinstance(entry.get("bundled"), bool):
        errors.append(
            f"{manifest}: third_party_licenses[{index}].bundled "
            "muss true oder false sein"
        )

    if _invalid_license(entry.get("license")):
        errors.append(
            f"{manifest}: third_party_licenses[{index}].license "
            "darf nicht leer oder TBD sein"
        )


def _validate_mediahub_license(
    manifest: Path,
    data: dict,
    errors: list[str],
) -> None:

    license_data = data.get("license")

    if not isinstance(license_data, dict):
        errors.append(
            f"{manifest}: license-Block fehlt"
        )
        return

    project_license = license_data.get(
        "project_license"
    )

    if _invalid_license(project_license):
        errors.append(
            f"{manifest}: project_license "
            "darf nicht leer oder TBD sein"
        )

    elif str(project_license).strip() != "Proprietary":
        errors.append(
            f"{manifest}: MediaHub-Plugin muss "
            'project_license="Proprietary" verwenden'
        )

    third_party = license_data.get(
        "third_party_licenses"
    )

    if not isinstance(third_party, list):
        errors.append(
            f"{manifest}: third_party_licenses "
            "muss eine Liste sein"
        )
        return

    for index, entry in enumerate(third_party):
        _validate_third_party_license(
            manifest,
            entry,
            index,
            errors,
        )


def _validate_ai_node_license(
    manifest: Path,
    data: dict,
    errors: list[str],
) -> None:

    value = data.get("license")

    if isinstance(value, dict):
        value = value.get("project_license")

    if _invalid_license(value):
        errors.append(
            f"{manifest}: AI-Node-Plugin benötigt "
            "eine gültige Lizenzangabe"
        )


def _validate_mediahub_plugin(
    directory: Path,
    manifest: Path,
    errors: list[str],
) -> None:

    data = _load_manifest(
        manifest,
        errors,
    )

    if data is None:
        return

    missing = [
        key
        for key in MEDIAHUB_REQUIRED
        if not str(data.get(key, "")).strip()
    ]

    if missing:
        errors.append(
            f"{manifest}: Pflichtfelder fehlen: "
            f"{', '.join(missing)}"
        )

    _validate_mediahub_license(
        manifest,
        data,
        errors,
    )

    entry = directory / str(
        data.get("entry", "")
    )

    if not entry.is_file():
        errors.append(
            f"{manifest}: Einstieg nicht gefunden: "
            f"{entry}"
        )


def _validate_ai_node_plugin(
    directory: Path,
    manifest: Path,
    errors: list[str],
) -> None:

    data = _load_manifest(
        manifest,
        errors,
    )

    if data is None:
        return

    missing = [
        key
        for key in AI_NODE_REQUIRED
        if not str(data.get(key, "")).strip()
    ]

    if missing:
        errors.append(
            f"{manifest}: AI-Node-Pflichtfelder fehlen: "
            f"{', '.join(missing)}"
        )

    _validate_ai_node_license(
        manifest,
        data,
        errors,
    )

    entrypoint = str(
        data.get("entrypoint") or ""
    )

    if ":" not in entrypoint:
        errors.append(
            f"{manifest}: entrypoint muss "
            f"'modul:Objekt' verwenden: "
            f"{entrypoint!r}"
        )

    else:
        module_name = (
            entrypoint
            .split(":", 1)[0]
            .strip()
        )

        module_file = directory / (
            module_name.replace(".", "/")
            + ".py"
        )

        package_init = (
            directory
            / module_name.replace(".", "/")
            / "__init__.py"
        )

        if (
            not module_file.is_file()
            and not package_init.is_file()
        ):
            errors.append(
                f"{manifest}: Entrypoint-Modul "
                f"nicht gefunden: {module_name}"
            )


def _plugin_dirs(root: Path):

    if not root.exists():
        return []

    return [
        directory
        for directory in sorted(root.iterdir())
        if directory.is_dir()
        and (directory / "plugin.json").is_file()
    ]


def main() -> int:

    errors: list[str] = []

    # Zentrale Pflichtdateien.
    for path in (
        ROOT / "LICENSE",
        ROOT / "THIRD_PARTY_LICENSES.md",
    ):
        if (
            not path.is_file()
            or path.stat().st_size == 0
        ):
            errors.append(
                "Repository-Pflichtdatei fehlt "
                f"oder ist leer: {path.name}"
            )

    mediahub_dirs = _plugin_dirs(
        MEDIAHUB_ROOT
    )

    ai_dirs = _plugin_dirs(
        AI_NODE_ROOT
    )

    for directory in mediahub_dirs:
        _validate_mediahub_plugin(
            directory,
            directory / "plugin.json",
            errors,
        )

    for directory in ai_dirs:
        _validate_ai_node_plugin(
            directory,
            directory / "plugin.json",
            errors,
        )

    # IDs repositoryweit eindeutig halten.
    ids: dict[str, Path] = {}

    for directory in [
        *mediahub_dirs,
        *ai_dirs,
    ]:
        manifest = (
            directory
            / "plugin.json"
        )

        data = _load_manifest(
            manifest,
            errors,
        )

        if data is None:
            continue

        plugin_id = str(
            data.get("id") or ""
        ).strip()

        if not plugin_id:
            continue

        previous = ids.get(plugin_id)

        if previous is not None:
            errors.append(
                f"Doppelte Plugin-ID "
                f"{plugin_id!r}: "
                f"{previous} und {manifest}"
            )
        else:
            ids[plugin_id] = manifest

    if (
        not mediahub_dirs
        and not ai_dirs
    ):
        errors.append(
            "Keine Plugin-Quellen mit "
            "plugin.json gefunden."
        )

    if errors:
        print(
            "\n".join(
                f"FEHLER: {error}"
                for error in errors
            ),
            file=sys.stderr,
        )
        return 1

    print(
        f"OK: {len(mediahub_dirs)} "
        "MediaHub-Plugin(s) und "
        f"{len(ai_dirs)} "
        "AI-Node-Plugin(s) geprüft "
        "(inkl. Lizenzprüfung)."
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
