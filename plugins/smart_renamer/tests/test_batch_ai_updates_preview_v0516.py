from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def test_batch_ai_result_updates_visible_preview_only():
    text=(ROOT/"plugin.py").read_text(encoding="utf-8")
    assert 'ai_suggested=str(result.get("suggested_name") or "").strip()' in text
    assert 'meta["proposed_name"]=ai_suggested' in text
    assert 'proposal_item=self.table.item(row,2)' in text
    assert 'proposal_item.setText(ai_suggested)' in text
    assert "nur Vorschau, noch nicht ausgeführt" in text


def test_batch_preview_update_does_not_execute_files():
    text=(ROOT/"plugin.py").read_text(encoding="utf-8")
    start=text.index("def _run_ai_batch_for_selection")
    end=text.index("def _run_ai_review_for_selection",start)
    block=text[start:end]
    assert "execute_plan" not in block
    assert "rename(" not in block
    assert "metadata_write" not in block
