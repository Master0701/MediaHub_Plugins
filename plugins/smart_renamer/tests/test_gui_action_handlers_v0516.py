from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def test_normal_selection_buttons_use_existing_state_handler():
    text=(ROOT/"plugin.py").read_text(encoding="utf-8")

    assert 'self._set_selected_preview_state("accepted")' in text
    assert 'self._set_selected_preview_state("ignored")' in text
    assert 'self._set_selected_preview_state("review")' in text

    assert "self._accept_selected" not in text
    assert "self._ignore_selected" not in text
    assert "self._review_selected" not in text

    assert "def _set_selected_preview_state(self, state):" in text


def test_phase2_handlers_used_by_new_buttons_exist():
    text=(ROOT/"plugin.py").read_text(encoding="utf-8")

    for method in (
        "_run_ai_review_for_selection",
        "_set_ai_reference_from_selection",
        "_run_ai_batch_for_selection",
        "_run_decision_fusion_for_selection",
        "_run_decision_evidence_for_selection",
    ):
        assert f"def {method}(self" in text
        assert f"self.{method}" in text
