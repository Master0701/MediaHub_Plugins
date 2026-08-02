from __future__ import annotations

import argparse
import hashlib
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


@dataclass(frozen=True)
class Plugin:
    key: str
    name: str
    version: str
    package_name: str
    minimum_mediahub: str
    manifest_path: Path

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
    if capture:
        return result.stdout.strip()
    return ""


def git(*args: str, capture: bool = False) -> str:
    return run("git", *args, capture=capture)


def load_plugins() -> list[Plugin]:
    plugins: list[Plugin] = []
    for manifest_path in sorted(PLUGINS_DIR.glob("*/plugin.json")):
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        for field in ("id", "name", "version"):
            if not data.get(field):
                raise RuntimeError(f"Pflichtfeld {field!r} fehlt in {manifest_path}")
        key = manifest_path.parent.name
        package_name = str(data.get("package_name") or data["name"])
        package_name = re.sub(r"[^A-Za-z0-9ÄÖÜäöüß_-]+", "", package_name.replace(" ", ""))
        plugins.append(
            Plugin(
                key=key,
                name=str(data["name"]),
                version=str(data["version"]),
                package_name=package_name,
                minimum_mediahub=str(
                    data.get("minimum_mediahub_version")
                    or data.get("minimum_mediahub")
                    or "nicht angegeben"
                ),
                manifest_path=manifest_path,
            )
        )
    if not plugins:
        raise RuntimeError("Keine Plugins gefunden.")
    return plugins


def infer_tag(text: str) -> str:
    match = re.search(r"^#\s+MediaHub Plugins\s+v?(\d+\.\d+\.\d+)\b", text, re.MULTILINE)
    if not match:
        raise RuntimeError(
            "Release-Version konnte nicht aus RELEASE_NOTES_PENDING.md gelesen werden. "
            "Erwartet: # MediaHub Plugins v0.5.5"
        )
    return f"v{match.group(1)}"


def normalize_pending(text: str, plugins: list[Plugin], tag: str) -> str:
    text = re.sub(
        r"^#\s+MediaHub Plugins\s+v?\d+\.\d+\.\d+.*$",
        f"# MediaHub Plugins {tag} – vollständiges Release",
        text,
        count=1,
        flags=re.MULTILINE,
    )

    for plugin in plugins:
        placeholder = "{{plugin:" + plugin.key + "}}"
        text = text.replace(placeholder, f"{plugin.name} v{plugin.version}")

        escaped = re.escape(plugin.name)
        pattern = rf"^(##+\s+){escaped}(?:\s+v?\d+\.\d+\.\d+)?\s*$"
        text = re.sub(
            pattern,
            rf"\1{plugin.name} v{plugin.version}",
            text,
            flags=re.MULTILINE | re.IGNORECASE,
        )

    return text.rstrip() + "\n"


def verify_document_versions(text: str, plugins: list[Plugin], label: str) -> None:
    for plugin in plugins:
        expected = f"{plugin.name} v{plugin.version}"
        if expected not in text:
            # README current-state entries intentionally omit the v prefix.
            alternate = f"{plugin.name} {plugin.version}"
            if alternate not in text:
                raise RuntimeError(f"{label}: aktuelle Version fehlt: {expected}")

        wrong = re.findall(
            rf"{re.escape(plugin.name)}\s+v?(\d+\.\d+\.\d+)", text, re.IGNORECASE
        )
        current = {version for version in wrong if version != plugin.version}
        if current:
            raise RuntimeError(
                f"{label}: veraltete Version(en) für {plugin.name}: {sorted(current)}"
            )


def verify_catalog(plugins: list[Plugin]) -> None:
    data = json.loads(CATALOG.read_text(encoding="utf-8"))
    products = data.get("products", [])
    by_id = {str(item.get("id")): item for item in products}
    for plugin in plugins:
        manifest = json.loads(plugin.manifest_path.read_text(encoding="utf-8"))
        plugin_id = str(manifest["id"])
        item = by_id.get(plugin_id)
        if not item:
            raise RuntimeError(f"Katalogeintrag fehlt: {plugin.name} ({plugin_id})")
        if str(item.get("version")) != plugin.version:
            raise RuntimeError(f"Katalogversion falsch für {plugin.name}")
        if str(item.get("package")) != plugin.artifact:
            raise RuntimeError(
                f"Katalogpaket falsch für {plugin.name}: {item.get('package')} != {plugin.artifact}"
            )


