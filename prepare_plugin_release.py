from __future__ import annotations

import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PENDING_NOTES = ROOT / "RELEASE_NOTES_PENDING.md"
RELEASE_NOTES = ROOT / "RELEASE_NOTES.md"
README = ROOT / "README.md"
MANIFESTS = ROOT / "plugins"


def read_pending_notes() -> str:
    if not PENDING_NOTES.exists():
        raise FileNotFoundError(
            "RELEASE_NOTES_PENDING.md wurde nicht gefunden."
        )

    text = PENDING_NOTES.read_text(encoding="utf-8").strip()
    if not text:
        raise RuntimeError("RELEASE_NOTES_PENDING.md ist leer.")

    return text


def without_commit_section(text: str) -> str:
    lines = text.splitlines()
    output: list[str] = []

    for line in lines:
        if line.strip().lower() == "## commit-nachricht":
            break
        output.append(line)

    return "\n".join(output).strip()


def current_plugin_versions() -> list[tuple[str, str]]:
    result: list[tuple[str, str]] = []

    for manifest_path in sorted(MANIFESTS.glob("*/plugin.json")):
        import json

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        result.append((str(manifest["name"]), str(manifest["version"])))

    return result


def update_readme(notes: str) -> None:
    body = without_commit_section(notes)
    body = re.sub(
        r"^#\s+(Änderungen|Release Notes)\s*$",
        "",
        body,
        flags=re.MULTILINE | re.IGNORECASE,
    ).strip()

    versions = current_plugin_versions()
    version_lines = "\n".join(
        f"- **{name} {version}**" for name, version in versions
    )

    text = f"""# MediaHub Plugins

Offizielles Erweiterungs-Repository für MediaHub.

## Aktueller Stand

{version_lines}

{body}

## Kompatibilität

Die aktuellen Plugins benötigen mindestens **MediaHub v1.0.5**.

## Projektaufbau

- `plugins/` – getrennte, einzeln installierbare Plugins
- `shared/` – gemeinsam genutzte Laufzeiten, APIs und Design-Bausteine
- `catalog/` – zukünftiger Download- und Updatekatalog
- `docs/` – Architektur-, Design- und Entwicklungsunterlagen
- `release/` – lokal und in GitHub Actions erzeugte Plugin-Pakete

Jedes Plugin bleibt optional und kann einzeln installiert, aktualisiert und entfernt werden.

## Plugins bauen

Alle Plugins sauber neu erstellen:

```powershell
python build_plugins.py all --clean
```

Nur WebRemote erstellen:

```powershell
python build_plugins.py web_remote --clean
```

Die fertigen `.mhplugin`-Dateien und `.sha256`-Prüfsummen liegen anschließend unter `release/`.

## Release vorbereiten

```powershell
python prepare_plugin_release.py
```

Dieser Befehl übernimmt `RELEASE_NOTES_PENDING.md` in die verfolgte Datei
`RELEASE_NOTES.md` und aktualisiert diese README. Die temporäre Pending-Datei
bleibt lokal und wird nicht in Git aufgenommen.
"""

    README.write_text(text, encoding="utf-8")


def main() -> int:
    notes = read_pending_notes()
    public_notes = without_commit_section(notes)

    RELEASE_NOTES.write_text(public_notes + "\n", encoding="utf-8")
    update_readme(notes)

    print(f"Aktualisiert: {RELEASE_NOTES}")
    print(f"Aktualisiert: {README}")
    print(
        "Danach alle Plugins bauen: "
        "python build_plugins.py all --clean"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
