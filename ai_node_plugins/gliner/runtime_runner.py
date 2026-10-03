"""Subprocess runner for the isolated GLiNER runtime."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

PLUGIN_DIR = Path(__file__).resolve().parent
ENGINE_FILE = PLUGIN_DIR / "engine.py"


def _activate_packages(
    packages_path: str | Path,
) -> Path:
    """Activate the plugin-private package directory."""

    packages = Path(packages_path).resolve()

    if not packages.is_dir():
        raise RuntimeError(
            "GLiNER-Paketverzeichnis nicht gefunden: "
            f"{packages}"
        )

    packages_text = str(packages)

    if packages_text not in sys.path:
        sys.path.insert(0, packages_text)

    return packages


def load_engine():
    spec = importlib.util.spec_from_file_location(
        "mediahub_runtime_gliner_engine",
        ENGINE_FILE,
    )

    if spec is None or spec.loader is None:
        raise RuntimeError(
            "GLiNER-Engine kann nicht geladen werden."
        )

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    try:
        raw = sys.stdin.read()
        request = json.loads(raw)

        packages_path = request.get(
            "packages_path"
        )

        if not packages_path:
            raise RuntimeError(
                "GLiNER packages_path fehlt."
            )

        _activate_packages(packages_path)

        engine = load_engine()

        result = engine.analyze_text(
            text=request["text"],
            execution=dict(
                request.get("execution")
                or {}
            ),
            options=dict(
                request.get("options")
                or {}
            ),
        )

        response = {
            "ok": True,
            "result": result,
        }

        sys.stdout.write(
            json.dumps(
                response,
                ensure_ascii=False,
            )
        )

        return 0

    except Exception as exc:  # noqa: BLE001
        response = {
            "ok": False,
            "error": {
                "type": type(exc).__name__,
                "message": str(exc),
            },
        }

        sys.stdout.write(
            json.dumps(
                response,
                ensure_ascii=False,
            )
        )

        return 1


if __name__ == "__main__":
    raise SystemExit(main())
