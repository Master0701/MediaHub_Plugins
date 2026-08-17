import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_source_contains_local_folder_ui_and_scanner():
    text=(ROOT/"plugin.py").read_text(encoding="utf-8")
    assert (
        'QPushButton("Ordner laden…")' in text
        or 'QPushButton("Lokalen Ordner wählen…")' in text
    )
    assert '"Lokaler Ordner"' in text
    assert "def scan_local_folder(" in text
    assert "def _choose_local_folder(" in text
    assert "getExistingDirectory" in text


def test_manifest_version_supports_local_folder_browser():
    data=json.loads((ROOT/"plugin.json").read_text(encoding="utf-8"))
    version=tuple(int(part) for part in str(data["version"]).split(".")[:3])
    assert version >= (0, 3, 7)


def test_scanner_uses_shared_supported_extensions():
    text = (ROOT / "plugin.py").read_text(encoding="utf-8")

    assert "SUPPORTED_EXTENSIONS" in text
    assert "LOCAL_MEDIA_EXTENSIONS" in text
    assert "set(SUPPORTED_EXTENSIONS)" in text


def test_shared_core_contains_common_video_and_audio_extensions():
    shared_root = ROOT.parents[1] / "shared"
    formats = (
        shared_root
        / "mediahub_metadata_core"
        / "formats.py"
    ).read_text(encoding="utf-8")

    for ext in (".mkv", ".mp4", ".avi", ".m4b", ".mp3"):
        assert f'"{ext}"' in formats


def test_library_and_local_items_are_kept_separately_before_merge():
    text=(ROOT/"plugin.py").read_text(encoding="utf-8")
    assert "self._library_items = []" in text
    assert "self._local_items = []" in text
    assert "def _rebuild_items(self):" in text
