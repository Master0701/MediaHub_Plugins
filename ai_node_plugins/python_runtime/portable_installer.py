"""Sichere lokale ZIP-Pruefung fuer die portable Python-Runtime."""

from __future__ import annotations

import hashlib
import re
import zipfile
from pathlib import Path, PurePosixPath


TEST_SHA256 = (
    "DC0878188B542087C80B35DB7C35E218C2D9D863AA5CF53A24312EAB993DA714"
)

REQUIRED_FILES = {
    "python.exe",
    "Lib/venv/__init__.py",
    "Lib/ensurepip/__init__.py",
    "LICENSE.txt",
}


def verify_archive(package: str | Path, expected_sha256: str) -> dict:
    package = Path(package)

    if not isinstance(expected_sha256, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", expected_sha256):
        raise ValueError("Ungueltiger SHA256-Pruefwert.")

    if not package.is_file():
        raise FileNotFoundError(package)

    digest = hashlib.sha256()

    with package.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)

    actual = digest.hexdigest().upper()

    if actual != expected_sha256.upper():
        raise ValueError("SHA256-Pruefung fehlgeschlagen.")

    with zipfile.ZipFile(package) as archive:
        names = set()
        windows_names = set()

        for entry in archive.infolist():
            name = entry.filename.replace("\\", "/")
            parts = PurePosixPath(name).parts

            if (
                name.startswith("/")
                or ".." in parts
                or ":" in name
                or not name.strip()
                or any(part in {"", "."} for part in name.rstrip("/").split("/"))
            ):
                raise ValueError(f"Unsicherer ZIP-Pfad: {name}")

            if name in names:
                raise ValueError(f"Doppelter ZIP-Eintrag: {name}")

            # Symbolische Links aus Unix-ZIP-Archiven ablehnen.
            unix_mode = entry.external_attr >> 16
            if entry.create_system == 3 and (unix_mode & 0o170000) == 0o120000:
                raise ValueError(f"Symbolischer Link nicht erlaubt: {name}")

            # Windows-reservierte Namen und problematische Pfade ablehnen.
            for part in parts:
                stem = part.split(".")[0].upper()
                if (
                    part.endswith((" ", "."))
                    or stem in {"CON", "PRN", "AUX", "NUL"}
                    or stem in {f"COM{i}" for i in range(1, 10)}
                    or stem in {f"LPT{i}" for i in range(1, 10)}
                ):
                    raise ValueError(f"Ungueltiger Windows-Pfad: {name}")

            # Windows behandelt Dateinamen normalerweise ohne
            # Unterscheidung zwischen Gross- und Kleinschreibung.
            windows_name = name.rstrip("/").casefold()

            if windows_name in windows_names:
                raise ValueError(
                    f"Windows-Dateinamenskollision: {name}"
                )

            windows_names.add(windows_name)
            names.add(name)

        # Begrenzung gegen uebermaessig grosse ZIP-Archive.
        if len(names) > 20000:
            raise ValueError("Zu viele ZIP-Eintraege.")

        total_size = sum(entry.file_size for entry in archive.infolist())
        if total_size > 1024 * 1024 * 1024:
            raise ValueError("ZIP-Inhalt ist zu gross.")

        # Eine Datei darf nicht zugleich als Verzeichnis
        # fuer andere Archiveintraege verwendet werden.
        file_paths = {
            entry.filename.replace("\\", "/").casefold()
            for entry in archive.infolist()
            if not entry.is_dir()
        }

        for entry in archive.infolist():
            name = entry.filename.replace("\\", "/").rstrip("/")
            parts = name.split("/")

            for index in range(1, len(parts)):
                parent = "/".join(parts[:index]).casefold()

                if parent in file_paths:
                    raise ValueError(
                        f"Datei-/Verzeichniskollision: {name}"
                    )

            if entry.is_dir() and name.casefold() in file_paths:
                raise ValueError(
                    f"Datei-/Verzeichniskollision: {name}"
                )

        missing = REQUIRED_FILES - names

        if missing:
            raise ValueError(f"Pflichtdateien fehlen: {sorted(missing)}")

        bad_member = archive.testzip()

        if bad_member is not None:
            raise ValueError(f"ZIP-Pruefung fehlgeschlagen: {bad_member}")

    return {
        "verified": True,
        "sha256": actual,
        "entries": len(names),
    }




def is_directory_link(path: str | Path) -> bool:
    """Erkennt symbolische Links und Windows-Junctions."""
    path = Path(path)
    return path.is_symlink() or (
        hasattr(path, "is_junction") and path.is_junction()
    )

