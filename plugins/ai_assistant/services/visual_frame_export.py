from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path
from typing import Any


def export_approved_frames(
    file_path: str | Path,
    ffmpeg: str | Path,
    selected_frames: list[dict[str, Any]],
    *,
    user_approved: bool,
    maximum_frames: int = 4,
) -> list[dict[str, Any]]:
    """Exportiert nur nach Freigabe kleine JPEG-Einzelbilder.

    Die Bilder werden in einem temporären Ordner erzeugt und müssen vom
    Aufrufer nach der Provider-Anfrage gelöscht werden.
    """
    if not user_approved:
        return []

    file_path = Path(file_path)
    ffmpeg = Path(ffmpeg)
    result: list[dict[str, Any]] = []

    for index, item in enumerate(
        list(selected_frames or [])[: max(1, min(maximum_frames, 8))]
    ):
        second = float(item.get("second") or 0.0)
        temp = tempfile.NamedTemporaryFile(
            prefix="mediahub_visual_",
            suffix=".jpg",
            delete=False,
        )
        temp_path = Path(temp.name)
        temp.close()

        command = [
            str(ffmpeg),
            "-hide_banner",
            "-loglevel",
            "error",
            "-nostdin",
            "-ss",
            str(max(0.0, second)),
            "-i",
            str(file_path),
            "-frames:v",
            "1",
            "-vf",
            "scale='min(640,iw)':-2",
            "-q:v",
            "4",
            "-y",
            str(temp_path),
        ]

        process = subprocess.run(
            command,
            capture_output=True,
            timeout=30,
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )

        if process.returncode == 0 and temp_path.is_file():
            result.append(
                {
                    "second": round(second, 2),
                    "path": str(temp_path),
                    "size": temp_path.stat().st_size,
                    "temporary": True,
                }
            )
        else:
            temp_path.unlink(missing_ok=True)

    return result
