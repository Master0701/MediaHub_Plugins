"""Explicitly approved, local-only llama.cpp ZIP installation.

No downloads, no overwrite, no removal of existing user data. The caller must
obtain confirmation independently and supply an independently trusted SHA256.
"""
from __future__ import annotations

import hashlib
import os
import re
import shutil
import stat
import tempfile
import zipfile
from pathlib import Path, PurePosixPath


class SafeInstallError(RuntimeError):
    pass


def preflight_local_archive(*, archive_path: str, expected_sha256: str, model: bool = False) -> dict:
    """Read-only structural and checksum verification before either installation.

    Does not create files, trust an in-archive digest, or execute binaries.
    """
    if not re.fullmatch(r"[a-fA-F0-9]{64}", expected_sha256):
        raise SafeInstallError("Ungueltige externe SHA-256-Pruefsumme")
    archive = Path(archive_path).resolve(strict=True)
    if not archive.is_file() or archive.suffix.lower() != ".zip":
        raise SafeInstallError("ZIP fehlt")
    with archive.open("rb") as stream:
        actual = hashlib.file_digest(stream, "sha256").hexdigest()
    if actual.lower() != expected_sha256.lower():
        raise SafeInstallError("ZIP-SHA-256 stimmt nicht")
    with zipfile.ZipFile(archive) as z:
        members = z.infolist()
        if not members or len(members) > 20000:
            raise SafeInstallError("Archiv leer oder zu viele Eintraege")
        names = set()
        matches = []
        total = 0
        for info in members:
            name = info.filename
            parts = PurePosixPath(name).parts
            if not name or name.startswith("/") or "\\" in name or not parts or any(x in (".", "..") for x in parts) or ":" in parts[0]:
                raise SafeInstallError("Unsicherer Archivpfad")
            normalized = name.rstrip("/").casefold()
            if normalized in names:
                raise SafeInstallError("Doppelter Archivpfad")
            names.add(normalized)
            if stat.S_ISLNK(info.external_attr >> 16) or info.flag_bits & 1:
                raise SafeInstallError("Symlink oder verschluesselter Eintrag")
            total += info.file_size
            if total > (8_000_000_000 if model else 2_000_000_000):
                raise SafeInstallError("Archivgroesse ueberschritten")
            if not info.is_dir() and (name.lower().endswith(".gguf") if model else PurePosixPath(name).name.lower() == "llama-server.exe"):
                matches.append(info)
        if len(matches) != 1:
            raise SafeInstallError("Genau eine GGUF-Datei bzw. llama-server.exe erforderlich")
        if model:
            if matches[0].file_size < 16:
                raise SafeInstallError("GGUF zu klein")
            with z.open(matches[0]) as stream:
                if stream.read(4) != b"GGUF":
                    raise SafeInstallError("GGUF-Magic fehlt")
    return {"valid": True, "sha256": actual, "entry": matches[0].filename}