def verify_artifacts(plugins: list[Plugin]) -> None:
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

    expected_names = {
        name
        for plugin in plugins
        for name in (plugin.artifact, plugin.artifact + ".sha256")
    }
    stale = [
        path.name
        for path in RELEASE_DIR.glob("MediaHub_*.mhplugin*")
        if path.name not in expected_names
    ]
    if stale:
        raise RuntimeError("Veraltete Build-Dateien gefunden: " + ", ".join(sorted(stale)))


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
    staged = git("diff", "--cached", "--quiet", capture=False) if False else None
    result = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT)
    if result.returncode == 0:
        print("Keine neuen verfolgten Release-Dateien zu committen.")
        return
    if result.returncode != 1:
        raise RuntimeError("Git-Diff konnte nicht geprüft werden.")
    run("git", "commit", "-m", f"Prepare MediaHub Plugins {tag} release")


def main() -> int:
    parser = argparse.ArgumentParser(description="Universeller MediaHub-Plugin-Release-Assistent")
    parser.add_argument("--tag", help="Release-Tag, z. B. v0.5.5")
    parser.add_argument("--skip-tests", action="store_true")
    parser.add_argument("--no-push", action="store_true")
    parser.add_argument("--yes", action="store_true", help="Veröffentlichung ohne Rückfrage bestätigen")
    args = parser.parse_args()

    ensure_clean_before_start()
    plugins = load_plugins()
    pending_text = PENDING.read_text(encoding="utf-8")
    tag = args.tag or infer_tag(pending_text)
    if not re.fullmatch(r"v\d+\.\d+\.\d+(?:[-+][A-Za-z0-9.-]+)?", tag):
        raise RuntimeError(f"Ungültiger Release-Tag: {tag}")

    print(f"Release: {tag}")
    for plugin in plugins:
        print(f"  - {plugin.name} v{plugin.version} -> {plugin.artifact}")

    normalized = normalize_pending(pending_text, plugins, tag)
    PENDING.write_text(normalized, encoding="utf-8")

    run(sys.executable, "prepare_plugin_release.py")
    run(sys.executable, "validate_plugins.py")

    if not args.skip_tests:
        ai_tests = PLUGINS_DIR / "ai_assistant" / "tests"
        if ai_tests.is_dir():
            run(sys.executable, "-m", "pytest", str(ai_tests), "-q")
        run(sys.executable, "-m", "compileall", str(PLUGINS_DIR))

    run(sys.executable, "build_plugins.py", "all", "--clean")

    verify_document_versions(RELEASE_NOTES.read_text(encoding="utf-8"), plugins, "RELEASE_NOTES.md")
    verify_document_versions(README.read_text(encoding="utf-8"), plugins, "README.md")
    verify_catalog(plugins)
    verify_artifacts(plugins)

    commit_generated_files(tag)

    if args.no_push:
        print("Lokaler Release-Lauf abgeschlossen (--no-push).")
        return 0

    if not args.yes:
        answer = input(
            f"\n{tag} wird jetzt auf GitHub neu veröffentlicht. "
            "Vorhandener Tag und Release werden aktualisiert.\n"
            "Zum Fortfahren RELEASE eingeben: "
        ).strip()
        if answer != "RELEASE":
            raise RuntimeError("Veröffentlichung abgebrochen.")

    run("git", "push", "origin", "main")
    # Der Tag wird absichtlich neu auf HEAD gesetzt. Der Workflow aktualisiert
    # danach Titel, Beschreibung und sämtliche Assets des vorhandenen Releases.
    run("git", "tag", "-f", "-a", tag, "-m", f"MediaHub Plugins {tag}")
    run("git", "push", "--force", "origin", f"refs/tags/{tag}")

    head = git("rev-parse", "HEAD", capture=True)
    tag_commit = git("rev-list", "-n", "1", tag, capture=True)
    if head != tag_commit:
        raise RuntimeError(f"Tag zeigt nicht auf HEAD: {tag_commit} != {head}")

    print("\nRelease wurde ausgelöst.")
    print(f"Tag {tag} zeigt auf {head}.")
    print("GitHub Actions aktualisiert Release-Text und Assets vollständig.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, subprocess.CalledProcessError, FileNotFoundError) as exc:
        print(f"\nFEHLER: {exc}", file=sys.stderr)
        raise SystemExit(1)
