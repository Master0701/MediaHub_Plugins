import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.semantic_field_classifier import SemanticFieldClassifier

TEXT = (
    "Aquaman: Lost Kingdom ist 2023 erschienen. "
    "Der Film ist die Fortsetzung von Aquaman aus dem Jahr 2018. "
    "Der Film sollte ursprünglich im Dezember 2022 in die Kinos kommen. "
    "Es ist der letzte Film des DC Extended Universe, das 2024 durch das DC Universe ersetzt wurde."
)

def test_release_year_and_predecessor():
    result = SemanticFieldClassifier().classify(
        title="Aquaman: Lost Kingdom",
        text=TEXT,
        semantic_result={"entity_proposals": [{
            "title": "Aquaman: Lost Kingdom",
            "entity_type": "movie",
            "year": 2023,
            "confidence": 0.89,
            "sentence": "Aquaman: Lost Kingdom ist 2023 erschienen.",
        }]},
        parser_result={"result": {"fields": {"metadata": {"universe": "DC Extended Universe"}}}},
    )
    assert result["primary_values"]["release_year"] == 2023
    assert result["primary_values"]["predecessor"]["year"] == 2018
    assert result["primary_values"]["universe"] == "DC Extended Universe"

def test_planned_release_and_transition():
    result = SemanticFieldClassifier().classify(
        title="Aquaman: Lost Kingdom",
        text=TEXT,
    )
    assert result["primary_values"]["planned_release_year"] == 2022
    assert result["primary_values"]["universe_transition_year"] == 2024

def test_cosplay_year_is_rejected():
    result = SemanticFieldClassifier().classify(
        title="Aquaman",
        text="Aquaman-Cosplay (2014). Aquaman ist ein Superheld.",
    )
    assert result["rejected"][0]["value"] == 2014
