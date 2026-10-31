"""Safe opt-in parallel install of the verified MediaHub CPython runtime.

Never changes existing runtime directories or virtual environments.
"""
from __future__ import annotations

import argparse
import importlib.util
import os
from pathlib import Path
import sys

EXPECTED_SHA256 = "e1f891ef60245148ab41593d7600a5430b6549a450d67329702bd700926902f8"
RUNTIME_DIRNAME = "cpython-3.12.10-x64-astral-20250409"


def load_installer(path: Path):
    spec = importlib.util.spec_from_file_location("mediahub_parallel_runtime_installer", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("portable_installer.py konnte nicht geladen werden")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    parser = argparse.ArgumentParser(description="Installiere gepruefte Python-Runtime parallel ohne bestehende Runtime zu veraendern")
    parser.add_argument("--archive", type=Path, help="Lokales, geprueftes ZIP")
    parser.add_argument("--from-tools", action="store_true", help="Paket aus MediaHub_Tools beziehen")
    parser.add_argument("--confirm", action="store_true", help="Ausdrueckliche Zustimmung zur Installation")
    parser.add_argument("--runtime-base", type=Path, help="Optionales Compute-Runtime-Stammverzeichnis")
    args = parser.parse_args()
    if bool(args.archive) == bool(args.from_tools):
        parser.error("Genau eines von --archive oder --from-tools angeben")
    if not args.confirm:
        parser.error("Installation erfordert --confirm")
    base = args.runtime_base or Path(os.environ.get("MEDIAHUB_COMPUTE_RUNTIME") or Path.home() / ".mediahub" / "compute_node")
    target = base / "private_python" / RUNTIME_DIRNAME
    installer_path = Path(__file__).with_name("portable_installer.py")
    if not installer_path.is_file():
        raise RuntimeError("portable_installer.py fehlt neben diesem Skript")
    if args.from_tools:
        import importlib.util
        plugin_file = Path(__file__).with_name("plugin.py")
        spec = importlib.util.spec_from_file_location("mediahub_python_runtime_cli", plugin_file)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        result = module.install_from_tools_repo(confirmed=True, target=target)
        print("Installationspruefung:", result)
        return 0
    if not args.archive.is_file():
        raise FileNotFoundError(args.archive)
    if target.exists() or target.is_symlink():
        raise FileExistsError(f"Ziel existiert bereits, nichts veraendert: {target}")
    print("Archiv:", args.archive)
    print("Ziel:", target)
    print("Alte Python-Runtime bleibt unveraendert.")
    installer = load_installer(installer_path)
    result = installer.install_verified_runtime(package=args.archive, target=target, expected_sha256=EXPECTED_SHA256)
    print("Installationspruefung:", result)
    if not result.get("ready"):
        raise RuntimeError("Neue Python-Runtime ist nicht einsatzbereit")
    print("ERFOLG: Neue Python-Runtime parallel installiert und geprueft.")
    print("Noch keine Umschaltung des Compute Nodes oder SmolVLM2 vorgenommen.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(f"FEHLER: {exc}", file=sys.stderr)
        sys.exit(1)
