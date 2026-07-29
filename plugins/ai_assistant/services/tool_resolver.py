from __future__ import annotations

import os
from pathlib import Path


class ToolResolver:
    """Findet zentrale MediaHub-Werkzeuge und bleibt eigenständig nutzbar."""

    TOOL_NAMES = {
        "ffprobe": ("ffprobe.exe", "ffprobe"),
        "ffmpeg": ("ffmpeg.exe", "ffmpeg"),
        "mediainfo": ("mediainfo.exe", "MediaInfo.exe", "mediainfo"),
        "tesseract": ("tesseract.exe", "tesseract"),
        "mkvmerge": ("mkvmerge.exe", "mkvmerge"),
        "mkvpropedit": ("mkvpropedit.exe", "mkvpropedit"),
    }

    def __init__(
        self,
        mediahub_base: Path,
        plugin_path: Path | None = None,
    ):
        self.mediahub_base = Path(mediahub_base).resolve()
        self.plugin_path = (
            Path(plugin_path).resolve()
            if plugin_path is not None
            else None
        )
        self.search_roots = self._build_search_roots()

    def _build_search_roots(self) -> list[Path]:
        candidates: list[Path] = []

        env_root = os.environ.get("MEDIAHUB_TOOLS_DIR")
        if env_root:
            candidates.append(Path(env_root))

        anchors = [
            self.mediahub_base,
            self.plugin_path,
            Path.cwd(),
        ]

        for anchor in anchors:
            if anchor is None:
                continue
            anchor = Path(anchor).resolve()

            # Direkte lokale und zentrale Toolordner.
            candidates.extend([
                anchor / "tools",
                anchor / "MediaHub_Tools",
            ])

            # Alle Eltern prüfen. Dadurch wird aus
            # MediaHub-Plugins/plugins/ai_assistant auch
            # D:/eigenes program/MediaHub/tools erreicht.
            for parent in (anchor, *anchor.parents):
                candidates.extend([
                    parent / "tools",
                    parent / "MediaHub_Tools",
                    parent / "MediaHub" / "tools",
                    parent / "MediaHub" / "MediaHub_Tools",
                ])

                # Geschwisterordner eines Projektverzeichnisses.
                candidates.extend([
                    parent.parent / "MediaHub" / "tools",
                    parent.parent / "MediaHub_Tools",
                ])

        result: list[Path] = []
        seen: set[str] = set()
        for candidate in candidates:
            try:
                key = str(candidate.resolve()).casefold()
            except OSError:
                key = str(candidate.absolute()).casefold()
            if key in seen:
                continue
            seen.add(key)
            result.append(candidate)
        return result

    @classmethod
    def _names(cls, tool_id: str) -> tuple[str, ...]:
        return cls.TOOL_NAMES.get(
            str(tool_id).strip().lower(),
            (f"{tool_id}.exe", str(tool_id)),
        )

    def find(self, tool_id: str) -> Path | None:
        names = self._names(tool_id)

        for root in self.search_roots:
            if not root.is_dir():
                continue

            for name in names:
                direct = root / name
                if direct.is_file():
                    return direct.resolve()

            # Die zentralen Pakete enthalten Werkzeuge häufig in
            # Unterordnern wie ffmpeg/bin oder mediainfo/.
            for name in names:
                try:
                    match = next(
                        (
                            item
                            for item in root.rglob(name)
                            if item.is_file()
                        ),
                        None,
                    )
                except OSError:
                    match = None
                if match is not None:
                    return match.resolve()

        # Eigenständiger Betrieb: zuletzt das normale System-PATH prüfen.
        for directory in os.environ.get("PATH", "").split(os.pathsep):
            if not directory:
                continue
            base = Path(directory)
            for name in names:
                path = base / name
                if path.is_file():
                    return path.resolve()

        return None

    def status(self) -> dict:
        return {
            "search_roots": [str(path) for path in self.search_roots],
            "ffprobe": self._entry("ffprobe", True),
            "ffmpeg": self._entry("ffmpeg", True),
            "mediainfo": self._entry("mediainfo", True),
            "tesseract": self._entry("tesseract", False),
            "mkvmerge": self._entry("mkvmerge", False),
            "mkvpropedit": self._entry("mkvpropedit", False),
        }

    def _entry(self, tool_id: str, required: bool) -> dict:
        path = self.find(tool_id)
        return {
            "id": tool_id,
            "required": required,
            "installed": path is not None,
            "path": str(path) if path else None,
        }
