from pathlib import Path


def test_ai_architecture_validator_integrated_v701():
    root = Path(__file__).resolve().parents[1]
    text = (root / "plugin.py").read_text(encoding="utf-8")

    assert (
        "from services.ai_architecture_validator "
        "import AIArchitectureValidator"
        in text
    )
    assert (
        "self.ai_architecture_validator = "
        "AIArchitectureValidator()"
        in text
    )
    assert (
        "architecture_validation = "
        "self.ai_architecture_validator.build("
        in text
    )
    assert (
        '"architecture_validation": architecture_validation'
        in text
    )
    assert (
        'context.document["architecture_validation"] = '
        "architecture_validation"
        in text
    )
