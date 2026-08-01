from pathlib import Path


PLUGIN_FILE = Path(__file__).resolve().parents[1] / "plugin.py"


def test_semantic_identity_has_output_priority():
    text = PLUGIN_FILE.read_text(encoding="utf-8")

    assert 'preferred_source = "Semantic Identity"' in text
    assert 'preferred_source = "Bestätigter Fingerprint"' in text
    assert 'preferred_source = "Dateiname"' in text
    assert "Primäre Quelle: {preferred_source}" in text


def test_filename_is_only_last_fallback():
    text = PLUGIN_FILE.read_text(encoding="utf-8")

    semantic_pos = text.index('preferred_source = "Semantic Identity"')
    fingerprint_pos = text.index(
        'preferred_source = "Bestätigter Fingerprint"'
    )
    fallback_pos = text.index(
        '"title": identification.get("title_candidate")'
    )

    assert semantic_pos < fingerprint_pos < fallback_pos