def install_local_archive(*, archive_path: str, expected_sha256: str,
                          target_dir: str, confirmed: bool = False,
                          max_uncompressed_bytes: int = 2_000_000_000) -> dict:
    if confirmed is not True:
        raise SafeInstallError("Explizite Installationsbestaetigung fehlt")
    if not re.fullmatch(r"[a-fA-F0-9]{64}", expected_sha256):
        raise SafeInstallError("Vertrauenswuerdige SHA-256-Pruefsumme erforderlich")
    archive = Path(archive_path).resolve(strict=True)
    target = Path(target_dir).absolute()
    if not archive.is_file() or archive.suffix.lower() != ".zip":
        raise SafeInstallError("Lokales ZIP fehlt")
    if not target.name or target == Path(target.anchor):
        raise SafeInstallError("Ungueltiges Installationsziel")
    if target.exists():
        raise SafeInstallError("Ziel existiert bereits; keine Ueberschreibung")
    if not target.parent.is_dir():
        raise SafeInstallError("Ziel-Elternordner muss bereits existieren")
    if target.parent.is_symlink():
        raise SafeInstallError("Symbolischer Link als Ziel-Elternordner unzulaessig")
    with archive.open("rb") as stream:
        actual = hashlib.file_digest(stream, "sha256").hexdigest()
    if actual.lower() != expected_sha256.lower():
        raise SafeInstallError("SHA-256-Pruefung fehlgeschlagen")
    with zipfile.ZipFile(archive) as z:
        members = z.infolist()
        if not members or len(members) > 20000:
            raise SafeInstallError("Leeres oder uebergrosses Archiv")
        total = 0
        names = set()
        for info in members:
            name = info.filename.replace("\\", "/")
            parts = PurePosixPath(name).parts
            if (not name or name.startswith("/") or "\\" in info.filename
                    or any(part in ("..", ".") for part in parts)
                    or (parts and ":" in parts[0]) or not parts):
                raise SafeInstallError("Unsicherer Archivpfad")
            if name.rstrip("/").casefold() in names:
                raise SafeInstallError("Doppelte Archivdatei")
            names.add(name.rstrip("/").casefold())
            mode = info.external_attr >> 16
            if stat.S_ISLNK(mode):
                raise SafeInstallError("Symlinks im Archiv nicht erlaubt")
            if info.flag_bits & 1:
                raise SafeInstallError("Verschluesseltes Archiv nicht erlaubt")
            total += info.file_size
            if total > max_uncompressed_bytes:
                raise SafeInstallError("Archiv ueberschreitet Groessenlimit")
        servers = [m for m in members if PurePosixPath(m.filename).name.lower() == "llama-server.exe"]
        if len(servers) != 1:
            raise SafeInstallError("Genau eine llama-server.exe erforderlich")
        with tempfile.TemporaryDirectory(prefix=".mediahub-llama-stage-", dir=target.parent) as temp:
            stage = Path(temp)
            for info in members:
                relative = PurePosixPath(info.filename)
                destination = stage.joinpath(*relative.parts)
                if info.is_dir():
                    destination.mkdir(parents=True, exist_ok=True)
                else:
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    with z.open(info) as source, destination.open("xb") as output:
                        shutil.copyfileobj(source, output)
            relative_server = PurePosixPath(servers[0].filename)
            if not stage.joinpath(*relative_server.parts).is_file():
                raise SafeInstallError("llama-server.exe fehlt nach Entpacken")
            if target.exists():
                raise SafeInstallError("Ziel wurde zwischenzeitlich angelegt")
            stage.rename(target)
    return {"ready": True, "backend_verified": False, "server": str(target.joinpath(*relative_server.parts)),
            "root": str(target), "sha256": actual, "requires_runtime_health_check": True}


def install_local_model_archive(*, archive_path: str, expected_sha256: str,
                                target_dir: str, confirmed: bool = False,
                                max_uncompressed_bytes: int = 8_000_000_000) -> dict:
    """Install a local, checksum-verified GGUF model ZIP without replacing data.

    This function intentionally does not download anything and does not prove
    the GGUF can be loaded by llama.cpp. An independent trusted checksum is
    required; checksums supplied by the same untrusted ZIP are insufficient.
    """
    if confirmed is not True:
        raise SafeInstallError("Explizite Modellinstallationsbestaetigung fehlt")
    if not re.fullmatch(r"[a-fA-F0-9]{64}", expected_sha256):
        raise SafeInstallError("Vertrauenswuerdige Modell-ZIP-SHA256 erforderlich")
    archive = Path(archive_path).resolve(strict=True)
    target = Path(target_dir).absolute()
    if not archive.is_file() or archive.suffix.lower() != ".zip":
        raise SafeInstallError("Lokales Modell-ZIP fehlt")
    if target.exists() or target == Path(target.anchor) or not target.parent.is_dir():
        raise SafeInstallError("Modellziel ungueltig oder bereits vorhanden")
    if target.parent.is_symlink():
        raise SafeInstallError("Symlink als Modellziel-Elternordner unzulaessig")
    with archive.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    if digest.lower() != expected_sha256.lower():
        raise SafeInstallError("Modell-ZIP-SHA256 stimmt nicht")
    with zipfile.ZipFile(archive) as z:
        members = z.infolist()
        if not members or len(members) > 20000:
            raise SafeInstallError("Modellarchiv leer oder zu viele Eintraege")
        names = set()
        total = 0
        models = []
        for info in members:
            name = info.filename
            parts = PurePosixPath(name).parts
            if (not name or name.startswith("/") or "\\" in name or
                not parts or any(part in ("..", ".") for part in parts) or
                ":" in parts[0]):
                raise SafeInstallError("Unsicherer Modellarchivpfad")
            normalized = name.rstrip("/").casefold()
            if normalized in names:
                raise SafeInstallError("Doppelter Modellarchivpfad")
            names.add(normalized)
            if stat.S_ISLNK(info.external_attr >> 16) or info.flag_bits & 1:
                raise SafeInstallError("Symlink oder verschluesselter Eintrag")
            total += info.file_size
            if total > max_uncompressed_bytes:
                raise SafeInstallError("Modellarchiv ueberschreitet Groessenlimit")
            if not info.is_dir() and name.lower().endswith(".gguf"):
                models.append(info)
        if len(models) != 1:
            raise SafeInstallError("Genau eine GGUF-Datei erforderlich")
        if models[0].file_size < 16:
            raise SafeInstallError("GGUF-Datei zu klein")
        with z.open(models[0]) as stream:
            if stream.read(4) != b"GGUF":
                raise SafeInstallError("GGUF-Magic fehlt")
        with tempfile.TemporaryDirectory(prefix=".mediahub-gguf-stage-", dir=target.parent) as temp:
            stage = Path(temp)
            for info in members:
                destination = stage.joinpath(*PurePosixPath(info.filename).parts)
                if info.is_dir():
                    destination.mkdir(parents=True, exist_ok=True)
                else:
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    with z.open(info) as source, destination.open("xb") as output:
                        shutil.copyfileobj(source, output)
            if target.exists():
                raise SafeInstallError("Modellziel inzwischen angelegt")
            stage.rename(target)
    model = target.joinpath(*PurePosixPath(models[0].filename).parts)
    return {"ready": True, "model": str(model), "root": str(target),
            "sha256": digest, "model_load_verified": False,
            "requires_runtime_health_check": True}


