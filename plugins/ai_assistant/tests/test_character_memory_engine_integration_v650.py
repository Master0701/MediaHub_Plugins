from pathlib import Path


def test_character_memory_engine_integrated_v650():
    root = Path(__file__).resolve().parents[1]
    text = (root / "plugin.py").read_text(encoding="utf-8")

    assert (
        "from services.character_memory_engine "
        "import CharacterMemoryEngine"
        in text
    )
    assert (
        "self.character_memory_engine = CharacterMemoryEngine()"
        in text
    )
    assert (
        "character_memory = "
        "self.character_memory_engine.build("
        in text
    )
    assert '"character_memory": character_memory' in text
    assert (
        'context.document["character_memory"] = '
        "character_memory"
        in text
    )
