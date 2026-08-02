from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PLUGINS_DIR = ROOT / "plugins"
PENDING = ROOT / "RELEASE_NOTES_PENDING.md"
RELEASE_NOTES = ROOT / "RELEASE_NOTES.md"
README = ROOT / "README.md"
CATALOG = ROOT / "catalog" / "plugins.json"
RELEASE_DIR = ROOT / "release"
BUILD_SCRIPT = ROOT / "build_plugins.py"


@dataclass(frozen=True)
class Plugin:
    key: str
    plugin_id: str
    name: str
    version: str
    package_name: str
    minimum_mediahub: str
    description: str
    manifest_path: Path

    @property
    def publishable(self) -> bool:
        return self.version != "0.0.0"

    @property
    def artifact(self) -> str:
        return f"MediaHub_{self.package_name}_v{self.version}.mhplugin"


def run(*args: str, capture: bool = False) -> str:
    print("+", " ".join(args))
    result = subprocess.run(
        args,
        cwd=ROOT,
        check=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=capture,
    )
    return result.stdout.strip() if capture else ""


def git(*args: str, capture: bool = False) -> str:
    return run("git", *args, capture=capture)


def load_build_helpers():
    spec = importlib.util.spec_from_file_location("mediahub_build_plugins", BUILD_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("build_plugins.py konnte nicht geladen werden.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not hasattr(module, "safe_package_name"):
        raise RuntimeError("safe_package_name fehlt in build_plugins.py.")
    return module


def load_plugins() -> list[Plugin]:
    build = load_build_helpers()
    plugins: list[Plugin] = []

    for manifest_path in sorted(PLUGINS_DIR.glob("*/plugin.json")):
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        for field in ("id", "name", "version"):
            if not data.get(field):
                raise RuntimeError(f"Pflichtfeld {field!r} fehlt in {manifest_path}")

        key = manifest_path.parent.name
        package_name = str(build.safe_package_name(data, key))
        plugins.append(
            Plugin(
                key=key,
                plugin_id=str(data["id"]),
                name=str(data["name"]),
                version=str(data["version"]),
                package_name=package_name,
                minimum_mediahub=str(
                    data.get("minimum_mediahub_version")
                    or data.get("minimum_mediahub")
                    or "nicht angegeben"
                ),
                description=str(data.get("description") or "").strip(),
                manifest_path=manifest_path,
            )
        )

    if not plugins:
        raise RuntimeError("Keine Plugins gefunden.")
    return plugins


def infer_tag(text: str) -> str:
    match = re.search(
        r"^#\s+MediaHub Plugins\s+v?(\d+\.\d+\.\d+)\b",
        text,
        re.MULTILINE,
    )
    if not match:
        raise RuntimeError(
            "Release-Version konnte nicht aus RELEASE_NOTES_PENDING.md gelesen werden. "
            "Erwartet: # MediaHub Plugins v0.5.5"
        )
    return f"v{match.group(1)}"


def extract_plugin_bodies(text: str, plugins: list[Plugin]) -> dict[str, str]:
    bodies: dict[str, str] = {}
    heading_re = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
    matches = list(heading_re.finditer(text))

    for index, match in enumerate(matches):
        heading = match.group(1).strip()
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = text[start:end].strip()

        for plugin in plugins:
            if re.match(
                rf"^{re.escape(plugin.name)}(?:\s+v?\d+\.\d+\.\d+)?$",
                heading,
                re.IGNORECASE,
            ):
                bodies[plugin.key] = body
                break

    return bodies


def generic_body(plugin: Plugin) -> str:
    if plugin.description:
        return f"- {plugin.description}"
    return "- Aktueller Plugin-Stand wurde aus dem Manifest übernommen."


def build_release_notes(source: str, plugins: list[Plugin], tag: str) -> str:
    bodies = extract_plugin_bodies(source, plugins)
    lines = [f"# MediaHub Plugins {tag} – vollständiges Release", ""]

    for plugin in plugins:
        if not plugin.publishable:
            continue
        lines.append(f"## {plugin.name} v{plugin.version}")
        lines.append("")
        lines.append(bodies.get(plugin.key) or generic_body(plugin))
        lines.append("")

    placeholders = [plugin for plugin in plugins if not plugin.publishable]
    if placeholders:
        lines.append("## Gemeinsamer Release-Stand")
        lines.append("")
        lines.append("- Alle veröffentlichten Plugins wurden aus den aktuellen Manifesten vollständig neu gebaut.")
        lines.append("- Für jedes veröffentlichte Plugin stehen eine `.mhplugin`-Datei und eine `.sha256`-Prüfsumme bereit.")
        lines.append("- Der Plugin-Katalog wurde aus den aktuellen Manifesten erzeugt.")
        lines.append("- Geplante Plugins mit Version 0.0.0 bleiben im Katalog sichtbar, werden aber nicht als veröffentlichte Release-Pakete geprüft.")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def build_readme(notes: str, plugins: list[Plugin]) -> str:
    version_lines = "\n".join(
        f"- **{plugin.name} {plugin.version}**" for plugin in plugins
    )
    compatibility = "\n".join(
        f"- **{plugin.name} {plugin.version}** – mindestens MediaHub v{plugin.minimum_mediahub}"
        for plugin in plugins
    )

    return f"""# MediaHub Plugins

Offizielles Erweiterungs-Repository für MediaHub.

## Aktueller Stand

{version_lines}

{notes.strip()}

## Kompatibilität

{compatibility}

## Projektaufbau

- `plugins/` – getrennte, einzeln installierbare Plugins
- `shared/` – gemeinsam genutzte Laufzeiten, APIs und Design-Bausteine
- `catalog/` – Plugin-Store- und Updatekataloge
- `docs/` – Architektur-, Design- und Entwicklungsunterlagen
- `tools/dev/` – dauerhaft nützliche Entwickler- und Diagnosetools
- `release/` – lokal und in GitHub Actions erzeugte Plugin-Pakete

Jedes Plugin bleibt optional und kann einzeln installiert, aktualisiert und entfernt werden.

## Release ausführen

Lokaler Prüflauf ohne Veröffentlichung:

```powershell
release_plugins.cmd -Tag v0.5.5 -NoPush
```

Vollständiges Release:

```powershell
release_plugins.cmd -Tag v0.5.5
```

Alle Versions- und Paketnamen werden automatisch aus den jeweiligen
`plugins/*/plugin.json` übernommen.
"""


def verify_document_versions(text: str, plugins: list[Plugin], label: str) -> None:
    for plugin in plugins:
        expected = f"{plugin.name} v{plugin.version}"
        alternate = f"{plugin.name} {plugin.version}"

        if plugin.publishable:
            if expected not in text and alternate not in text:
                raise RuntimeError(f"{label}: aktuelle Version fehlt: {expected}")
        elif label == "README.md":
            if alternate not in text:
                raise RuntimeError(f"{label}: Platzhalterversion fehlt: {alternate}")

        found = re.findall(
            rf"{re.escape(plugin.name)}\s+v?(\d+\.\d+\.\d+)",
            text,
            re.IGNORECASE,
        )
        wrong = {version for version in found if version != plugin.version}
        if wrong:
            raise RuntimeError(
                f"{label}: veraltete Version(en) für {plugin.name}: {sorted(wrong)}"
            )


def verify_catalog(plugins: list[Plugin]) -> None:
    data = json.loads(CATALOG.read_text(encoding="utf-8"))
    products = data.get("products", [])
    by_id = {str(item.get("id")): item for item in products}

    for plugin in plugins:
        item = by_id.get(plugin.plugin_id)
        if not item:
            raise RuntimeError(f"Katalogeintrag fehlt: {plugin.name} ({plugin.plugin_id})")
        if str(item.get("version")) != plugin.version:
            raise RuntimeError(f"Katalogversion falsch für {plugin.name}")
        if str(item.get("package")) != plugin.artifact:
            raise RuntimeError(
                f"Katalogpaket falsch für {plugin.name}: "
                f"{item.get('package')} != {plugin.artifact}"
            )


def verify_artifacts(plugins: list[Plugin]) -> None:
    expected_names: set[str] = set()

    for plugin in plugins:
        artifact = RELEASE_DIR / plugin.artifact
        checksum_file = artifact.with_name(artifact.name + ".sha256")

        if not artifact.is_file():
            raise RuntimeError(f"Build-Datei fehlt: {artifact}")
        if not checksum_file.is_file():
            raise RuntimeError(f"Prüfsumme fehlt: {checksum_file}")

        expected = hashlib.sha256(artifact.read_bytes()).hexdigest()
        recorded = checksum_file.read_text(encoding="utf-8").strip().split()[0]
        if expected.lower() != recorded.lower():
            raise RuntimeError(f"SHA256 stimmt nicht: {artifact.name}")

        expected_names.add(plugin.artifact)
        expected_names.add(plugin.artifact + ".sha256")

    stale = [
        path.name
        for path in RELEASE_DIR.glob("MediaHub_*.mhplugin*")
        if path.name not in expected_names
    ]
    if stale:
        raise RuntimeError(
            "Veraltete Build-Dateien gefunden: " + ", ".join(sorted(stale))
        )


def ensure_clean_before_start() -> None:
    status = git("status", "--porcelain", capture=True)
    allowed = {
        "RELEASE_NOTES_PENDING.md",
        "README.md",
        "RELEASE_NOTES.md",
        "catalog/plugins.json",
    }

    unexpected: list[str] = []
    for line in status.splitlines():
        path = line[3:].strip().strip('"')
        if path and path not in allowed:
            unexpected.append(line)

    if unexpected:
        raise RuntimeError(
            "Unerwartete Änderungen im Arbeitsbaum. Erst prüfen oder committen:\n"
            + "\n".join(unexpected)
        )


def commit_generated_files(tag: str) -> None:
    tracked = ["README.md", "RELEASE_NOTES.md", "catalog/plugins.json"]
    run("git", "add", *tracked)
    result = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT)

    if result.returncode == 0:
        print("Keine neuen verfolgten Release-Dateien zu committen.")
        return
    if result.returncode != 1:
        raise RuntimeError("Git-Diff konnte nicht geprüft werden.")

    run("git", "commit", "-m", f"Prepare MediaHub Plugins {tag} release")


def update_tag(tag: str) -> None:
    existing = git("tag", "--list", tag, capture=True)
    if existing:
        run("git", "tag", "-d", tag)
        run("git", "push", "origin", f":refs/tags/{tag}")
    run("git", "tag", "-a", tag, "-m", f"MediaHub Plugins {tag}")
    run("git", "push", "origin", tag)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Universeller MediaHub-Plugin-Release-Assistent v3"
    )
    parser.add_argument("--tag", help="Release-Tag, z. B. v0.5.5")
    parser.add_argument("--skip-tests", action="store_true")
    parser.add_argument("--no-push", action="store_true")
    parser.add_argument("--yes", action="store_true")
    args = parser.parse_args()

    ensure_clean_before_start()
    plugins = load_plugins()

    pending_text = PENDING.read_text(encoding="utf-8")
    tag = args.tag or infer_tag(pending_text)
    if not tag.startswith("v"):
        tag = "v" + tag

    notes = build_release_notes(pending_text, plugins, tag)
    PENDING.write_text(notes, encoding="utf-8")
    RELEASE_NOTES.write_text(notes, encoding="utf-8")
    README.write_text(build_readme(notes, plugins), encoding="utf-8")

    print(f"Release: {tag}")
    for plugin in plugins:
        state = "veröffentlicht" if plugin.publishable else "Platzhalter"
        print(f"  - {plugin.name} v{plugin.version} [{state}] -> {plugin.artifact}")

    run(sys.executable, "validate_plugins.py")

    if not args.skip_tests:
        ai_tests = PLUGINS_DIR / "ai_assistant" / "tests"
        if ai_tests.is_dir():
            run(sys.executable, "-m", "pytest", str(ai_tests), "-q")
        run(sys.executable, "-m", "compileall", str(PLUGINS_DIR))

    run(sys.executable, "build_plugins.py", "all", "--clean")

    verify_document_versions(
        RELEASE_NOTES.read_text(encoding="utf-8"),
        plugins,
        "RELEASE_NOTES.md",
    )
    verify_document_versions(
        README.read_text(encoding="utf-8"),
        plugins,
        "README.md",
    )
    verify_catalog(plugins)
    verify_artifacts(plugins)

    commit_generated_files(tag)

    if args.no_push:
        print("Lokaler Release-Lauf abgeschlossen (--no-push).")
        return 0

    if not args.yes:
        answer = input(
            f"Release {tag} jetzt vollständig neu veröffentlichen? "
            "Zum Bestätigen RELEASE eingeben: "
        )
        if answer.strip() != "RELEASE":
            raise RuntimeError("Veröffentlichung wurde nicht bestätigt.")

    run("git", "push", "origin", "main")
    update_tag(tag)

    head = git("rev-parse", "HEAD", capture=True)
    tagged = git("rev-list", "-n", "1", tag, capture=True)
    if head != tagged:
        raise RuntimeError(f"Tag {tag} zeigt nicht auf HEAD.")

    print(f"Release {tag} wurde erfolgreich angestoßen.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as exc:
        print(f"\nFEHLER: Befehl fehlgeschlagen ({exc.returncode}).", file=sys.stderr)
        raise SystemExit(exc.returncode)
    except Exception as exc:
        print(f"\nFEHLER: {exc}", file=sys.stderr)
        raise SystemExit(1)
