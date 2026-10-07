"""SmolVLM2 inference engine."""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any


class SmolVLM2EngineError(RuntimeError):
    pass


def engine_status() -> dict[str, Any]:
    modules = {
        name: (
            importlib.util.find_spec(name)
            is not None
        )
        for name in (
            "torch",
            "torchvision",
            "transformers",
            "PIL",
            "num2words",
        )
    }

    return {
        "engine": "smolvlm2",
        "modules": modules,
        "available": all(
            modules.values()
        ),
    }


def _resolve_backend(
    requested: str,
) -> tuple[str, Any]:
    import torch

    requested = (
        requested or "auto"
    ).strip().lower()

    if requested == "auto":
        backend = (
            "cuda"
            if torch.cuda.is_available()
            else "cpu"
        )

    elif requested == "cuda":
        if not torch.cuda.is_available():
            raise SmolVLM2EngineError(
                "CUDA wurde angefordert, "
                "ist aber nicht verfuegbar."
            )

        backend = "cuda"

    elif requested == "cpu":
        backend = "cpu"

    else:
        raise SmolVLM2EngineError(
            "Unbekanntes Backend: "
            f"{requested}"
        )

    dtype = (
        torch.float16
        if backend == "cuda"
        else torch.float32
    )

    return backend, dtype


def analyze_image(
    *,
    input_path: str | Path,
    execution: dict[str, Any],
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    path = Path(input_path)

    if not path.is_file():
        raise SmolVLM2EngineError(
            "Bilddatei nicht gefunden: "
            f"{path}"
        )

    options = dict(options or {})

    if options.get("mock", False):
        return {
            "engine": "mock",
            "input": str(path),
            "text": str(
                options.get(
                    "mock_text",
                    "MediaHub SmolVLM2 Mock",
                )
            ),
            "execution": execution,
        }

    status = engine_status()

    if not status["available"]:
        raise SmolVLM2EngineError(
            "SmolVLM2-Runtime ist "
            "nicht vollstaendig installiert."
        )

    import torch
    from model_runtime import MODEL_ID
    from transformers import (
        AutoModelForImageTextToText,
        AutoProcessor,
    )

    requested = str(
        execution.get(
            "backend",
            "auto",
        )
    )

    backend, dtype = _resolve_backend(
        requested
    )

    if backend == "cpu":
        threads = int(
            execution.get(
                "cpu_threads",
                4,
            )
        )

        torch.set_num_threads(
            max(1, threads)
        )

    model_source = str(
        options.get(
            "model_path",
            MODEL_ID,
        )
    )

    local_files_only = bool(
        options.get(
            "local_files_only",
            True,
        )
    )

    processor = (
        AutoProcessor.from_pretrained(
            model_source,
            local_files_only=local_files_only,
        )
    )

    model = (
        AutoModelForImageTextToText
        .from_pretrained(
            model_source,
            dtype=dtype,
            local_files_only=local_files_only,
        )
        .to(backend)
    )

    model.eval()

    prompt = str(
        options.get(
            "prompt",
            (
                "Describe this image precisely. "
                "Read visible text and identify "
                "important objects, people, "
                "logos, titles and scene details."
            ),
        )
    )

    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "path": str(path),
                },
                {
                    "type": "text",
                    "text": prompt,
                },
            ],
        }
    ]

    inputs = processor.apply_chat_template(
        messages,
        add_generation_prompt=True,
        tokenize=True,
        return_dict=True,
        return_tensors="pt",
    )

    inputs = {
        key: (
            value.to(backend)
            if hasattr(value, "to")
            else value
        )
        for key, value in inputs.items()
    }

    max_new_tokens = int(
        options.get(
            "max_new_tokens",
            128,
        )
    )

    with torch.inference_mode():
        generated = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=False,
        )

    input_length = (
        inputs["input_ids"].shape[1]
    )

    generated = generated[
        :,
        input_length:,
    ]

    answer = processor.batch_decode(
        generated,
        skip_special_tokens=True,
    )[0].strip()

    result = {
        "engine": "smolvlm2",
        "model": model_source,
        "backend": backend,
        "text": answer,
        "input": str(path),
        "execution": {
            **execution,
            "backend": backend,
        },
    }

    if backend == "cuda":
        result["gpu"] = (
            torch.cuda.get_device_name(0)
        )

    return result


