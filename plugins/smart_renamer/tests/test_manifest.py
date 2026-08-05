import json
from pathlib import Path
def test_manifest_version_and_ui():
 root=Path(__file__).resolve().parents[1]; m=json.loads((root/"plugin.json").read_text(encoding="utf-8")); assert m["version"]=="0.4.4"; assert m["ui"]["enabled"] is True
