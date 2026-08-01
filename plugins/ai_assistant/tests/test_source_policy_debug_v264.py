from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCANNER = ROOT / "services" / "source_scanner.py"
PLUGIN = ROOT / "plugin.py"


def test_policy_engine_has_distinct_states():
    text = SCANNER.read_text(encoding="utf-8")
    for state in (
        "robots_missing",
        "network_error",
        "timeout",
        "blocked",
        "allowed",
    ):
        assert f'"{state}"' in text


def test_policy_engine_reports_diagnostics():
    text = SCANNER.read_text(encoding="utf-8")
    assert '"http_status"' in text
    assert '"content_type"' in text
    assert '"user_agent"' in text
    assert '"robots_text_preview"' in text


def test_policy_diagnosis_gui_exists():
    text = PLUGIN.read_text(encoding="utf-8")
    assert 'QPushButton("Policy-Diagnose")' in text
    assert "def diagnose_source_policy_gui(self):" in text
    assert "def diagnose_source_policy(" in text