def extract_verified_archive(
    package: str | Path,
    target: str | Path,
    expected_sha256: str,
) -> Path:
    """Entpackt ein geprueftes ZIP ausschliesslich in ein neues Ziel."""
    import shutil

    package = Path(package)
    target = Path(target)

    verify_archive(package, expected_sha256)

    if target.exists() or target.is_symlink():
        raise FileExistsError(
            f"Zielverzeichnis existiert bereits: {target}"
        )

    if not target.parent.is_dir():
        raise FileNotFoundError(
            f"Ziel-Ueberverzeichnis fehlt: {target.parent}"
        )

    # Alle uebergeordneten Verzeichnisse kontrollieren.
    for parent in (target.parent, *target.parent.parents):
        if is_directory_link(parent):
            raise ValueError(
                f"Verknuepfter Ziel-Ueberordner nicht erlaubt: {parent}"
            )

    written = 0
    limit = 1024 * 1024 * 1024

    created_target = False

    try:
        target.mkdir()
        created_target = True

        with zipfile.ZipFile(package) as archive:
            for entry in archive.infolist():
                name = entry.filename.replace("\\", "/")
                destination = target.joinpath(*PurePosixPath(name).parts)

                if entry.is_dir() or name.endswith("/"):
                    destination.mkdir(parents=True, exist_ok=True)
                    continue

                destination.parent.mkdir(parents=True, exist_ok=True)

                with archive.open(entry) as source_file:
                    with destination.open("xb") as output:
                        while True:
                            chunk = source_file.read(1024 * 1024)

                            if not chunk:
                                break

                            written += len(chunk)

                            if written > limit:
                                raise ValueError(
                                    "Entpackte Datenmenge zu gross."
                                )

                            output.write(chunk)

        return target

    except Exception:
        # Nur ein nachweislich selbst angelegtes Ziel entfernen.
        if created_target and target.is_dir() and not is_directory_link(target):
            shutil.rmtree(target)
        raise


def install_verified_runtime(
    package: str | Path,
    target: str | Path,
    expected_sha256: str,
) -> dict:
    """Installiert eine gepruefte Runtime und kontrolliert ihre Funktion."""
    import importlib.util

    plugin_path = Path(__file__).with_name("plugin.py")
    spec = importlib.util.spec_from_file_location(
        "mediahub_python_runtime_inspection",
        plugin_path,
    )

    if spec is None or spec.loader is None:
        raise RuntimeError("Runtime-Pruefmodul konnte nicht geladen werden.")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    target = Path(target)

    # Vorhandene Installationen niemals ueberschreiben.
    if target.exists() or target.is_symlink():
        raise FileExistsError(f"Runtime-Ziel existiert bereits: {target}")

    # Fehlende Elternverzeichnisse bei einer Erstinstallation selbst anlegen.
    # Vorhandene Junctions/Symlinks in der Zielkette nicht durchlaufen.
    for parent in (target.parent, *target.parent.parents):
        if is_directory_link(parent):
            raise ValueError(f"Verknuepfter Ziel-Ueberordner nicht erlaubt: {parent}")
    target.parent.mkdir(parents=True, exist_ok=True)

    # Die Runtime wird zunaechst in einem separaten Ordner geprueft.
    import uuid
    staging = target.with_name(
        target.name + ".staging-" + uuid.uuid4().hex
    )

    extract_verified_archive(package, staging, expected_sha256)

    try:
        result = module.inspect_runtime(staging)

        if not result.get("ready", False):
            raise RuntimeError(
                f"Entpackte Python-Runtime ist nicht einsatzbereit: {result}"
            )

        # Erst nach erfolgreicher Pruefung endgueltig uebernehmen.
        # Vorhandene Ziele duerfen nicht ersetzt werden.
        if target.exists() or target.is_symlink() or is_directory_link(target):
            raise FileExistsError(
                f"Runtime-Ziel wurde inzwischen angelegt: {target}"
            )

        # Windows kann Dateien nach dem Runtime-Check kurzfristig sperren.
        # Nur temporaere Zugriffsfehler beim finalen Umbenennen wiederholen.
        import time
        for attempt in range(10):
            if target.exists() or target.is_symlink() or is_directory_link(target):
                raise FileExistsError(
                    f"Runtime-Ziel wurde inzwischen angelegt: {target}"
                )
            try:
                staging.rename(target)
                break
            except PermissionError as exc:
                if attempt == 9:
                    raise PermissionError(
                        f"Runtime konnte nach 10 Versuchen nicht uebernommen werden: {target}"
                    ) from exc
                time.sleep(1)

        # Der zurueckgegebene Pfad muss auf die fertige Runtime zeigen.
        return module.inspect_runtime(target)

    except Exception:
        # Nur den selbst angelegten Staging-Ordner bereinigen.
        # Vorhandene Installationen bleiben unangetastet.
        if staging.is_dir() and not is_directory_link(staging):
            import shutil
            shutil.rmtree(staging)
        raise
