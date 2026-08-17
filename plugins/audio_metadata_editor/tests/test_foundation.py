import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_manifest_foundation():
    data = json.loads((ROOT / "plugin.json").read_text(encoding="utf-8"))
    assert data["version"] == "0.0.1"
    assert data["id"] == "mediahub.audio_metadata_editor"
    assert "mediahub.audio_metadata.v1" in data["capabilities"]

def test_no_bundled_binaries():
    forbidden = {".exe", ".dll", ".msi"}
    assert not [
        p for p in ROOT.rglob("*")
        if p.is_file() and p.suffix.lower() in forbidden
    ]

def test_reserved_tools():
    data = json.loads((ROOT / "plugin.json").read_text(encoding="utf-8"))
    ids = {
        item["id"] if isinstance(item, dict) else item
        for item in data["required_tools"] + data["optional_tools"]
    }
    assert {"ffmpeg", "ffprobe", "mediainfo", "chromaprint_fpcalc", "mp3tag"} <= ids
