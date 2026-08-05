from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD_SCRIPT = ROOT / "build_plugins.py"


def load_build_module():
    spec = importlib.util.spec_from_file_location(
        "mediahub_build_plugins",
        BUILD_SCRIPT,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("build_plugins.py konnte nicht geladen werden.")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    for required in ("discover_plugins", "update_catalog"):
        if not hasattr(module, required):
            raise RuntimeError(
                f"{required} fehlt in build_plugins.py."
            )
    return module


def main() -> int:
    build = load_build_module()
    plugins = build.discover_plugins()
    if not plugins:
        raise RuntimeError("Keine Plugins gefunden.")

    catalog_path = build.update_catalog(plugins)
    print(f"Verbindlicher Plugin-Store-Katalog erstellt: {catalog_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
