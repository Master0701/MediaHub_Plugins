import json
from pathlib import Path

def test_manifest_version_and_ui():
    root = Path(__file__).resolve().parents[1]
    manifest = json.loads((root / "plugin.json").read_text(encoding="utf-8"))
    assert manifest["version"] == "0.4.5"
    assert manifest["ui"]["enabled"] is True
