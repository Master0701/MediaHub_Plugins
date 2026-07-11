from __future__ import annotations
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PLUGINS = ROOT / "plugins"
REQUIRED = ("id", "name", "version", "entry", "minimum_mediahub")

def main() -> int:
    errors = []
    found = 0
    for directory in sorted(PLUGINS.iterdir()):
        manifest = directory / "plugin.json"
        if not directory.is_dir() or not manifest.exists():
            continue
        found += 1
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
        except Exception as exc:
            errors.append(f"{manifest}: ungültiges JSON: {exc}")
            continue
        missing = [k for k in REQUIRED if not str(data.get(k, "")).strip()]
        if missing:
            errors.append(f"{manifest}: Pflichtfelder fehlen: {', '.join(missing)}")
        entry = directory / str(data.get("entry", ""))
        if not entry.is_file():
            errors.append(f"{manifest}: Einstieg nicht gefunden: {entry}")
    if found == 0:
        errors.append("Keine Plugin-Quellen mit plugin.json gefunden.")
    if errors:
        print("\\n".join(f"FEHLER: {e}" for e in errors), file=sys.stderr)
        return 1
    print(f"OK: {found} Plugin(s) geprüft.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
