from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_ai_metadata_preview_contains_edition():
    text = (ROOT / "plugin.py").read_text(
        encoding="utf-8"
    )

    assert '"edition": "Fassung / Edition"' in text
    assert (
        '"year",\n'
        '            "edition",\n'
        '            "description",'
        in text
    )


def test_edition_field_is_visible_in_basic_form():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    plugin_text = (
        root / "plugin.py"
    ).read_text(encoding="utf-8")

    assert 'basic_form.addRow(\n            "Fassung / Edition",\n            self.edition_edit,\n        )' in plugin_text


def test_release_label_uses_real_utf8_umlaut():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    plugin_text = (
        root / "plugin.py"
    ).read_text(encoding="utf-8")

    assert "Veröffentlichung / Ausstrahlung" in plugin_text
    assert "Ver?ffentlichung" not in plugin_text
