from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def test_batch_detail_shows_metadata_source_diagnostics():
    text=(ROOT/"plugin.py").read_text(encoding="utf-8")
    assert '"Metadaten-Quellen:"' in text
    assert '"metadata.read: "' in text
    assert '"metadata.review: "' in text
    assert '"NFO: "' in text
    assert '"Episodentitel-Felder: keine gefunden"' in text
