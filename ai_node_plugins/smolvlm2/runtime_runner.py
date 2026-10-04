"""Subprocess runner for SmolVLM2."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

PLUGIN_DIR = Path(__file__).resolve().parent
ENGINE_FILE = PLUGIN_DIR / "engine.py"


def load_engine():
    spec = importlib.util.spec_from_file_location(
        "mediahub_runtime_smolvlm2_engine",
        ENGINE_FILE,
    )

    if (
        spec is None
        or spec.loader is None
    ):
        raise RuntimeError(
            "SmolVLM2 engine kann "
            "nicht geladen werden."
        )

    module = importlib.util.module_from_spec(
        spec
    )

    sys.path.insert(
        0,
        str(PLUGIN_DIR),
    )

    spec.loader.exec_module(module)

    return module


def main() -> int:
    try:
        request = json.loads(
            sys.stdin.read()
        )

        engine = load_engine()

        job_type = str(
            request.get("job_type")
            or "vision_analysis"
        )

        if job_type not in {
            "vision_analysis",
            "video_frame_analysis",
        }:
            raise RuntimeError(
                f"Nicht unterstuetzter Runtime-Jobtyp: {job_type}"
            )

        execution = dict(
            request.get("execution")
            or {}
        )

        options = dict(
            request.get("options")
            or {}
        )

        if job_type == "video_frame_analysis":
            result = engine.analyze_video_frames(
                input_path=request["input_path"],
                execution=execution,
                options=options,
            )
        else:
            result = engine.analyze_image(
                input_path=request["input_path"],
                execution=execution,
                options=options,
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
        sys.stdout.write(
            json.dumps(
                {
                    "ok": False,
                    "error": {
                        "type": (
                            type(exc).__name__
                        ),
                        "message": str(exc),
                    },
                },
                ensure_ascii=False,
            )
        )

        return 1


if __name__ == "__main__":
    raise SystemExit(main())

