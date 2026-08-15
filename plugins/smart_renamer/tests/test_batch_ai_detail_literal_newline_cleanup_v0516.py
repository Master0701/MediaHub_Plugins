from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def test_batch_formatter_normalizes_literal_backslash_n():
    text=(ROOT/"plugin.py").read_text(encoding="utf-8")
    start=text.index("def _format_batch_ai_detail")
    end=text.find("\n            def ", start+10)
    block=text[start:end if end!=-1 else None]
    assert 'replace("\\\\n", "\\n")' in block