def inspect_installed_archive(*, archive_path: str, expected_sha256: str,
                              target_dir: str, model: bool = False) -> dict:
    """Read-only byte-for-byte comparison with a trusted, checksum-pinned ZIP.

    No existing files are changed or deleted. Extra files or symlinks prevent
    reuse, as do truncated or modified files.
    """
    import hmac
    archive = Path(archive_path)
    target = Path(target_dir)
    result = {"exists": target.exists() or target.is_symlink(),
              "ready": False, "root": str(target),
              "error": None, "reused": False}
    if not result["exists"]:
        return result
    if target.is_symlink() or not target.is_dir():
        result["error"] = "Ziel ist kein normales Verzeichnis"
        return result
    try:
        checked = preflight_local_archive(
            archive_path=str(archive), expected_sha256=expected_sha256,
            model=model)
        with zipfile.ZipFile(archive) as z:
            expected = set()
            selected = None
            for info in z.infolist():
                if info.is_dir():
                    continue
                relative = PurePosixPath(info.filename)
                expected.add(relative.as_posix().casefold())
                actual = target.joinpath(*relative.parts)
                if actual.is_symlink() or not actual.is_file():
                    raise SafeInstallError("Datei fehlt oder ist Symlink: " + info.filename)
                if actual.stat().st_size != info.file_size:
                    raise SafeInstallError("Dateigroesse weicht ab: " + info.filename)
                with z.open(info) as source, actual.open("rb") as installed:
                    while True:
                        source_bytes = source.read(1024 * 1024)
                        installed_bytes = installed.read(1024 * 1024)
                        if not hmac.compare_digest(source_bytes, installed_bytes):
                            raise SafeInstallError("Dateiinhalt weicht ab: " + info.filename)
                        if not source_bytes:
                            break
                if info.filename == checked["entry"]:
                    selected = actual
            for item in target.rglob("*"):
                if item.is_symlink():
                    raise SafeInstallError("Symlink im Installationsziel")
                if item.is_file() and item.relative_to(target).as_posix().casefold() not in expected:
                    raise SafeInstallError("Zusaetzliche Datei im Installationsziel")
        result.update({"ready": True, "reused": True, "sha256": checked["sha256"],
                       "requires_runtime_health_check": True})
        if model:
            result.update({"model": str(selected), "model_load_verified": False})
        else:
            result.update({"server": str(selected), "backend_verified": False})
    except (OSError, ValueError, zipfile.BadZipFile, SafeInstallError) as exc:
        result["error"] = str(exc)
    return result
