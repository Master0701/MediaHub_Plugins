from __future__ import annotations

import json
import py_compile
import re
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable


class PatchError(RuntimeError):
    pass


@dataclass(frozen=True)
class TextEdit:
    file: str
    label: str
    anchor: str
    insertion: str
    position: str = "after"
    required_count: int = 1


class RepositoryPatch:
    def __init__(
        self,
        repository: Path,
        *,
        plugin_id: str,
        expected_version: str,
        target_version: str,
    ) -> None:
        self.repository = repository.resolve()
        self.plugin_dir = self.repository / "plugins" / plugin_id
        self.manifest_path = self.plugin_dir / "plugin.json"
        self.plugin_path = self.plugin_dir / "plugin.py"
        self.expected_version = expected_version
        self.target_version = target_version
        self.backup_dir: Path | None = None
        self.changed_files: set[Path] = set()

    def validate_repository(self) -> dict:
        if not self.manifest_path.is_file():
            raise PatchError(f"Manifest fehlt: {self.manifest_path}")
        if not self.plugin_path.is_file():
            raise PatchError(f"Plugin-Datei fehlt: {self.plugin_path}")

        manifest = json.loads(
            self.manifest_path.read_text(encoding="utf-8")
        )
        current = str(manifest.get("version") or "")
        if current != self.expected_version:
            raise PatchError(
                f"Patch erwartet v{self.expected_version}, "
                f"gefunden wurde {current!r}."
            )
        return manifest

    def require_markers(
        self,
        relative_file: str,
        markers: Iterable[str],
    ) -> None:
        path = self.repository / relative_file
        text = path.read_text(encoding="utf-8")
        missing = [marker for marker in markers if marker not in text]
        if missing:
            raise PatchError(
                f"{relative_file}: Pflichtmarker fehlen:\n"
                + "\n".join(missing)
            )

    def create_backup(self, paths: Iterable[Path]) -> Path:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup = self.repository / f"_patch_backup_ai_v570_{stamp}"
        backup.mkdir(parents=True, exist_ok=False)
        for path in paths:
            if not path.exists():
                continue
            target = backup / path.relative_to(self.repository)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
        self.backup_dir = backup
        return backup

    def copy_payload(self, payload_root: Path) -> None:
        for source in payload_root.rglob("*"):
            if not source.is_file():
                continue
            target = self.repository / source.relative_to(payload_root)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            self.changed_files.add(target)

    def insert(self, edit: TextEdit) -> None:
        path = self.repository / edit.file
        text = path.read_text(encoding="utf-8")
        count = text.count(edit.anchor)
        if count != edit.required_count:
            raise PatchError(
                f"{edit.label}: erwartet {edit.required_count} "
                f"Treffer, gefunden {count}."
            )

        replacement = (
            edit.insertion + edit.anchor
            if edit.position == "before"
            else edit.anchor + edit.insertion
        )
        text = text.replace(edit.anchor, replacement, 1)
        path.write_text(text, encoding="utf-8")
        self.changed_files.add(path)

    def replace_regex(
        self,
        relative_file: str,
        pattern: str,
        replacement: str,
        label: str,
    ) -> None:
        path = self.repository / relative_file
        text = path.read_text(encoding="utf-8")
        new_text, count = re.subn(
            pattern,
            replacement,
            text,
            count=1,
            flags=re.MULTILINE,
        )
        if count != 1:
            raise PatchError(
                f"{label}: erwartet 1 Treffer, gefunden {count}."
            )
        path.write_text(new_text, encoding="utf-8")
        self.changed_files.add(path)

    def replace_all_checked(
        self,
        relative_file: str,
        old: str,
        new: str,
        *,
        minimum: int,
        label: str,
    ) -> None:
        path = self.repository / relative_file
        text = path.read_text(encoding="utf-8")
        count = text.count(old)
        if count < minimum:
            raise PatchError(
                f"{label}: mindestens {minimum} Treffer erwartet, "
                f"gefunden {count}."
            )
        path.write_text(text.replace(old, new), encoding="utf-8")
        self.changed_files.add(path)

    def update_manifest(self, manifest: dict, capabilities: list[str]) -> None:
        manifest["version"] = self.target_version
        existing = list(manifest.get("capabilities") or [])
        for capability in capabilities:
            if capability not in existing:
                existing.append(capability)
        manifest["capabilities"] = sorted(existing)
        self.manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        self.changed_files.add(self.manifest_path)

    def validate_python(self) -> None:
        python_files = [
            path
            for path in self.changed_files
            if path.suffix == ".py"
        ]
        for path in python_files:
            try:
                py_compile.compile(str(path), doraise=True)
            except py_compile.PyCompileError as exc:
                raise PatchError(
                    f"Syntaxprüfung fehlgeschlagen: {path}\n{exc}"
                ) from exc

    def rollback(self) -> None:
        if self.backup_dir is None:
            return
        for source in self.backup_dir.rglob("*"):
            if not source.is_file():
                continue
            target = self.repository / source.relative_to(self.backup_dir)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
