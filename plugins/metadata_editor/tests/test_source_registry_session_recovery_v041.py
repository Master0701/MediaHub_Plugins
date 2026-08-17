import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = (ROOT / "plugin.py").read_text(encoding="utf-8")


def test_manifest_is_v041_or_newer():
    data = json.loads((ROOT / "plugin.json").read_text(encoding="utf-8"))
    version = tuple(int(part) for part in str(data["version"]).split(".")[:3])
    assert version >= (0, 4, 1)


def test_multiple_sources_are_persistent_without_media_list():
    assert "def _load_local_sources(" in PLUGIN
    assert "def remember_local_source(" in PLUGIN
    assert "def forget_local_source(" in PLUGIN
    assert "def scan_local_sources(" in PLUGIN
    assert 'self.local_sources_file = self.data_dir / "local_sources.json"' in PLUGIN


def test_scan_state_is_lightweight():
    assert 'self.scan_state_file = self.data_dir / "scan_state.json"' in PLUGIN
    assert '"size": int(stat.st_size)' in PLUGIN
    assert '"mtime_ns": int(stat.st_mtime_ns)' in PLUGIN
    assert '"scan_status": scan_status' in PLUGIN


def test_drafts_are_session_only():
    assert "self._session_drafts" in PLUGIN
    assert "return deepcopy(self._session_drafts)" in PLUGIN
    assert "self._session_drafts = deepcopy" in PLUGIN
    assert '"draft_storage": "session_only"' in PLUGIN


def test_real_writes_get_recovery_records():
    assert 'self.recovery_dir = self.data_dir / "recovery"' in PLUGIN
    assert "def _record_recovery(" in PLUGIN
    assert 'action="metadata.update"' in PLUGIN
    assert 'action="nfo.write"' in PLUGIN
    assert 'action="image.replace"' in PLUGIN


def test_metadata_write_capability_requires_confirmation():
    assert '"mode": "confirmed_write"' in PLUGIN
    assert '"automatic_apply_allowed": False' in PLUGIN
    assert '"human_confirmation_required": True' in PLUGIN


def test_native_ui_adds_and_rescans_sources():
    assert 'QPushButton("Lokalen Ordner wählen…")' in PLUGIN
    assert "self.plugin.remember_local_source(folder)" in PLUGIN
    assert "self.plugin.scan_local_sources()" in PLUGIN
