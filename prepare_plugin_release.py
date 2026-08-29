from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Iterator

ROOT = Path(__file__).resolve().parent
PENDING_NOTES = ROOT / "RELEASE_NOTES_PENDING.md"
RELEASE_NOTES = ROOT / "RELEASE_NOTES.md"
README = ROOT / "README.md"

PLUGIN_GROUPS = (
    ("MediaHub", ROOT / "plugins"),
    ("AI-Node", ROOT / "ai_node_plugins"),
)


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


def iter_plugin_manifests() -> Iterator[tuple[str, Path, dict]]:
    """Liefert alle normalen MediaHub- und AI-Node-Plugin-Manifeste."""
    for group_name, root in PLUGIN_GROUPS:
        if not root.exists():
            continue

        for manifest_path in sorted(root.glob("*/plugin.json")):
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            yield group_name, manifest_path, manifest


def current_plugin_versions() -> dict[str, list[tuple[str, str]]]:
    result: dict[str, list[tuple[str, str]]] = {
        group_name: [] for group_name, _ in PLUGIN_GROUPS
    }

    for group_name, _manifest_path, manifest in iter_plugin_manifests():
        result[group_name].append(
            (str(manifest["name"]), str(manifest["version"]))
        )

    return result


def _version_section(
    title: str,
    versions: list[tuple[str, str]],
) -> str:
    lines = [f"### {title}", ""]

    if versions:
        lines.extend(
            f"- **{name} {version}**" for name, version in versions
        )
    else:
        lines.append("- Keine Plugins gefunden.")

    return "\n".join(lines)


def _compatibility_lines() -> str:
    lines: list[str] = []

    for group_name, _manifest_path, manifest in iter_plugin_manifests():
        name = str(manifest["name"])
        version = str(manifest["version"])

        if group_name == "MediaHub":
            minimum = str(
                manifest.get("minimum_mediahub_version")
                or manifest.get("minimum_mediahub")
                or "nicht angegeben"
            )
            lines.append(
                f"- **{name} {version}** – mindestens MediaHub v{minimum}"
            )
            continue

        targets = manifest.get("targets") or []
        platforms = manifest.get("platforms") or []

        details: list[str] = []
        if targets:
            details.append("Ziele: " + ", ".join(map(str, targets)))
        if platforms:
            details.append("Plattformen: " + ", ".join(map(str, platforms)))

        suffix = "; ".join(details) if details else "Ziel/Plattform nicht angegeben"
        lines.append(f"- **{name} {version}** – {suffix}")

    return "\n".join(lines) or "- Keine Plugin-Manifeste gefunden."


def update_readme(notes: str) -> None:
    body = without_commit_section(notes)
    body = re.sub(
        r"^#\s+(Änderungen|Release Notes)\s*$",
        "",
        body,
        flags=re.MULTILINE | re.IGNORECASE,
    ).strip()

    versions = current_plugin_versions()
    version_sections = "\n\n".join(
        (
            _version_section("MediaHub-Plugins", versions["MediaHub"]),
            _version_section("AI-Node-Plugins", versions["AI-Node"]),
        )
    )
    compatibility = _compatibility_lines()

    text = f"""# MediaHub Plugins

Offizielles Erweiterungs-Repository für die MediaHub-Produktfamilie.

## Aktueller Stand

{version_sections}

{body}

## Kompatibilität

{compatibility}

## Projektaufbau

- `plugins/` – normale MediaHub-Plugins (`.mhplugin`)
- `ai_node_plugins/` – AI-Node-/Compute-Node-Plugins (`.mhaiplugin`)
- `shared/` – gemeinsam genutzte Laufzeiten, APIs und Design-Bausteine
- `catalog/` – Plugin-Store- und Updatekataloge
- `docs/` – Architektur-, Design- und Entwicklungsunterlagen
- `tools/dev/` – dauerhaft nützliche Entwickler- und Diagnosetools
- `release/` – lokal und in GitHub Actions erzeugte Plugin-Pakete

Beide Plugin-Gruppen bleiben technisch getrennt. Jedes Plugin bleibt optional
und kann einzeln installiert, aktualisiert und entfernt werden.

## Plugins bauen

Alle normalen MediaHub- und AI-Node-Plugins sauber neu erstellen:

```powershell
python build_plugins.py all --clean
```

Die fertigen `.mhplugin`- und `.mhaiplugin`-Dateien sowie ihre
`.sha256`-Prüfsummen liegen anschließend unter `release/`.

## Tests

Den vollständigen repositoryweiten Testlauf ausführen:

```powershell
python -m pytest -q
```

## Release vorbereiten

```powershell
python prepare_plugin_release.py
```

Dieser Befehl übernimmt `RELEASE_NOTES_PENDING.md` in die verfolgte Datei
`RELEASE_NOTES.md` und aktualisiert diese README. Die temporäre Pending-Datei
bleibt lokal und wird nicht in Git aufgenommen.

Vor der Veröffentlichung anschließend erneut vollständig prüfen:

```powershell
python -m pytest -q
python build_plugins.py all --clean
```
"""

    README.write_text(text, encoding="utf-8")


def main() -> int:
    notes = read_pending_notes()
    public_notes = without_commit_section(notes)

    RELEASE_NOTES.write_text(public_notes + "\n", encoding="utf-8")
    update_readme(notes)

    print(f"Aktualisiert: {RELEASE_NOTES}")
    print(f"Aktualisiert: {README}")
    print("Danach vollständig prüfen:")
    print("  python -m pytest -q")
    print("  python build_plugins.py all --clean")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
