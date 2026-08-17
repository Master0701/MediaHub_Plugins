import json
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def test_native_poster_preview_ui_is_present():
    text=(ROOT/"plugin.py").read_text(encoding="utf-8")
    assert (
        '"Poster-Vorschau"' in text
        or '"Poster  (Vorschau)"' in text
    )
    assert "self.poster_preview = QLabel(" in text
    assert "self.poster_preview.setMinimumSize(" in text
    assert "self.poster_preview.setMaximumSize(" in text
    assert "def _update_poster_preview(" in text

    match = re.search(
        r"self\.poster_preview\.setMinimumSize\((\d+),\s*(\d+)\)",
        text,
    )
    assert match
    width, height = map(int, match.groups())
    assert width >= 180
    assert height >= 260

def test_poster_lookup_uses_existing_image_names():
    text=(ROOT/"plugin.py").read_text(encoding="utf-8")
    assert "def _poster_path(" in text
    assert 'self.IMAGE_NAMES.get("poster"' in text
    assert '"poster_path"' in text
    assert '"cover_path"' in text

def test_replace_poster_refreshes_preview():
    text=(ROOT/"plugin.py").read_text(encoding="utf-8")
    start=text.index("    def _replace_poster(self):")
    end=text.find("\n    def ",start+10)
    block=text[start:end if end!=-1 else None]
    assert "self._update_poster_preview(self._current)" in block

def test_manifest_version_supports_poster_preview():
    data=json.loads((ROOT/"plugin.json").read_text(encoding="utf-8"))
    version=tuple(int(part) for part in str(data["version"]).split(".")[:3])
    assert version >= (0, 3, 8)