def _ffmpeg_executable() -> Path:
    """Resolve the platform-appropriate FFmpeg executable."""
    if os.name == "nt":
        ffmpeg = (
            Path(__file__).resolve().parent
            / "tools"
            / "ffmpeg"
            / "ffmpeg.exe"
        )

        if not ffmpeg.is_file():
            raise SmolVLM2EngineError(
                "Eingebettetes FFmpeg wurde nicht gefunden: "
                f"{ffmpeg}"
            )

        return ffmpeg

    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise SmolVLM2EngineError(
            "FFmpeg wurde auf diesem Linux-System nicht gefunden. "
            "Erwartet wird ein verfuegbares 'ffmpeg' im PATH."
        )

    return Path(ffmpeg)


def _ffprobe_executable() -> Path:
    """Resolve the platform-appropriate FFprobe executable."""
    if os.name == "nt":
        ffprobe = (
            Path(__file__).resolve().parent
            / "tools"
            / "ffmpeg"
            / "ffprobe.exe"
        )

        if not ffprobe.is_file():
            raise SmolVLM2EngineError(
                "Eingebettetes FFprobe wurde nicht gefunden: "
                f"{ffprobe}"
            )

        return ffprobe

    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        raise SmolVLM2EngineError(
            "FFprobe wurde auf diesem Linux-System nicht gefunden. "
            "Erwartet wird ein verfuegbares 'ffprobe' im PATH."
        )

    return Path(ffprobe)


def _video_duration(path: Path) -> float:
    """Read video duration using the platform FFprobe."""
    completed = subprocess.run(
        [
            str(_ffprobe_executable()),
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "json",
            str(path),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        timeout=60,
    )

    if completed.returncode != 0:
        raise SmolVLM2EngineError(
            "FFprobe konnte die Videodauer nicht bestimmen: "
            f"{completed.stderr.strip()}"
        )

    try:
        data = json.loads(completed.stdout)
        duration = float(data["format"]["duration"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise SmolVLM2EngineError(
            "Ungueltige FFprobe-Antwort fuer Videodauer."
        ) from exc

    if duration <= 0:
        raise SmolVLM2EngineError(
            f"Ungueltige Videodauer: {duration}"
        )

    return duration


def _extract_video_frame(
    video_path: Path,
    output_path: Path,
    timestamp: float,
) -> None:
    """Extract one frame using the platform FFmpeg."""
    completed = subprocess.run(
        [
            str(_ffmpeg_executable()),
            "-hide_banner",
            "-loglevel",
            "error",
            "-ss",
            f"{timestamp:.3f}",
            "-i",
            str(video_path),
            "-frames:v",
            "1",
            "-q:v",
            "2",
            "-y",
            str(output_path),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        timeout=120,
    )

    if (
        completed.returncode != 0
        or not output_path.is_file()
    ):
        raise SmolVLM2EngineError(
            "FFmpeg konnte keinen Frame extrahieren "
            f"(Position {timestamp:.3f}s): "
            f"{completed.stderr.strip()}"
        )


def analyze_video_frames(
    *,
    input_path: str | Path,
    execution: dict[str, Any],
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Analyze representative frames from a video."""
    path = Path(input_path)

    if not path.is_file():
        raise SmolVLM2EngineError(
            "Videodatei nicht gefunden: "
            f"{path}"
        )

    options = dict(options or {})

    duration = _video_duration(path)

    requested_frames = int(
        options.get("frame_count", 3)
    )

    frame_count = max(
        1,
        min(requested_frames, 32),
    )

    # Avoid the absolute beginning/end because these are
    # frequently black frames, logos or fade transitions.
    positions = [
        duration * (index + 1) / (frame_count + 1)
        for index in range(frame_count)
    ]

    results = []

    with tempfile.TemporaryDirectory(
        prefix="mediahub_smolvlm2_"
    ) as temp_dir:
        temp_root = Path(temp_dir)

        for index, timestamp in enumerate(
            positions,
            start=1,
        ):
            frame_path = (
                temp_root
                / f"frame_{index:03d}.jpg"
            )

            _extract_video_frame(
                path,
                frame_path,
                timestamp,
            )

            frame_options = dict(options)

            frame_options.pop(
                "frame_count",
                None,
            )

            if "prompt" not in frame_options:
                frame_options["prompt"] = (
                    "Analyze this frame from a video precisely. "
                    "Read all visible text. Identify titles, "
                    "logos, people, locations, objects and other "
                    "details that may help identify the movie, "
                    "series or episode."
                )

            analysis = analyze_image(
                input_path=frame_path,
                execution=execution,
                options=frame_options,
            )

            results.append(
                {
                    "index": index,
                    "timestamp": timestamp,
                    "analysis": analysis,
                }
            )

    return {
        "engine": "smolvlm2",
        "type": "video_frame_analysis",
        "input": str(path),
        "duration": duration,
        "frame_count": len(results),
        "frames": results,
    }


