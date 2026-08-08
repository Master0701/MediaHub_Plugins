from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_plan_ui_buttons_are_present_and_initially_safe():
    html = (ROOT / "index.html").read_text(encoding="utf-8")

    assert 'id="plan" disabled' in html
    assert 'id="prepare" disabled' in html
    assert "Rename-Plan" in html
    assert "Rollback vorbereiten" in html


def test_plan_ui_shows_required_security_information():
    html = (ROOT / "index.html").read_text(encoding="utf-8")

    for marker in (
        'id="planState"',
        'id="planConfirm"',
        'id="planExecution"',
        'id="planId"',
        'id="planHash"',
        'id="planMessage"',
    ):
        assert marker in html


def test_ui_calls_plan_api_but_not_execute_api():
    html = (ROOT / "index.html").read_text(encoding="utf-8")

    assert "'/smart-renamer/api/plan'" in html
    assert "'/smart-renamer/api/transaction/prepare'" in html
    assert "/smart-renamer/api/execute" not in html


def test_ui_keeps_execution_visibly_locked():
    html = (ROOT / "index.html").read_text(encoding="utf-8")

    assert "Ausführung gesperrt" in html
    assert "Medien wurden NICHT verändert" in html
    assert "wird aber noch NICHT ausgeführt" in html


def test_prepare_button_only_activates_for_executable_plan():
    html = (ROOT / "index.html").read_text(encoding="utf-8")

    assert "$('prepare').disabled=!lastPlan.executable" in html
    assert "if(!lastPlan||!lastPlan.executable)return" in html


def test_plan_css_supports_mobile_layout():
    css = (
        ROOT / "assets" / "css" / "mediahub.css"
    ).read_text(encoding="utf-8")

    assert ".plan-panel" in css
    assert ".plan-meta" in css
    assert "@media(max-width:800px)" in css
