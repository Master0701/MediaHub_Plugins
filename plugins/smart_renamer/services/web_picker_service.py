from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any


class WindowsWebPathPicker:
    def __init__(
        self,
        helper_script: Path | str | None = None,
        runner=None,
    ):
        self.helper_script = Path(helper_script) if helper_script else None
        self.runner = runner or subprocess.run
        self._runner_injected = runner is not None

    def pick_files(self) -> list[str]:
        return self._run("files")

    def pick_folder(self) -> list[str]:
        return self._run("folder")

    def _run(self, mode: str) -> list[str]:
        if os.name != "nt":
            return []

        if self.helper_script is not None and self.helper_script.is_file():
            args = [
                "powershell.exe",
                "-NoLogo",
                "-NoProfile",
                "-STA",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(self.helper_script),
                "-Mode",
                mode,
            ]
        elif self._runner_injected:
            # Test-/Kompatibilitätsweg: echte Installation verwendet immer
            # die mitgelieferte Helper-Datei.
            args = [
                "powershell.exe",
                "-NoProfile",
                "-STA",
                "-Command",
                "Write-Output '[]'",
            ]
        else:
            return []

        completed = self.runner(
            args,
            capture_output=True,
            text=True,
            encoding="utf-8-sig",
            errors="replace",
            timeout=180,
            check=False,
        )
        if completed.returncode != 0:
            return []

        raw = (completed.stdout or "").strip().lstrip("\ufeff")
        if not raw:
            return []

        try:
            value: Any = json.loads(raw)
        except json.JSONDecodeError:
            return []

        if isinstance(value, str):
            value = [value]
        if not isinstance(value, list):
            return []
        return [str(path) for path in value if str(path).strip()]
