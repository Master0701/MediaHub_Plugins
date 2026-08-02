from pathlib import Path


def test_character_evolution_engine_integrated_v640():
    root = Path(__file__).resolve().parents[1]
    text = (root / "plugin.py").read_text(encoding="utf-8")

    assert (
        "from services.character_evolution_engine "
        "import CharacterEvolutionEngine"
        in text
    )
    assert (
        "self.character_evolution_engine = CharacterEvolutionEngine()"
        in text
    )
    assert (
        "character_evolution = "
        "self.character_evolution_engine.build("
        in text
    )
    assert '"character_evolution": character_evolution' in text
    assert (
        'context.document["character_evolution"] = '
        "character_evolution"
        in text
    )
